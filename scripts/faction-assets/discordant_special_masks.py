"""Preview conservative GrabCut masks for five difficult Discordant Stars logos.

This script reads the preserved full-card sources and writes only to
docs/faction-assets-qa/special-preview. It never replaces the main extraction
inventory or any intermediate/final asset. The caller may integrate a reviewed
preview into the primary pipeline after visual QA.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".asset-pipeline-deps"))
import cv2  # noqa: E402


SOURCE_MAPPING = ROOT / "docs/faction-assets-qa/discordant-stars-mapping.json"
OUTPUT_DIR = ROOT / "docs/faction-assets-qa/special-preview"

# Rectangle coordinates are local to each mapping's source crop. They were
# chosen by inspecting the five original reference cards, leaving ample BG
# outside the emblems. No pixel art, geometry, or color is generated.
GRABCUT_RECTS = {
    "the-florzen-profiteers": (85, 150, 580, 590),
    "the-vaylerian-scourge": (100, 120, 540, 620),
    "the-vaden-banking-clans": (90, 190, 590, 570),
    "the-zelian-purifier": (35, 65, 350, 350),
    "the-nokar-sellships": (100, 160, 570, 625),
}

PADDING = 16
MIN_COMPONENT_AREA = 100
ITERATIONS = 8


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def extract(source: Path, crop: list[int], rect: tuple[int, int, int, int]) -> tuple[Image.Image, dict]:
    full = cv2.imread(str(source), cv2.IMREAD_COLOR)
    if full is None:
        raise RuntimeError(f"Cannot decode {source}")
    x0, y0, x1, y1 = crop
    if not (0 <= x0 < x1 <= full.shape[1] and 0 <= y0 < y1 <= full.shape[0]):
        raise RuntimeError(f"Invalid source crop for {source}")
    roi = full[y0:y1, x0:x1].copy()
    rx, ry, rw, rh = rect
    if not (0 < rx < rx + rw < roi.shape[1] and 0 < ry < ry + rh < roi.shape[0]):
        raise RuntimeError(f"Invalid GrabCut rectangle for {source}")

    cv2.setRNGSeed(0)
    mask = np.zeros(roi.shape[:2], np.uint8)
    background_model = np.zeros((1, 65), np.float64)
    foreground_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(roi, mask, rect, background_model, foreground_model, ITERATIONS, cv2.GC_INIT_WITH_RECT)
    foreground = np.isin(mask, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.uint8)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, connectivity=8)
    cleaned = np.zeros_like(foreground)
    kept_components = []
    for index in range(1, count):
        x, y, w, h, area = map(int, stats[index])
        if area >= MIN_COMPONENT_AREA:
            cleaned[labels == index] = 255
            kept_components.append({"x": x, "y": y, "width": w, "height": h, "area": area})
    ys, xs = np.where(cleaned > 0)
    if not len(xs):
        raise RuntimeError(f"No foreground extracted from {source}")
    left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)

    # This 1-pixel alpha treatment keeps source RGB untouched and avoids a
    # hard stair-step edge. Interior pixels remain fully opaque (255).
    soft_alpha = cv2.GaussianBlur(cleaned, (3, 3), 0.55)
    rgb = cv2.cvtColor(roi[top:bottom, left:right], cv2.COLOR_BGR2RGB)
    rgba = np.zeros((bottom - top + 2 * PADDING, right - left + 2 * PADDING, 4), np.uint8)
    rgba[PADDING:-PADDING, PADDING:-PADDING, :3] = rgb
    rgba[PADDING:-PADDING, PADDING:-PADDING, 3] = soft_alpha[top:bottom, left:right]
    result = Image.fromarray(rgba, "RGBA")
    metrics = {
        "sourceCrop": crop,
        "grabCutRectInCrop": list(rect),
        "foregroundBBoxInCrop": [left, top, right, bottom],
        "foregroundBBoxInSource": [x0 + left, y0 + top, x0 + right, y0 + bottom],
        "foregroundPixels": int((cleaned > 0).sum()),
        "foregroundComponents": kept_components,
        "outputWidth": result.width,
        "outputHeight": result.height,
        "alphaExtrema": list(result.getchannel("A").getextrema()),
        "padding": PADDING,
    }
    return result, metrics


def build_contact(entries: list[dict], background: str, destination: Path) -> None:
    canvas = Image.new("RGB", (len(entries) * 260, 280), background)
    draw = ImageDraw.Draw(canvas)
    for index, entry in enumerate(entries):
        picture = Image.open(ROOT / entry["preview"]).convert("RGBA")
        picture.thumbnail((245, 250))
        x = index * 260 + (245 - picture.width) // 2
        y = (250 - picture.height) // 2
        canvas.paste(picture, (x, y), picture)
        draw.text((index * 260 + 4, 255), entry["slug"][:24], fill="white" if background == "#19202a" else "black")
    canvas.save(destination)


def main() -> None:
    mapping = json.loads(SOURCE_MAPPING.read_text(encoding="utf-8"))
    by_slug = {faction["slug"]: faction for faction in mapping["factions"]}
    if len(GRABCUT_RECTS) != 5 or not set(GRABCUT_RECTS).issubset(by_slug):
        raise RuntimeError("Five special-case slugs must exist in DS source inventory")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for slug, rect in GRABCUT_RECTS.items():
        faction = by_slug[slug]
        source = ROOT / faction["source"]
        original = ROOT / faction["importSource"]
        before = sha256(source)
        if before != faction["sourceSha256"] or sha256(original) != faction["importSha256"] or before != sha256(original):
            raise RuntimeError(f"Source/import hash mismatch: {slug}")
        preview, metrics = extract(source, faction["crop"], rect)
        preview_path = OUTPUT_DIR / f"{slug}.png"
        preview.save(preview_path, format="PNG")
        if sha256(source) != before or sha256(original) != before:
            raise RuntimeError(f"Original changed while processing: {slug}")
        entries.append(
            {
                "slug": slug,
                "source": rel(source),
                "sourceSha256": before,
                "original": rel(original),
                "originalSha256": before,
                "preview": rel(preview_path),
                "previewSha256": sha256(preview_path),
                "method": "OpenCV GrabCut rectangle initialization with isolated-component cleanup and 1-pixel alpha smoothing",
                "parameters": {"rect": list(rect), "iterations": ITERATIONS, "minimumComponentArea": MIN_COMPONENT_AREA, "padding": PADDING},
                "metrics": metrics,
                "warnings": ["SOURCE_GLOW_REVIEW"] if slug == "the-vaylerian-scourge" else [],
                "status": "READY_FOR_REVIEW",
            }
        )
    for color, name in (("#e7edf3", "_contact-light.png"), ("#19202a", "_contact-dark.png")):
        build_contact(entries, color, OUTPUT_DIR / name)
    (OUTPUT_DIR / "manifest.json").write_text(json.dumps({"schemaVersion": 1, "factions": entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} non-destructive special-case previews to {rel(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
