"""Observable alpha/shape metrics; warnings never remove image components."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".asset-pipeline-deps"))
import cv2
import numpy as np
from PIL import Image


def metrics(path: Path, threshold: int = 8) -> dict:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    alpha = np.asarray(image, dtype=np.uint8)[:, :, 3]
    visible = (alpha > threshold).astype(np.uint8)
    ys, xs = np.nonzero(visible)
    if not len(xs):
        return {"empty": True, "warnings": ["EMPTY_SYMBOL"]}
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1), int(ys.max() + 1)]
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    area = int(visible.sum())
    weighted_area = float(alpha.astype(np.float64).sum() / 255)
    count, labels, stats, centers = cv2.connectedComponentsWithStats(visible, connectivity=8)
    components = sorted([
        {"area": int(stats[i, cv2.CC_STAT_AREA]),
         "bbox": [int(stats[i, 0]), int(stats[i, 1]), int(stats[i, 0] + stats[i, 2]), int(stats[i, 1] + stats[i, 3])],
         "centroid": [round(float(centers[i, 0]), 2), round(float(centers[i, 1]), 2)]}
        for i in range(1, count)
    ], key=lambda item: item["area"], reverse=True)
    largest = components[0]["area"]
    large = [item for item in components if item["area"] >= max(16, largest * .05)]
    tiny = [item for item in components if item["area"] <= 4]
    nonzero = int((alpha > 0).sum())
    fringe = int(((alpha > 0) & (alpha <= 32)).sum()) / max(1, nonzero)
    soft = int(((alpha > threshold) & (alpha < 247)).sum()) / max(1, area)
    warnings = []
    if len(large) > 1:
        warnings.append("MULTIPLE_LARGE_COMPONENTS_REVIEW")
    if len(tiny) > 8:
        warnings.append("TINY_FRAGMENTS_REVIEW")
    if fringe > .18:
        warnings.append("ALPHA_FRINGE_REVIEW")
    if soft > .40:
        warnings.append("SOFT_ALPHA_REVIEW")
    density = area / (width * height)
    if density > .94 and width / image.width > .70 and height / image.height > .70:
        warnings.append("RECTANGULAR_BACKGROUND_REVIEW")
    return {
        "empty": False, "width": image.width, "height": image.height,
        "bounds": bbox, "aspectRatio": round(width / height, 4),
        "visibleArea": area, "weightedAlphaArea": round(weighted_area, 2),
        "alphaOccupancy": round(weighted_area / (image.width * image.height), 4),
        "bboxOccupancy": round(width * height / (image.width * image.height), 4),
        "density": round(density, 4), "alphaFringeRatio": round(fringe, 4),
        "softAlphaRatio": round(soft, 4), "componentCount": len(components),
        "largeComponentCount": len(large), "tinyComponentCount": len(tiny),
        "components": components[:12], "warnings": warnings,
    }
