"""Snapshot/check every imported, preserved source and previous TTS candidate."""
import argparse
import hashlib
import json
from pathlib import Path
from build_assets import ROOT, QA_ROOT


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inventory():
    result = {}
    for folder in ("imports/discordant-stars", "assets/factions/source", "docs/tts-assets-review/candidates"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file():
                result[path.relative_to(ROOT).as_posix()] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    return result


parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("snapshot", "check"))
args = parser.parse_args()
snapshot = QA_ROOT / "source-immutability-baseline.json"
current = inventory()
if args.mode == "snapshot":
    if snapshot.exists():
        raise SystemExit("Baseline exists; refusing to overwrite integrity evidence")
    snapshot.write_text(json.dumps({"scope": "before final extraction/build validation", "files": current}, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"files": len(current), "bytes": sum(x["bytes"] for x in current.values())}))
else:
    baseline = json.loads(snapshot.read_text(encoding="utf-8"))["files"]
    changed = sorted(path for path in set(baseline)|set(current) if baseline.get(path) != current.get(path))
    report = {"ok": not changed, "files": len(current), "changed": changed,
              "scope": "full import archive, all preserved sources, all previous TTS candidates"}
    (QA_ROOT / "source-immutability-report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report))
    raise SystemExit(bool(changed))
