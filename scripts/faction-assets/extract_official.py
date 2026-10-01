"""Extract review candidates from the official TTS reference atlas.

This script only reads the validated atlas and catalog. It writes isolated
review candidates into assets/factions/intermediate/official and a provenance
record into docs/faction-assets-qa. It does not edit any TTS original or
source copy, and extraction never implies visual approval.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".asset-pipeline-deps"))
import cv2  # noqa: E402


REPORT = ROOT / "docs/tts-assets-review/tts-faction-assets-report.json"
MAPPING = ROOT / "docs/faction-assets-qa/official-mapping.json"
ATLAS = ROOT / "docs/tts-assets-review/candidates/official-reference-atlas-4ac482e11a79.png"
ATLAS_COPY = ROOT / "assets/factions/source/official/official-reference-atlas-4ac482e11a79.png"
OUTPUT_DIR = ROOT / "assets/factions/intermediate/official"
OUTPUT_JSON = ROOT / "docs/faction-assets-qa/official-extraction.json"

# Atlas card cell is 1418 x 827 px. The emblem occupies its upper-right badge.
# This crop excludes card text/number and gives GrabCut a safe background margin.
BADGE_CROP_IN_CELL = (1190, 0, 1415, 190)
DEFAULT_GRABCUT_RECT = (28, 8, 188, 175)  # x, y, width, height in badge crop
MIN_COMPONENT_AREA = 100
SPECIAL_WARNINGS = {
    "the-ghosts-of-creuss": ["ALTERNATE_TOKEN_SHEET_EXISTS"],
    "the-council-keleres": ["KELERES_REFERENCE_USES_MENTAK_VARIANT"],
    "the-firmament-the-obsidian": ["COMBINED_FACTION_IDENTITY"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def extract_badge(
    atlas_bgr: np.ndarray,
    column: int,
    row: int,
    rect: tuple[int, int, int, int],
) -> tuple[np.ndarray, dict]:
    cell_width = atlas_bgr.shape[1] // 5
    cell_height = atlas_bgr.shape[0] // 6
    x0 = column * cell_width + BADGE_CROP_IN_CELL[0]
    y0 = row * cell_height + BADGE_CROP_IN_CELL[1]
    x1 = column * cell_width + BADGE_CROP_IN_CELL[2]
    y1 = row * cell_height + BADGE_CROP_IN_CELL[3]
    badge = atlas_bgr[y0:y1, x0:x1].copy()
    if badge.shape[:2] != (190, 225):
        raise RuntimeError(f"Unexpected badge crop {badge.shape}")

    mask = np.zeros(badge.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(badge, mask, rect, bgd_model, fgd_model, 8, cv2.GC_INIT_WITH_RECT)
    foreground = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)

    # Exclude isolated noise; keep distinct emblem pieces such as Argent/Hacan.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    clean = np.zeros_like(foreground)
    components = []
    for index in range(1, count):
        x, y, w, h, area = map(int, stats[index])
        if area >= MIN_COMPONENT_AREA:
            clean[labels == index] = 1
            components.append({"x": x, "y": y, "width": w, "height": h, "area": area})

    alpha = clean * 255
    rgb = cv2.cvtColor(badge, cv2.COLOR_BGR2RGB)
    rgba = np.dstack((rgb, alpha)).astype(np.uint8)
    ys, xs = np.where(clean > 0)
    if not len(xs):
        raise RuntimeError("GrabCut found no foreground")
    left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    margin = 5
    crop_left, crop_top = max(0, left - margin), max(0, top - margin)
    crop_right, crop_bottom = min(rgba.shape[1], right + margin), min(rgba.shape[0], bottom + margin)
    out = rgba[crop_top:crop_bottom, crop_left:crop_right].copy()
    metadata = {
        "atlasCrop": [x0, y0, x1, y1],
        "grabCutRect": list(rect),
        "localForegroundBBox": [left, top, right, bottom],
        "intermediateCropInOriginal": [x0 + crop_left, y0 + crop_top, x0 + crop_right, y0 + crop_bottom],
        "foregroundPixels": int(clean.sum()),
        "alphaCoverage": round(float(clean.mean()), 6),
        "foregroundComponents": components,
        "outputWidth": int(out.shape[1]),
        "outputHeight": int(out.shape[0]),
    }
    return out, metadata


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    if mapping.get("candidateReportSha256") != sha256(REPORT):
        raise RuntimeError("TTS candidate report changed after official inventory")
    catalog_path = ROOT / mapping["catalogSource"]
    if mapping.get("catalogSha256") != sha256(catalog_path):
        raise RuntimeError("Catalog changed after official inventory")
    by_slug = {item["slug"]: item for item in mapping["factions"]}
    if len(by_slug) != 30 or len(report["factions"]) != 30:
        raise RuntimeError("Expected 30 official factions")
    expected_atlas_sha = next(
        item["sourceSha256"]
        for item in by_slug["the-arborec"]["candidates"]
        if item.get("atlas")
    )
    if sha256(ATLAS) != expected_atlas_sha:
        raise RuntimeError("Validated TTS atlas changed")
    with Image.open(ATLAS) as atlas_image:
        if atlas_image.size != (7090, 4962) or atlas_image.getchannel("A").getextrema() != (255, 255):
            raise RuntimeError("Atlas dimensions/alpha changed")
    if not ATLAS_COPY.exists():
        ATLAS_COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ATLAS, ATLAS_COPY)
    if sha256(ATLAS_COPY) != expected_atlas_sha:
        raise RuntimeError("Atlas source copy differs from validated original")

    atlas_bgr = cv2.imread(str(ATLAS_COPY), cv2.IMREAD_COLOR)
    if atlas_bgr is None:
        raise RuntimeError("Cannot decode copied atlas")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for faction in report["factions"]:
        slug = faction["slug"]
        authoritative = by_slug[slug]
        if faction["name"] != authoritative["name"] or faction["contentSet"] != authoritative["contentSet"]:
            raise RuntimeError(f"Catalog mismatch: {slug}")
        atlas_candidate = next(c for c in faction["candidates"] if c.get("atlas"))
        if atlas_candidate["sha256"] != expected_atlas_sha or atlas_candidate["relativeFile"] != "candidates/official-reference-atlas-4ac482e11a79.png":
            raise RuntimeError(f"Unexpected atlas source for {slug}")
        atlas_meta = atlas_candidate["atlas"]
        output, metrics = extract_badge(
            atlas_bgr, atlas_meta["column"], atlas_meta["row"], DEFAULT_GRABCUT_RECT
        )
        output_path = OUTPUT_DIR / f"{slug}.png"
        Image.fromarray(output, "RGBA").save(output_path, format="PNG")
        bbox = metrics["localForegroundBBox"]
        largest_side = max(bbox[2] - bbox[0], bbox[3] - bbox[1])
        warnings = list(SPECIAL_WARNINGS.get(slug, []))
        if largest_side < 140:
            warnings.append("SMALL_ATLAS_ICON")
        entries.append(
            {
                "slug": slug,
                "name": faction["name"],
                "contentSet": faction["contentSet"],
                "sourceKind": "atlas",
                "original": relative(ATLAS),
                "originalSha256": expected_atlas_sha,
                "source": relative(ATLAS_COPY),
                "sourceSha256": expected_atlas_sha,
                "sourceWidth": int(atlas_bgr.shape[1]),
                "sourceHeight": int(atlas_bgr.shape[0]),
                "intermediate": relative(output_path),
                "intermediateSha256": sha256(output_path),
                "intermediateWidth": metrics["outputWidth"],
                "intermediateHeight": metrics["outputHeight"],
                "crop": metrics["atlasCrop"],
                "method": "OpenCV GrabCut rectangle initialization (8 iterations), connected-component noise cutoff <100 px",
                "parameters": {
                    "atlasCardId": atlas_meta["cardId"],
                    "atlasIndex": atlas_meta["index"],
                    "grabCutRect": list(DEFAULT_GRABCUT_RECT),
                    "minComponentArea": MIN_COMPONENT_AREA,
                    "alpha": "binary",
                    "marginPixels": 5,
                },
                "warnings": warnings,
                "metrics": metrics,
                "status": "READY_FOR_REVIEW",
            }
        )
    if len(entries) != 30:
        raise RuntimeError("Incomplete extraction")
    OUTPUT_JSON.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sourceReport": relative(REPORT),
                "sourceReportSha256": sha256(REPORT),
                "mapping": relative(MAPPING),
                "mappingSha256": sha256(MAPPING),
                "limitations": [
                    "READY_FOR_REVIEW means ready for human visual inspection, not approved for production.",
                    "GrabCut produces binary alpha; inspect edges/halos at zoom on light, dark and checkerboard backgrounds.",
                    "Atlas emblem resolution is 99–171 px wide before later card normalization; enlargement cannot restore lost detail.",
                    "Seven icons with largest source side below 140 px were compared with larger token-sheet emblems. Token segmentation lost part of Ghosts and retained background for Yssaril; other token images had textured/JPEG backgrounds without a clear sharpness gain. The atlas was retained consistently and SMALL_ATLAS_ICON flags the seven candidates.",
                ],
                "factions": entries,
            },
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"Extracted {len(entries)} review candidates into {relative(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
