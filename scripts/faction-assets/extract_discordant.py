"""Copy and conservatively isolate the Discordant Stars faction marks.

The import archive is read only.  The copied card is the immutable source;
the derived PNG is only an intermediate for visual QA and later normalization.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".asset-pipeline-deps"))
import cv2  # noqa: E402
from discordant_special_masks import GRABCUT_RECTS as SPECIAL_GRABCUT_RECTS, extract as extract_special  # noqa: E402

IMPORT_ROOT = ROOT / "imports" / "discordant-stars" / "Discordant Stars" / "Files"
SOURCE_ROOT = ROOT / "assets" / "factions" / "source" / "discordant-stars"
INTERMEDIATE_ROOT = ROOT / "assets" / "factions" / "intermediate" / "discordant-stars"
MAPPING_FILE = ROOT / "docs" / "faction-assets-qa" / "discordant-stars-mapping.json"
CATALOG_FILE = ROOT / "supabase" / "migrations" / "20260930150000_content_catalog_and_draft_configuration.sql"

# The title and symbol were checked on the faction reference cards.  Zelian is
# absent from that folder; the Alliance Reference Card explicitly says ZELIAN.
CARD_BY_SLUG = {
    "the-shipwrights-of-axis": "Axis R.png",
    "the-celdauri-trade-confederation": "Celd R.png",
    "the-savages-of-cymiae": "Cymi R.png",
    "the-dih-mohn-flotilla": "DihM R.png",
    "the-florzen-profiteers": "Flor R.png",
    "the-free-systems-compact": "Free R.png",
    "the-ghemina-raiders": "Ghem R.png",
    "the-augurs-of-ilyxum": "Ilyx R.png",
    "the-kollecc-society": "Koll R.png",
    "the-kortali-tribunal": "Kort R.png",
    "the-li-zho-dynasty": "LiZh R.png",
    "the-ltokk-khrask": "LTok R.png",
    "the-mirveda-protectorate": "Mirv R.png",
    "the-glimmer-of-mortheus": "Mort R.png",
    "the-myko-mentori": "Myko R.png",
    "the-nivyn-star-kings": "Nivy R.png",
    "the-olradin-league": "Olra R.png",
    "the-zealots-of-rhodun": "Rhod R.png",
    "rohdhna-mechatronics": "RohD R.png",
    "the-tnelis-syndicate": "Tnel R.png",
    "the-vaden-banking-clans": "Vade R.png",
    "the-vaylerian-scourge": "Vayl R.png",
    "the-veldyr-sovereignty": "Veld R.png",
    "the-zelian-purifier": "Zelian.png",
    "the-bentor-conglomerate": "Bent R.png",
    "the-cheiran-hordes": "Chei R.png",
    "the-edyn-mandate": "Edyn R.png",
    "the-ghoti-wayfarers": "Ghot R.png",
    "the-gledge-union": "GLEd R.png",
    "the-berserkers-of-kjalengard": "Kjal R.png",
    "the-monks-of-kolume": "Kolu R.png",
    "the-kyro-sodality": "Kyro R.png",
    "the-lanefir-remnants": "Lane R.png",
    "the-nokar-sellships": "Noka R.png",
}

REFERENCE_CROP = (5270, 100, 6030, 900)
ZELIAN_CROP = (170, 150, 580, 590)
PADDING = 16
GRABCUT_RECTS = {
    "the-cheiran-hordes": (100, 185, 560, 570),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def catalog() -> list[tuple[str, str]]:
    sql = CATALOG_FILE.read_text(encoding="utf-8")
    pattern = re.compile(r"\('discordant-stars', '((?:[^']|'')+)', '([^']+)', \d+\)")
    entries = [(slug, name.replace("''", "'")) for name, slug in pattern.findall(sql)]
    if len(entries) != 34 or len({slug for slug, _ in entries}) != 34:
        raise RuntimeError("The catalog must contain exactly 34 unique Discordant Stars slugs")
    if set(CARD_BY_SLUG) != {slug for slug, _ in entries}:
        raise RuntimeError("The explicit source map and catalog disagree")
    return entries


def source_path(slug: str) -> Path:
    folder = "Alliance Reference Cards" if slug == "the-zelian-purifier" else "Faction Reference Cards"
    return IMPORT_ROOT / folder / CARD_BY_SLUG[slug]


def _fit_background(rgb: np.ndarray) -> np.ndarray:
    """Fit a smooth card background from off-emblem pixels, trimming art/frame."""
    height, width = rgb.shape[:2]
    ys, xs = np.mgrid[0:height, 0:width]
    x = (xs.astype(np.float32) - width / 2) / width
    y = (ys.astype(np.float32) - height / 2) / height
    design = np.stack((np.ones_like(x), x, y, x * y, x * x, y * y), axis=-1)
    # Restrict sampling to the panel's interior, outside the central emblem.
    outside_mark = ((x / 0.30) ** 2 + (y / 0.36) ** 2) > 1
    interior = (xs > 95) & (xs < width - 95) & (ys > 65) & (ys < height - 65)
    samples = outside_mark & interior
    matrix = design[samples][::4]
    colors = rgb[samples][::4].astype(np.float32)
    weights = np.ones(len(matrix), dtype=np.float32)
    for _ in range(6):
        root_weight = np.sqrt(weights)[:, None]
        coefficients = np.linalg.lstsq(matrix * root_weight, colors * root_weight, rcond=None)[0]
        residual = np.max(np.abs(matrix @ coefficients - colors), axis=1)
        weights = 1 / (1 + (residual / 17) ** 4)
    return np.clip(design @ coefficients, 0, 255)


def isolate(card: Image.Image, crop: tuple[int, int, int, int], slug: str) -> tuple[Image.Image, dict, list[str]]:
    """Build a tentative alpha mask without modifying the source or resampling."""
    original = np.asarray(card.convert("RGB").crop(crop), dtype=np.uint8)
    height, width = original.shape[:2]
    background = _fit_background(original)
    difference = np.max(np.abs(original.astype(np.float32) - background), axis=2)
    border = np.zeros((height, width), dtype=bool)
    border[:36] = True
    border[-36:] = True
    border[:, :36] = True
    border[:, -36:] = True
    noise = float(np.percentile(difference[border], 45))
    # A high threshold is intentional: losing faint details is visible and
    # flagged, whereas incorporating card art could be mistaken for a logo.
    threshold = max(55.0, noise + 25.0)
    opaque = (difference > threshold).astype(np.uint8)
    opaque[:12] = 0
    opaque[-12:] = 0
    opaque[:, :12] = 0
    opaque[:, -12:] = 0
    if slug in GRABCUT_RECTS:
        # The printed emblem is a compact, color-distinct object. GrabCut's
        # rectangle excludes the panel while retaining dark enclosed details.
        grabcut_mask = np.zeros((height, width), np.uint8)
        cv2.grabCut(
            original[:, :, ::-1].copy(), grabcut_mask, GRABCUT_RECTS[slug],
            np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64),
            8, cv2.GC_INIT_WITH_RECT,
        )
        opaque = np.isin(grabcut_mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)
    if slug == "the-celdauri-trade-confederation":
        ys, xs = np.mgrid[0:height, 0:width]
        # The blue outline is chromatically distinct from the olive panel.
        blue = (
            (original[:, :, 2].astype(np.int16) - original[:, :, 0].astype(np.int16) > 12)
            & (original[:, :, 2].astype(np.int16) - original[:, :, 1].astype(np.int16) > 10)
            & (xs > 55) & (xs < width - 55) & (ys > 65) & (ys < height - 65)
        )
        opaque = np.maximum(opaque, blue.astype(np.uint8))
        red, green, indigo = (original[:, :, i].astype(np.int16) for i in range(3))
        gold = (
            (red > 80) & (green > 55) & (red - indigo > 60) & (green - indigo > 45)
            & (xs > 70) & (xs < width - 55) & (ys > 80) & (ys < height - 65)
        )
        opaque = np.maximum(opaque, gold.astype(np.uint8))
    if slug == "the-dih-mohn-flotilla":
        ys, xs = np.mgrid[0:height, 0:width]
        red, green, blue = (original[:, :, i].astype(np.int16) for i in range(3))
        violet = (
            (blue - red > 10) & (blue - green > 30) & (blue > 65)
            & (xs > 100) & (xs < 660) & (ys > 130) & (ys < 760)
        )
        opaque = np.maximum(opaque, violet.astype(np.uint8))
    if slug in {"the-free-systems-compact", "the-monks-of-kolume", "the-veldyr-sovereignty"}:
        # Both sources show a closed circular mark. Retain all original pixels
        # within that printed outline, including near-black design regions.
        circle = np.zeros_like(opaque)
        center, radius = (
            ((375, 470), 258) if slug == "the-free-systems-compact"
            else ((365, 430), 280) if slug == "the-monks-of-kolume"
            else ((375, 470), 263)
        )
        cv2.circle(circle, center, radius, 1, thickness=-1)
        opaque = circle
    if slug == "the-glimmer-of-mortheus":
        # Both eyes are visibly filled grey discs in the printed source.
        for center, radius in (((190, 547), 55), ((562, 414), 55)):
            cv2.circle(opaque, center, radius, 1, thickness=-1)
    if slug in {"the-ghoti-wayfarers", "the-ltokk-khrask"}:
        # Source/token comparison confirms a near-black filled substrate inside
        # these closed emblems. Keep original source pixels inside the outline.
        panel = np.zeros_like(opaque)
        points = (
            [(370, 211), (626, 465), (370, 720), (109, 465)]
            if slug == "the-ghoti-wayfarers" else
            [(119, 251), (640, 251), (378, 697)]
        )
        cv2.fillConvexPoly(panel, np.array(points, np.int32), 1)
        opaque = np.maximum(opaque, panel)
    if slug == "the-augurs-of-ilyxum":
        # The broad left petal is pale purple and touches the central stem, so
        # it is not a closed topological hole. Restrict its color seed to the
        # petal bounded by the visible silver source outline.
        petal = np.zeros_like(opaque)
        cv2.fillPoly(petal, [np.array([
            (78, 431), (135, 408), (210, 404), (291, 413),
            (385, 437), (344, 466), (270, 507), (193, 525), (120, 482),
        ], np.int32)], 1)
        red, green, blue = (original[:, :, i].astype(np.int16) for i in range(3))
        violet = (red - green > 35) & (blue - green > 45) & (blue > 70)
        opaque = np.maximum(opaque, (petal & violet.astype(np.uint8)))
    if slug == "the-tnelis-syndicate":
        ys, xs = np.mgrid[0:height, 0:width]
        staff_black = (
            (original[:, :, 0] < 25) & (original[:, :, 1] < 25) & (original[:, :, 2] < 25)
            & (xs > 345) & (xs < 420) & (ys > 370) & (ys < 660)
        )
        opaque = np.maximum(opaque, staff_black.astype(np.uint8))
        # The right wing and coiled snake are saturated green in the source;
        # the card behind them is a much darker, less saturated green.
        red, green, blue = (original[:, :, i].astype(np.int16) for i in range(3))
        green_symbol = (
            (green > 65) & (green - red > 40) & (green - blue > 40)
            & (xs > 225) & (xs < 695) & (ys > 335) & (ys < 665)
        )
        opaque = np.maximum(opaque, green_symbol.astype(np.uint8))
    if slug == "the-kortali-tribunal":
        # The white octagonal border encloses a deliberate black shield.
        # Filling its largest contour retains the complete source design.
        luminosity = original.min(axis=2)
        bright = (luminosity > 155).astype(np.uint8)
        bright[:145] = 0
        bright[785:] = 0
        bright[:, :60] = 0
        bright[:, 700:] = 0
        bright = cv2.morphologyEx(bright, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(bright, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = [c for c in contours if cv2.contourArea(c) > 100000]
        if candidates:
            shield = np.zeros_like(opaque)
            cv2.drawContours(shield, [max(candidates, key=cv2.contourArea)], -1, 1, thickness=-1)
            opaque = shield
    if slug == "the-shipwrights-of-axis":
        # The moon is an intentional near-black disc on near-black card art.
        # Its visible circular edge was measured on the full-size source.
        moon = np.zeros_like(opaque)
        cv2.circle(moon, (378, 346), 145, 1, thickness=-1)
        opaque = np.maximum(opaque, moon)
        ys, xs = np.mgrid[0:height, 0:width]
        # Crimson body fills are darker than the white linework yet distinctly
        # redder than the surrounding brown panel.
        crimson = (
            (original[:, :, 0].astype(np.int16) - original[:, :, 1].astype(np.int16) > 70)
            & (original[:, :, 0].astype(np.int16) - original[:, :, 2].astype(np.int16) > 70)
            & (original[:, :, 0] > 75)
            & (xs > 210) & (xs < 540) & (ys > 300) & (ys < 770)
        )
        opaque = np.maximum(opaque, crimson.astype(np.uint8))

    # Reject edge-attached components from borders/decorations. Keep independent
    # parts of a mark (for example the three Celdauri chevrons).
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(opaque, 8)
    kept = np.zeros_like(opaque)
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        cx, cy = centroids[index]
        minimum_area = 200 if slug == "the-celdauri-trade-confederation" else 15
        if area < minimum_area or x <= 3 or y <= 3 or x + w >= width - 3 or y + h >= height - 3:
            continue
        if slug == "the-celdauri-trade-confederation" and cx < 155 and cy > 635:
            # A detached gold corner of the printed hex panel, not the mark.
            continue
        if not (width * 0.12 <= cx <= width * 0.88 and height * 0.08 <= cy <= height * 0.9):
            continue
        kept[labels == index] = 1
    if slug == "the-celdauri-trade-confederation":
        # Small enclosed false holes occur inside the solid gold chevrons;
        # open spaces between chevrons remain connected to the exterior.
        hole_count, hole_labels, hole_stats, _ = cv2.connectedComponentsWithStats(1 - kept, 8)
        for index in range(1, hole_count):
            x, y, w, h, area = hole_stats[index]
            if area <= 12000 and x > 0 and y > 0 and x + w < width and y + h < height:
                kept[hole_labels == index] = 1
        kept = cv2.morphologyEx(kept, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        kept = cv2.dilate(kept, np.ones((3, 3), np.uint8), iterations=1)
    if slug == "the-augurs-of-ilyxum":
        # Pale petals are bounded by retained silver outlines. Fill only
        # topologically enclosed holes with their unchanged source pixels.
        kept = cv2.morphologyEx(kept, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        hole_count, hole_labels, hole_stats, _ = cv2.connectedComponentsWithStats(1 - kept, 8)
        for index in range(1, hole_count):
            x, y, w, h, area = hole_stats[index]
            if area <= 30000 and x > 0 and y > 0 and x + w < width and y + h < height:
                kept[hole_labels == index] = 1

    warnings: list[str] = []
    if not kept.any():
        warnings.append("foreground_not_detected")
        # Do not silently turn the full printed card into a purported logo.
        rgba = Image.new("RGBA", (width + PADDING * 2, height + PADDING * 2))
        metrics = {"detectedPixels": 0, "cropPixels": width * height, "backgroundNoise": noise}
        return rgba, metrics, warnings

    ys, xs = np.nonzero(kept)
    left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)
    if left <= 30 or top <= 30 or right >= width - 30 or bottom >= height - 30:
        warnings.append("foreground_near_crop_boundary")
    if kept.mean() < 0.025:
        warnings.append("small_foreground_area")
    if kept.mean() > 0.65:
        warnings.append("large_foreground_area")
    if noise > 30 and slug not in GRABCUT_RECTS:
        warnings.append("textured_background")

    # A 1 px soft edge only changes alpha. RGB stays at exact source pixels.
    alpha = cv2.GaussianBlur((kept * 255).astype(np.uint8), (3, 3), 0.55)
    region = original[top:bottom, left:right]
    region_alpha = alpha[top:bottom, left:right]
    result = np.zeros((bottom - top + 2 * PADDING, right - left + 2 * PADDING, 4), np.uint8)
    result[PADDING:-PADDING, PADDING:-PADDING, :3] = region
    result[PADDING:-PADDING, PADDING:-PADDING, 3] = region_alpha
    result[result[:, :, 3] == 0, :3] = 0
    metrics = {
        "detectedPixels": int(kept.sum()),
        "cropPixels": width * height,
        "backgroundNoise": round(noise, 2),
        "foregroundBoundsInCrop": [left, top, right, bottom],
        "intermediatePadding": PADDING,
        "intermediateOffset": [crop[0] + left - PADDING, crop[1] + top - PADDING],
        "occupancy": round(float(kept.mean()), 4),
    }
    return Image.fromarray(result, "RGBA"), metrics, warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", nargs="*", help="Only these slugs; do not copy cards or write mapping")
    args = parser.parse_args()
    entries = catalog()
    if args.preview is not None:
        requested = set(args.preview)
        entries = [entry for entry in entries if entry[0] in requested]
        if len(entries) != len(requested):
            raise RuntimeError("Unknown preview slug")
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    INTERMEDIATE_ROOT.mkdir(parents=True, exist_ok=True)
    MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = []
    total_bytes = 0
    for slug, name in entries:
        imported = source_path(slug)
        if not imported.is_file():
            raise FileNotFoundError(imported)
        imported_sha_before = sha256(imported)
        total_bytes += imported.stat().st_size
        copied = SOURCE_ROOT / f"{slug}{imported.suffix.lower()}"
        if args.preview is None:
            if copied.exists() and sha256(copied) != imported_sha_before:
                raise RuntimeError(f"Existing source differs from import: {copied}")
            if not copied.exists():
                shutil.copy2(imported, copied)
            copied_sha = sha256(copied)
            if copied_sha != imported_sha_before:
                raise RuntimeError(f"Copy hash mismatch: {copied}")
        else:
            copied_sha = None
        crop = ZELIAN_CROP if slug == "the-zelian-purifier" else REFERENCE_CROP
        with Image.open(imported) as image:
            source_width, source_height = image.size
            if slug in SPECIAL_GRABCUT_RECTS:
                intermediate, special_metrics = extract_special(imported, list(crop), SPECIAL_GRABCUT_RECTS[slug])
                if slug == "the-nokar-sellships":
                    # The enclosed aperture is a dark part of Nokar's shutter,
                    # confirmed against its token. Fill only bounded alpha
                    # holes using RGB already present from the copied source.
                    pixels = np.array(intermediate)
                    holes, labels, stats, _ = cv2.connectedComponentsWithStats((pixels[:, :, 3] < 128).astype(np.uint8), 8)
                    filled = 0
                    for index in range(1, holes):
                        x, y, w, h, area = stats[index]
                        if 1000 < area < 20000 and x > 0 and y > 0 and x + w < intermediate.width and y + h < intermediate.height:
                            pixels[labels == index, 3] = 255
                            filled += int(area)
                    if filled == 0:
                        raise RuntimeError("Nokar dark aperture could not be identified as a bounded hole")
                    intermediate = Image.fromarray(pixels, "RGBA")
                    special_metrics["enclosedAperturePixelsRestored"] = filled
                bounds = special_metrics["foregroundBBoxInCrop"]
                metrics = {
                    "detectedPixels": special_metrics["foregroundPixels"],
                    "cropPixels": (crop[2] - crop[0]) * (crop[3] - crop[1]),
                    "foregroundBoundsInCrop": bounds,
                    "intermediatePadding": PADDING,
                    "intermediateOffset": [crop[0] + bounds[0] - PADDING, crop[1] + bounds[1] - PADDING],
                    "occupancy": round(special_metrics["foregroundPixels"] / ((crop[2] - crop[0]) * (crop[3] - crop[1])), 4),
                    "foregroundComponents": special_metrics["foregroundComponents"],
                }
                if slug == "the-nokar-sellships":
                    metrics["enclosedAperturePixelsRestored"] = special_metrics["enclosedAperturePixelsRestored"]
                warnings = ["source_glow_requires_review"] if slug == "the-vaylerian-scourge" else []
            else:
                intermediate, metrics, warnings = isolate(image, crop, slug)
        intermediate_path = INTERMEDIATE_ROOT / f"{slug}.png"
        intermediate.save(intermediate_path, optimize=True)
        if sha256(imported) != imported_sha_before:
            raise RuntimeError(f"Import changed during processing: {imported}")
        output.append({
            "slug": slug,
            "name": name,
            "contentSet": "discordant-stars",
            "importSource": rel(imported),
            "importSha256": imported_sha_before,
            "source": rel(copied) if args.preview is None else None,
            "sourceSha256": copied_sha,
            "sourceWidth": source_width,
            "sourceHeight": source_height,
            "sourceKind": "ds",
            "intermediate": rel(intermediate_path),
            "intermediateSha256": sha256(intermediate_path),
            "intermediateWidth": intermediate.width,
            "intermediateHeight": intermediate.height,
            "crop": list(crop),
            "method": "opencv_grabcut_rect_8_iterations_no_resampling" if slug in SPECIAL_GRABCUT_RECTS or slug in GRABCUT_RECTS else "robust_background_color_difference_mask_no_resampling",
            "parameters": ({"padding": PADDING, "grabcutRect": list(SPECIAL_GRABCUT_RECTS[slug]), "grabcutIterations": 8, "minimumComponentArea": 100, "fillEnclosedDarkAperture": slug == "the-nokar-sellships"} if slug in SPECIAL_GRABCUT_RECTS else {
                "padding": PADDING,
                "backgroundFit": "quadratic_IRLS_6_iterations_off_center",
                "differenceThreshold": "max(55, p45_border+25)",
                "manualGeometry": (
                    {"shape": "circle", "center": [378, 346], "radius": 145, "meaning": "Axis moon"} if slug == "the-shipwrights-of-axis"
                    else {"shape": "circle", "center": [375, 470], "radius": 258, "meaning": "Free Systems enclosed mark"} if slug == "the-free-systems-compact"
                    else {"shape": "circle", "center": [365, 430], "radius": 280, "meaning": "Kolume enclosed mark"} if slug == "the-monks-of-kolume"
                    else {"shape": "circle", "center": [375, 470], "radius": 263, "meaning": "Veldyr enclosed mark"} if slug == "the-veldyr-sovereignty"
                    else {"shape": "two_circles", "centers": [[190, 547], [562, 414]], "radii": [55, 55], "meaning": "Mortheus filled eyes"} if slug == "the-glimmer-of-mortheus"
                    else {"shape": "source_panel_polygon", "meaning": "Ghoti dark diamond"} if slug == "the-ghoti-wayfarers"
                    else {"shape": "source_panel_polygon", "meaning": "L'tokk dark triangle"} if slug == "the-ltokk-khrask"
                    else {"shape": "largest_closed_white_contour", "minimumArea": 100000, "meaning": "Kortali black shield"} if slug == "the-kortali-tribunal"
                    else None
                ),
                "colorSeed": (
                    "gold_and_blue_outline" if slug == "the-celdauri-trade-confederation"
                    else "violet" if slug == "the-dih-mohn-flotilla"
                    else "crimson" if slug == "the-shipwrights-of-axis"
                    else "localized_violet_left_petal" if slug == "the-augurs-of-ilyxum"
                    else "black_staff_and_saturated_green_snake_wing" if slug == "the-tnelis-syndicate"
                    else None
                ),
                "fillEnclosedHoles": slug in {"the-celdauri-trade-confederation", "the-augurs-of-ilyxum"},
                "grabcutRect": list(GRABCUT_RECTS[slug]) if slug in GRABCUT_RECTS else None,
                "grabcutIterations": 8 if slug in GRABCUT_RECTS else None,
            }),
            "warnings": warnings,
            "metrics": metrics,
            "status": "NEEDS_MANUAL_REVIEW" if warnings else "READY_FOR_REVIEW",
        })
        print(f"{slug}: {intermediate.width}x{intermediate.height}; warnings={warnings}")
    if args.preview is None:
        MAPPING_FILE.write_text(json.dumps({"version": 1, "count": len(output), "selectedSourceBytes": total_bytes, "factions": output}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {MAPPING_FILE}")


if __name__ == "__main__":
    main()
