"""Report visual-weight outliers and render review sheets without altering assets."""
import json
from collections import Counter
from statistics import median
from PIL import Image, ImageDraw
from build_assets import MANIFEST, QA_ROOT, ROOT


def build():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = [e for e in data["factions"] if e.get("final")]
    occupancy = [e["finalMetrics"]["alphaOccupancy"] for e in entries]
    center = median(occupancy) if occupancy else 0
    outliers = []
    for entry in entries:
        metric = entry["finalMetrics"]
        reasons = []
        if metric["alphaOccupancy"] < center * .5:
            reasons.append("alpha area below half the population median")
        if metric["alphaOccupancy"] > center * 2:
            reasons.append("alpha area above twice the population median")
        if metric["aspectRatio"] < .5 or metric["aspectRatio"] > 2:
            reasons.append("elongated geometry")
        if reasons:
            outliers.append({"slug": entry["slug"], "reasons": reasons,
                             "metrics": metric})
    summary = {"counts": data["counts"], "sourceKinds": dict(Counter(e["sourceKind"] for e in entries)),
               "warningsEntries": sum(bool(e["warnings"]) for e in entries),
               "warningCodes": dict(Counter(w for e in entries for w in e["warnings"])),
               "alphaOccupancyMedian": center, "outliers": outliers,
               "resolutionLimited": [e["slug"] for e in entries if e["processing"]["scale"] == 2],
               "decision": "Keep the approved baseline. Outliers require human comparison; do not distort or invent detail."}
    summary["population"] = {}
    for field in ("alphaOccupancy", "bboxOccupancy", "density", "aspectRatio", "weightedAlphaArea"):
        values = [e["finalMetrics"][field] for e in entries]
        summary["population"][field] = {"min": min(values), "median": median(values), "max": max(values)} if values else None
    summary["byContentSet"] = {}
    for group in sorted({e["contentSet"] for e in entries}):
        values = [e["finalMetrics"]["alphaOccupancy"] for e in entries if e["contentSet"] == group]
        summary["byContentSet"][group] = {"count": len(values), "alphaOccupancyMedian": median(values)}
    (QA_ROOT / "visual-consistency.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for label, color, textcolor in (("dark", "#080c12", "white"), ("light", "#f3f2e8", "black")):
        sheet = Image.new("RGB", (1440, ((len(entries)+7)//8)*205), color)
        draw = ImageDraw.Draw(sheet)
        for index, entry in enumerate(entries):
            x, y = index%8*180, index//8*205
            with Image.open(ROOT / entry["final"]) as image:
                image = image.resize((170, 170), Image.Resampling.LANCZOS)
                sheet.paste(image, (x+5, y), image)
            draw.text((x+5, y+174), entry["slug"][:25], fill=textcolor)
            draw.text((x+5, y+188), entry["contentSet"], fill=textcolor)
        sheet.save(QA_ROOT / f"contact-{label}.png")
    print(json.dumps({"outputs": len(entries), "median": center, "outliers": len(outliers)}))


if __name__ == "__main__":
    build()
