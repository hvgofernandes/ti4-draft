"""Check the delivered gallery and every declared image over local HTTP."""
import json
from urllib.request import Request, urlopen
from urllib.parse import quote
from build_assets import MANIFEST, QA_ROOT

base = "http://127.0.0.1:5173/"
paths = {"docs/faction-assets-qa/", "docs/faction-assets-qa/faction-assets-manifest.json",
         "docs/faction-assets-qa/official-extraction.json", "docs/faction-assets-qa/discordant-stars-mapping.json"}
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
for entry in manifest["factions"]:
    for key in ("source", "intermediate", "final"):
        if entry.get(key):
            paths.add(entry[key])
    for key in ("preview", "sourcePreview"):
        if entry.get(key):
            paths.add(entry[key]["path"])
errors = []
for path in sorted(paths):
    try:
        with urlopen(Request(base + quote(path), method="HEAD"), timeout=30) as response:
            if response.status != 200:
                errors.append({"path": path, "status": response.status})
            if path.endswith(".png") and "image/png" not in response.headers.get("Content-Type", ""):
                errors.append({"path": path, "error": "wrong image content type"})
    except Exception as error:
        errors.append({"path": path, "error": str(error)})
with urlopen(base + "docs/faction-assets-qa/", timeout=30) as response:
    page = response.read().decode("utf-8")
    if "ISOLATED / INTERMEDIATE" not in page:
        errors.append({"error": "HTTP gallery is stale"})
report = {"url": base + "docs/faction-assets-qa/", "checked": len(paths), "errors": errors, "ok": not errors}
(QA_ROOT / "http-report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
print(json.dumps(report))
raise SystemExit(bool(errors))
