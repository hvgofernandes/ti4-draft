"""Build the faction asset manifest and normalize explicitly selected sources.

The catalog migration is the only authority for names, slugs and content sets.
This script never changes a source image and refuses to guess a background mask.
Run with Python 3 and Pillow: python scripts/faction-assets/build_assets.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CATALOG_SQL = ROOT / "supabase/migrations/20260930150000_content_catalog_and_draft_configuration.sql"
TTS_MAPPING = ROOT / "docs/faction-assets-qa/official-mapping.json"
SELECTIONS = ROOT / "scripts/faction-assets/source-selections.json"
SOURCE_ROOT = ROOT / "assets/factions/source"
FINAL_ROOT = ROOT / "assets/factions/final"
INTERMEDIATE_ROOT = ROOT / "assets/factions/intermediate"
QA_ROOT = ROOT / "docs/faction-assets-qa"
PREVIEW_ROOT = QA_ROOT / "previews"
MANIFEST = QA_ROOT / "faction-assets-manifest.json"
CANVAS = 512
TARGET_LONG_SIDE = 0.72
MAX_UPSCALE = 2.0
ALPHA_THRESHOLD = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def catalog() -> list[dict]:
    sql = CATALOG_SQL.read_text(encoding="utf-8-sig")
    block = sql.split("WITH catalog(content_set_slug, name, slug, sort_order) AS (VALUES", 1)[1].split(")\nINSERT INTO", 1)[0]
    rows = re.findall(r"\('([^']+)', '((?:[^']|'')+)', '([^']+)', (\d+)\)", block)
    entries = [
        {"contentSet": content_set, "name": name.replace("''", "'"), "slug": slug, "sortOrder": int(order)}
        for content_set, name, slug, order in rows
    ]
    expected = {"base": 17, "pok": 7, "thunders-edge": 6, "discordant-stars": 34}
    if Counter(item["contentSet"] for item in entries) != expected or len({item["slug"] for item in entries}) != 64:
        raise ValueError("The catalog must contain 64 unique faction slugs in the expected content sets")
    return entries


def within_root(path_text: str) -> Path:
    path = (ROOT / path_text).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError(f"Path escapes project root: {path_text}")
    return path


def project_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def image_info(path: Path) -> dict:
    with Image.open(path) as image:
        alpha = image.getchannel("A") if "A" in image.getbands() else None
        minimum, maximum = alpha.getextrema() if alpha else (255, 255)
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "hasAlphaChannel": alpha is not None,
            "hasTransparency": minimum < 255,
            "alphaExtrema": [minimum, maximum],
        }


def preserve_source(source: Path, destination: Path) -> str:
    """Copy one source byte-for-byte, refusing to replace different content."""
    source = source.resolve()
    destination = destination.resolve()
    if source == destination or not source.is_relative_to(ROOT) or not destination.is_relative_to(SOURCE_ROOT.resolve()):
        raise ValueError("Unsafe source copy")
    before = sha256(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256(destination) != before:
            raise ValueError(f"Existing source copy differs: {destination}")
    else:
        shutil.copyfile(source, destination)
    if sha256(source) != before or sha256(destination) != before:
        raise ValueError(f"Source integrity failed: {source}")
    return before


def preview_crop(source: Path, destination: Path, roi: dict) -> dict:
    """Make a clearly labelled inspection crop; never use it as a final logo."""
    before = sha256(source)
    x, y, width, height = (roi[key] for key in ("x", "y", "width", "height"))
    if any(not isinstance(value, int) for value in (x, y, width, height)):
        raise ValueError("Preview ROI must use integer coordinates")
    with Image.open(source) as image:
        if not (0 <= x < x + width <= image.width and 0 <= y < y + height <= image.height):
            raise ValueError("Preview ROI lies outside source")
        excerpt = image.crop((x, y, x + width, y + height))
        destination.parent.mkdir(parents=True, exist_ok=True)
        excerpt.save(destination, format="PNG", optimize=True)
    if sha256(source) != before:
        raise ValueError("Preview generation modified source")
    return {"path": project_path(destination), "sha256": sha256(destination),
            "width": width, "height": height}


def normalize(source: Path, output: Path, crop: list[int] | None = None) -> dict:
    """Normalize a source with real alpha; never infer transparency from RGB."""
    source_hash_before = sha256(source)
    with Image.open(source) as opened:
        if "A" not in opened.getbands():
            raise ValueError("Source lacks alpha; background removal requires manual review")
        image = opened.convert("RGBA")
    if crop is not None:
        if len(crop) != 4 or any(not isinstance(value, int) for value in crop):
            raise ValueError("Crop must be four integer coordinates")
        x0, y0, x1, y1 = crop
        if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
            raise ValueError("Crop is outside source bounds")
        image = image.crop(tuple(crop))
    alpha = image.getchannel("A")
    minimum, maximum = alpha.getextrema()
    if minimum == 255 or maximum == 0:
        raise ValueError("Source is opaque or empty; no safe symbol bounds")
    corners = [alpha.getpixel(point) for point in ((0, 0), (image.width - 1, 0),
               (0, image.height - 1), (image.width - 1, image.height - 1))]
    if any(value > ALPHA_THRESHOLD for value in corners):
        raise ValueError("Visible corner pixels suggest a background or cropped symbol")
    mask = alpha.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0)
    bbox = mask.getbbox()
    if not bbox:
        raise ValueError("Visible alpha bounds are empty")
    left, top, right, bottom = bbox
    if min(left, top, image.width - right, image.height - bottom) <= 1:
        raise ValueError("Visible pixels touch the crop boundary; possible accidental cut")
    cropped = image.crop(bbox)
    longest = max(cropped.size)
    target = CANVAS * TARGET_LONG_SIDE
    scale = min(target / longest, MAX_UPSCALE)
    width = max(1, round(cropped.width * scale))
    height = max(1, round(cropped.height * scale))
    resample = Image.Resampling.LANCZOS
    resized = cropped.resize((width, height), resample=resample)
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    x = (CANVAS - width) // 2
    y = (CANVAS - height) // 2
    canvas.alpha_composite(resized, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format="PNG", optimize=True)
    if sha256(source) != source_hash_before:
        raise ValueError("Source bytes changed during processing")
    final_bbox = canvas.getchannel("A").point(lambda value: 255 if value > ALPHA_THRESHOLD else 0).getbbox()
    assert final_bbox is not None
    warnings = []
    if scale == MAX_UPSCALE and longest * scale < target:
        warnings.append("LOW_SOURCE_RESOLUTION")
    if min(width, height) / CANVAS < 0.20:
        warnings.append("NARROW_SYMBOL_OUTLIER")
    return {
        "sourceSha256": source_hash_before,
        "finalSha256": sha256(output),
        "sourceBounds": list(bbox),
        "finalBounds": list(final_bbox),
        "sourceOccupancy": round((right - left) * (bottom - top) / (image.width * image.height), 4),
        "finalOccupancy": round(width * height / (CANVAS * CANVAS), 4),
        "scale": round(scale, 4),
        "resampling": "Pillow LANCZOS",
        "crop": crop,
        "warnings": warnings,
    }


def load_mapping() -> dict:
    if not TTS_MAPPING.exists():
        raise ValueError("Official TTS mapping is missing")
    data = json.loads(TTS_MAPPING.read_text(encoding="utf-8"))
    entries = data.get("factions", [])
    expected = {item["slug"]: item for item in catalog() if item["contentSet"] != "discordant-stars"}
    if data.get("catalogSha256") != sha256(CATALOG_SQL) or len(entries) != 30:
        raise ValueError("Official mapping catalog hash/count differs from current catalog")
    mapped = {item["slug"]: item for item in entries}
    if len(mapped) != 30 or set(mapped) != set(expected):
        raise ValueError("Official mapping slugs differ from current catalog")
    for slug, item in mapped.items():
        if item["name"] != expected[slug]["name"] or item["contentSet"] != expected[slug]["contentSet"]:
            raise ValueError(f"Official mapping identity differs from catalog: {slug}")
    return mapped


def provenance(selection: dict, selected: Path) -> dict:
    """Validate the original artwork behind a selected isolated symbol."""
    origin_data = selection.get("origin")
    derivation = selection.get("derivation")
    if not isinstance(origin_data, dict) or not isinstance(derivation, dict):
        raise ValueError("Every selection requires origin and derivation metadata")
    original = within_root(origin_data["path"])
    if not original.is_file() or sha256(original) != origin_data["sha256"]:
        raise ValueError(f"Original artwork missing or changed: {original}")
    method = derivation.get("method")
    if method == "original-alpha":
        if original != selected or sha256(original) != sha256(selected):
            raise ValueError("original-alpha requires source and original to be the same file")
    elif method == "manual-extraction":
        crop = derivation.get("originalCrop")
        notes = derivation.get("notes")
        if not isinstance(crop, list) or len(crop) != 4 or not all(isinstance(x, int) for x in crop):
            raise ValueError("Manual extraction requires originalCrop coordinates")
        with Image.open(original) as image:
            if not (0 <= crop[0] < crop[2] <= image.width and 0 <= crop[1] < crop[3] <= image.height):
                raise ValueError("Manual extraction crop is outside original image")
        if not isinstance(notes, str) or not notes.strip():
            raise ValueError("Manual extraction requires notes describing the alpha mask/work")
    else:
        raise ValueError("Derivation method must be original-alpha or manual-extraction")
    return {"path": project_path(original), "sha256": sha256(original),
            "derivation": derivation}


def load_extractions() -> dict:
    """Merge the two extraction inventories without maintaining another catalog."""
    extracted = {}
    expected = {item["slug"]: item for item in catalog()}
    for path in (QA_ROOT / "official-extraction.json", QA_ROOT / "discordant-stars-mapping.json"):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("factions", []):
            slug = item["slug"]
            if slug not in expected or slug in extracted:
                raise ValueError(f"Unknown or duplicate extraction slug: {slug}")
            if item.get("name", expected[slug]["name"]) != expected[slug]["name"]:
                raise ValueError(f"Extraction identity differs from catalog: {slug}")
            extracted[slug] = item
    return extracted


def build_extracted(record: dict, extraction: dict) -> None:
    from image_metrics import metrics

    slug = record["slug"]
    source = within_root(extraction["source"])
    isolated = within_root(extraction["intermediate"])
    if not source.is_relative_to(SOURCE_ROOT.resolve()) or not isolated.is_relative_to(INTERMEDIATE_ROOT.resolve()):
        raise ValueError(f"Extraction files outside source/intermediate directories: {slug}")
    group = "discordant-stars" if record["contentSet"] == "discordant-stars" else "official"
    if isolated.name != f"{slug}.png" or isolated.parent != (INTERMEDIATE_ROOT / group).resolve() or source.parent != (SOURCE_ROOT / group).resolve():
        raise ValueError(f"Extraction path identity differs from catalog: {slug}")
    if group == "discordant-stars" and source.stem != slug:
        raise ValueError(f"DS source filename differs from catalog: {slug}")
    if not source.is_file() or sha256(source) != extraction["sourceSha256"]:
        raise ValueError(f"Extracted original source missing/changed: {slug}")
    if not isolated.is_file() or sha256(isolated) != extraction["intermediateSha256"]:
        raise ValueError(f"Isolated intermediate missing/changed: {slug}")
    source_info, intermediate_info = image_info(source), image_info(isolated)
    crop = extraction.get("crop")
    if crop:
        if len(crop) != 4 or not all(isinstance(value, int) for value in crop):
            raise ValueError(f"Invalid original crop: {slug}")
        source_preview = preview_crop(source, PREVIEW_ROOT / "source" / f"{slug}.png",
            {"x": crop[0], "y": crop[1], "width": crop[2] - crop[0], "height": crop[3] - crop[1]})
        record["sourcePreview"] = source_preview
    output = FINAL_ROOT / record["contentSet"] / f"{slug}.png"
    details = normalize(isolated, output)
    intermediate_metrics, final_metrics = metrics(isolated), metrics(output)
    expected_area = intermediate_metrics["weightedAlphaArea"] * details["scale"] ** 2
    area_retention = final_metrics["weightedAlphaArea"] / max(1, expected_area)
    details["areaRetention"] = round(area_retention, 4)
    warning_codes = list(dict.fromkeys(extraction.get("warnings", []) + details["warnings"]
                                     + intermediate_metrics["warnings"] + final_metrics["warnings"]))
    if area_retention < .80 or area_retention > 1.20:
        warning_codes.append("SEVERE_AREA_CHANGE_REVIEW")
    crop_area = (crop[2] - crop[0]) * (crop[3] - crop[1]) if crop else intermediate_info["width"] * intermediate_info["height"]
    foreground_fraction = intermediate_metrics["weightedAlphaArea"] / max(1, crop_area)
    if foreground_fraction < .025 or foreground_fraction > .90:
        warning_codes.append("EXTRACTION_AREA_OUTLIER_REVIEW")
    record.update(source=project_path(source), sourceWidth=source_info["width"], sourceHeight=source_info["height"],
                  sourceMode=source_info["mode"], sourceHasAlpha=source_info["hasAlphaChannel"],
                  sourceTransparent=source_info["hasTransparency"], sourceSha256=sha256(source),
                  intermediate=project_path(isolated), intermediateSha256=sha256(isolated),
                  intermediateWidth=intermediate_info["width"], intermediateHeight=intermediate_info["height"],
                  final=project_path(output), finalSha256=sha256(output), finalWidth=CANVAS, finalHeight=CANVAS,
                  transparent=True, processing=details, sourceKind=extraction.get("sourceKind", "ds" if record["contentSet"] == "discordant-stars" else "token"),
                  status=extraction.get("status", "READY_FOR_REVIEW"), warnings=warning_codes,
                  intermediateMetrics=intermediate_metrics, finalMetrics=final_metrics)
    record["origin"] = {"path": project_path(source), "sha256": sha256(source)}
    record["extraction"] = {"method": extraction.get("method"), "crop": crop,
        "parameters": extraction.get("parameters", {}), "metrics": extraction.get("metrics", {}),
        "foregroundFraction": round(foreground_fraction, 4),
        "originalPath": extraction.get("importSource", extraction.get("original", extraction.get("originalSource", extraction.get("source")))),
        "originalSha256": extraction.get("importSha256", extraction.get("originalSha256", extraction.get("sourceSha256")))}
    record["derivation"] = {"method": "classical-extraction", "originalCrop": crop,
                            "notes": extraction.get("method"), "parameters": extraction.get("parameters", {})}


def build() -> dict:
    QA_ROOT.mkdir(parents=True, exist_ok=True)
    mapping = load_mapping()
    extractions = load_extractions()
    selections = json.loads(SELECTIONS.read_text(encoding="utf-8")) if SELECTIONS.exists() else {}
    unknown = set(selections) - {item["slug"] for item in catalog()}
    if unknown:
        raise ValueError(f"Selections contain unknown slugs: {sorted(unknown)}")
    entries = []
    for faction in catalog():
        slug = faction["slug"]
        content_set = faction["contentSet"]
        record = {**faction, "catalogKey": slug, "source": None, "final": None,
                  "sourceWidth": None, "sourceHeight": None, "finalWidth": None, "finalHeight": None,
                  "transparent": None, "status": "NEEDS_MANUAL_REVIEW", "warnings": [], "processing": None}
        if content_set != "discordant-stars":
            mapped = mapping.get(slug)
            preview = next((candidate for candidate in mapped.get("candidates", [])
                            if candidate["index"] == mapped.get("previewCandidateIndex")), None) if mapped else None
            if preview:
                original = within_root(preview["sourcePath"])
                if not original.is_file() or sha256(original) != preview["sourceSha256"]:
                    raise ValueError(f"Official candidate missing or changed: {slug}")
                copy = SOURCE_ROOT / "official" / f"{slug}{original.suffix.lower()}"
                digest = preserve_source(original, copy)
                info = image_info(copy)
                record.update(source=project_path(copy), sourceWidth=info["width"],
                              sourceHeight=info["height"], sourceSha256=digest,
                              sourceMode=info["mode"], sourceHasAlpha=info["hasAlphaChannel"],
                              sourceTransparent=info["hasTransparency"])
                record["warnings"].append("COMPOSITE_TOKEN_SOURCE_NOT_ISOLATED")
                if mapped.get("previewRoiPixels"):
                    record["previewRoiPixels"] = mapped["previewRoiPixels"]
                    record["preview"] = preview_crop(copy, PREVIEW_ROOT / f"{slug}.png", mapped["previewRoiPixels"])
                record["sourceCandidates"] = len(mapped.get("candidates", []))
            else:
                record["warnings"].append("OFFICIAL_SOURCE_MAPPING_PENDING")
        else:
            record["warnings"].append("DISCORDANT_STARS_SOURCE_UNAVAILABLE")

        selection = selections.get(slug)
        if slug in extractions:
            build_extracted(record, extractions[slug])
        elif selection:
            selected = within_root(selection["source"])
            if not selected.is_relative_to(SOURCE_ROOT.resolve()):
                raise ValueError(f"Selected source is outside the preserved source directory: {selected}")
            if not selected.is_file():
                raise ValueError(f"Selected source missing: {selected}")
            if sha256(selected) != selection["sha256"]:
                raise ValueError(f"Selected source hash mismatch: {selected}")
            lineage = provenance(selection, selected)
            output = FINAL_ROOT / content_set / f"{slug}.png"
            details = normalize(selected, output, selection.get("crop"))
            info = image_info(selected)
            record.update(source=project_path(selected), final=project_path(output),
                          sourceWidth=info["width"], sourceHeight=info["height"],
                          sourceMode=info["mode"], sourceHasAlpha=info["hasAlphaChannel"],
                          sourceTransparent=info["hasTransparency"],
                          sourceSha256=details["sourceSha256"], finalSha256=details["finalSha256"],
                          finalWidth=CANVAS, finalHeight=CANVAS, transparent=True,
                          status="READY_FOR_REVIEW", processing=details)
            record["origin"] = {"path": lineage["path"], "sha256": lineage["sha256"]}
            record["derivation"] = lineage["derivation"]
            record["warnings"] = details["warnings"]
        entries.append(record)
    manifest = {
        "schemaVersion": 1,
        "catalogSource": project_path(CATALOG_SQL),
        "catalogSha256": sha256(CATALOG_SQL),
        "parameters": {"canvas": [CANVAS, CANVAS], "format": "PNG RGBA",
                       "targetLongSideOccupancy": TARGET_LONG_SIDE, "maxUpscale": MAX_UPSCALE,
                       "alphaThreshold": ALPHA_THRESHOLD, "resampling": "Pillow LANCZOS"},
        "counts": {"catalog": len(entries), "mappedSources": sum(bool(e["source"]) for e in entries),
                   "isolated": sum(bool(e.get("intermediate")) for e in entries),
                   "outputs": sum(bool(e["final"]) for e in entries),
                   "readyForReview": sum(e["status"] == "READY_FOR_REVIEW" for e in entries),
                   "needsManualReview": sum(e["status"] == "NEEDS_MANUAL_REVIEW" for e in entries)},
        "factions": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = build()
    print(json.dumps(result["counts"], ensure_ascii=False))
