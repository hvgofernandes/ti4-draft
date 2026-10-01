"""Audit faction assets and report incomplete work separately from hard errors."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from build_assets import ALPHA_THRESHOLD, CANVAS, CATALOG_SQL, FINAL_ROOT, INTERMEDIATE_ROOT, MANIFEST, PREVIEW_ROOT, ROOT, TTS_MAPPING, catalog, sha256, within_root


def validate(require_complete: bool = False) -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = {item["slug"]: item for item in catalog()}
    entries = data["factions"]
    errors: list[str] = []
    warnings: list[str] = []
    if sha256(CATALOG_SQL) != data.get("catalogSha256"):
        errors.append("Catalog migration changed after manifest generation")
    if len(entries) != 64 or len({entry["slug"] for entry in entries}) != 64:
        errors.append("Manifest must have 64 distinct slugs")
    if {entry["slug"] for entry in entries} != set(expected):
        errors.append("Manifest slugs differ from catalog")
    if Counter(entry["contentSet"] for entry in entries) != Counter(item["contentSet"] for item in expected.values()):
        errors.append("Manifest content set counts differ from catalog")
    mapping = json.loads(TTS_MAPPING.read_text(encoding="utf-8")) if TTS_MAPPING.exists() else {"factions": []}
    official = {item["slug"]: item for item in mapping["factions"]}
    candidate_hashes: dict[str, set[str]] = defaultdict(set)
    for faction in mapping["factions"]:
        for candidate in faction["candidates"]:
            if not candidate.get("atlas"):
                candidate_hashes[candidate["sourceSha256"]].add(faction["slug"])
    shared_candidates = [
        {"sha256": digest, "slugs": sorted(slugs)}
        for digest, slugs in candidate_hashes.items() if len(slugs) > 1
    ]
    hashes: dict[str, list[str]] = defaultdict(list)
    source_count = final_count = isolated_count = 0
    for entry in entries:
        slug = entry["slug"]
        if slug not in expected:
            continue
        if entry["name"] != expected[slug]["name"] or entry["contentSet"] != expected[slug]["contentSet"]:
            errors.append(f"Catalog mismatch: {slug}")
        source_text = entry.get("source")
        if source_text:
            source = within_root(source_text)
            if not source.is_file():
                errors.append(f"Missing source: {slug}")
            elif sha256(source) != entry.get("sourceSha256"):
                errors.append(f"Source hash mismatch: {slug}")
            else:
                source_count += 1
                with Image.open(source) as image:
                    if image.size != (entry["sourceWidth"], entry["sourceHeight"]):
                        errors.append(f"Source dimensions mismatch: {slug}")
        else:
            warnings.append(f"Source unavailable: {slug}")
        if slug in official:
            mapped = official[slug]
            candidate = next((item for item in mapped["candidates"] if item["index"] == mapped["previewCandidateIndex"]), None)
            if not candidate:
                errors.append(f"Official preview candidate missing from mapping: {slug}")
            else:
                original = within_root(candidate["sourcePath"])
                copy = ROOT / "assets/factions/source/official" / f"{slug}{original.suffix.lower()}"
                if not original.is_file() or not copy.is_file() or sha256(original) != candidate["sourceSha256"] or sha256(copy) != sha256(original):
                    errors.append(f"TTS candidate or preserved copy changed: {slug}")
            preview = entry.get("preview")
            if not preview:
                errors.append(f"Official inspection preview missing: {slug}")
            else:
                preview_path = within_root(preview["path"])
                if not preview_path.is_relative_to(PREVIEW_ROOT.resolve()) or preview_path.name != f"{slug}.png":
                    errors.append(f"Preview path is unsafe or mismatched: {slug}")
                elif not preview_path.is_file() or sha256(preview_path) != preview["sha256"]:
                    errors.append(f"Inspection preview missing or changed: {slug}")
                else:
                    with Image.open(preview_path) as image:
                        if image.size != (preview["width"], preview["height"]):
                            errors.append(f"Inspection preview dimensions mismatch: {slug}")
        intermediate = entry.get("intermediate")
        if intermediate:
            isolated = within_root(intermediate)
            if not isolated.is_file() or sha256(isolated) != entry.get("intermediateSha256"):
                errors.append(f"Intermediate missing or changed: {slug}")
            else:
                isolated_count += 1
                if isolated.name != f"{slug}.png" or not isolated.is_relative_to(INTERMEDIATE_ROOT.resolve()):
                    errors.append(f"Intermediate path identity mismatch: {slug}")
                with Image.open(isolated) as image:
                    extrema = image.getchannel("A").getextrema() if image.mode == "RGBA" else (255, 0)
                    if image.mode != "RGBA" or extrema[0] != 0 or extrema[1] <= ALPHA_THRESHOLD:
                        errors.append(f"Intermediate lacks usable transparency: {slug}")
                    bounds = image.getchannel("A").getbbox()
                    if not bounds or min(bounds[0], bounds[1], image.width-bounds[2], image.height-bounds[3]) < 2:
                        errors.append(f"Intermediate crop touches symbol: {slug}")
        extraction = entry.get("extraction")
        if extraction:
            original = within_root(extraction["originalPath"])
            if not original.is_file() or sha256(original) != extraction["originalSha256"]:
                errors.append(f"Extraction original changed: {slug}")
        preview = entry.get("sourcePreview")
        if preview:
            preview_path = within_root(preview["path"])
            if preview_path.parent != (PREVIEW_ROOT / "source").resolve() or preview_path.name != f"{slug}.png":
                errors.append(f"Source ROI preview path mismatch: {slug}")
            elif not preview_path.is_file() or sha256(preview_path) != preview["sha256"]:
                errors.append(f"Source ROI preview changed: {slug}")
        if entry["status"] not in ("READY_FOR_REVIEW", "NEEDS_MANUAL_REVIEW"):
            errors.append(f"Unexpected approval status: {slug}")
        final_text = entry.get("final")
        if not final_text:
            warnings.append(f"Final asset pending: {slug}")
            continue
        origin = entry.get("origin")
        derivation = entry.get("derivation")
        if not origin or not derivation:
            errors.append(f"Final provenance missing: {slug}")
        else:
            original = within_root(origin["path"])
            if not original.is_file() or sha256(original) != origin["sha256"]:
                errors.append(f"Original provenance hash mismatch: {slug}")
        final = within_root(final_text)
        if not final.is_relative_to(FINAL_ROOT.resolve()) or final.name != f"{slug}.png":
            errors.append(f"Unsafe or mismatched final path: {slug}")
            continue
        if not final.is_file():
            errors.append(f"Missing final image: {slug}")
            continue
        digest = sha256(final)
        hashes[digest].append(slug)
        if digest != entry.get("finalSha256"):
            errors.append(f"Final hash mismatch: {slug}")
        final_count += 1
        with Image.open(final) as image:
            if image.mode != "RGBA" or image.size != (CANVAS, CANVAS):
                errors.append(f"Final format/dimensions mismatch: {slug}")
                continue
            alpha = image.getchannel("A")
            minimum, maximum = alpha.getextrema()
            if maximum == 0 or minimum == 255:
                errors.append(f"Final alpha missing or empty: {slug}")
            bbox = alpha.point(lambda value: 255 if value > ALPHA_THRESHOLD else 0).getbbox()
            if not bbox:
                errors.append(f"Empty visible bounds: {slug}")
            else:
                x0, y0, x1, y1 = bbox
                if min(x0, y0, CANVAS - x1, CANVAS - y1) < 8:
                    errors.append(f"Final bounds touch canvas edge: {slug}")
                longest = max(x1 - x0, y1 - y0) / CANVAS
                if longest < .35:
                    warnings.append(f"Small visible symbol: {slug}")
                if longest > .85:
                    warnings.append(f"Large visible symbol: {slug}")
                processing = entry.get("processing") or {}
                if list(bbox) != processing.get("finalBounds"):
                    errors.append(f"Final bounding box mismatch: {slug}")
                src_bounds = processing.get("sourceBounds")
                if src_bounds:
                    original_ratio = (src_bounds[2] - src_bounds[0]) / (src_bounds[3] - src_bounds[1])
                    final_ratio = (x1 - x0) / (y1 - y0)
                    if abs(final_ratio / original_ratio - 1) > .025:
                        errors.append(f"Aspect ratio appears deformed: {slug}")
    for digest, slugs in hashes.items():
        if len(slugs) > 1:
            errors.append(f"Identical final images across factions: {', '.join(slugs)} ({digest[:12]})")
    actual = {path.resolve() for path in FINAL_ROOT.rglob("*.png")} if FINAL_ROOT.exists() else set()
    declared = {within_root(entry["final"]) for entry in entries if entry.get("final")}
    for extra in sorted(actual - declared):
        errors.append(f"Final file has no catalog slug: {extra.relative_to(ROOT)}")
    actual_isolated = {path.resolve() for path in INTERMEDIATE_ROOT.rglob("*.png")} if INTERMEDIATE_ROOT.exists() else set()
    declared_isolated = {within_root(entry["intermediate"]) for entry in entries if entry.get("intermediate")}
    for extra in sorted(actual_isolated - declared_isolated):
        errors.append(f"Intermediate file has no catalog slug: {extra.relative_to(ROOT)}")
    actual_previews = {path.resolve() for path in PREVIEW_ROOT.rglob("*.png")} if PREVIEW_ROOT.exists() else set()
    declared_previews = {within_root(entry[key]["path"]) for entry in entries for key in ("preview", "sourcePreview") if entry.get(key)}
    for extra in sorted(actual_previews - declared_previews):
        errors.append(f"Preview file has no catalog slug: {extra.relative_to(ROOT)}")
    gallery = MANIFEST.parent / "index.html"
    if not gallery.is_file() or "id=\"grid\"" not in gallery.read_text(encoding="utf-8"):
        errors.append("QA gallery missing or invalid")
    if require_complete and (source_count, isolated_count, final_count) != (64, 64, 64):
        errors.append(f"Expected 64 sources/intermediates/finals, found {source_count}/{isolated_count}/{final_count}")
    return {"ok": not errors, "complete": final_count == 64, "sources": source_count,
            "isolated": isolated_count, "outputs": final_count, "missingSources": 64 - source_count,
            "candidateWarningEntries": sum(bool(entry.get("warnings")) for entry in entries),
            "candidateWarningCodes": dict(Counter(w for entry in entries for w in entry.get("warnings", []))),
            "missingFinals": [entry["slug"] for entry in entries if not entry.get("final")],
            "sharedCandidateImages": shared_candidates, "errors": errors, "warnings": warnings}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = validate(args.require_complete)
    (MANIFEST.parent / "qa-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**result, "warnings": result["warnings"][:8],
                      "missingFinals": f"{len(result['missingFinals'])} entries",
                      "warningCount": len(result["warnings"])}, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)
