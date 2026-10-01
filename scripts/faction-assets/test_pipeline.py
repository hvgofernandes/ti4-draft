"""Local tests for the deterministic image pipeline and current inventory."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_assets import CANVAS, MANIFEST, TTS_MAPPING, catalog, normalize, sha256
from validate_assets import validate


class FactionPipelineTests(unittest.TestCase):
    def test_catalog_has_64_unique_entries(self):
        entries = catalog()
        self.assertEqual(len(entries), 64)
        self.assertEqual(len({item["slug"] for item in entries}), 64)
        self.assertEqual(Counter(item["contentSet"] for item in entries),
                         {"base": 17, "pok": 7, "thunders-edge": 6, "discordant-stars": 34})

    def test_official_mapping_preserves_all_candidates(self):
        mapping = json.loads(TTS_MAPPING.read_text(encoding="utf-8"))
        self.assertEqual(len(mapping["factions"]), 30)
        official_slugs = {item["slug"] for item in catalog() if item["contentSet"] != "discordant-stars"}
        self.assertEqual({item["slug"] for item in mapping["factions"]}, official_slugs)
        self.assertEqual(len({item["slug"] for item in mapping["factions"]}), 30)
        self.assertEqual(sum(len(item["candidates"]) for item in mapping["factions"]), 121)
        self.assertTrue(all(item["selectedSource"] is None for item in mapping["factions"]))
        for faction in mapping["factions"]:
            for candidate in faction["candidates"]:
                source = TTS_MAPPING.parents[2] / candidate["sourcePath"]
                self.assertTrue(source.is_file())
                self.assertEqual(sha256(source), candidate["sourceSha256"])

    def test_alpha_normalization_preserves_shape_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            output = Path(tmp) / "final.png"
            image = Image.new("RGBA", (300, 240), (0, 0, 0, 0))
            ImageDraw.Draw(image).ellipse((50, 60, 250, 180), fill=(20, 120, 240, 255))
            image.save(source)
            before = sha256(source)
            result = normalize(source, output)
            self.assertEqual(sha256(source), before)
            self.assertEqual(result["sourceSha256"], before)
            with Image.open(output) as final:
                self.assertEqual(final.mode, "RGBA")
                self.assertEqual(final.size, (CANVAS, CANVAS))
                self.assertEqual(final.getpixel((0, 0))[3], 0)
                bbox = final.getchannel("A").getbbox()
                self.assertGreater(min(bbox[0], bbox[1], CANVAS - bbox[2], CANVAS - bbox[3]), 20)
                source_ratio = (result["sourceBounds"][2] - result["sourceBounds"][0]) / (result["sourceBounds"][3] - result["sourceBounds"][1])
                final_ratio = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
                self.assertLess(abs(final_ratio / source_ratio - 1), .025)

    def test_opaque_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "opaque.jpg"
            Image.new("RGB", (120, 120), "white").save(source)
            with self.assertRaisesRegex(ValueError, "lacks alpha"):
                normalize(source, Path(tmp) / "result.png")
            rgba = Path(tmp) / "opaque.png"
            Image.new("RGBA", (120, 120), (255, 255, 255, 255)).save(rgba)
            with self.assertRaisesRegex(ValueError, "opaque or empty"):
                normalize(rgba, Path(tmp) / "result.png")

    def test_empty_alpha_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "empty.png"
            Image.new("RGBA", (120, 120), (0, 0, 0, 0)).save(source)
            with self.assertRaisesRegex(ValueError, "opaque or empty"):
                normalize(source, Path(tmp) / "result.png")

    def test_crop_touching_symbol_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            ImageDraw.Draw(image).rectangle((20, 20, 80, 80), fill=(255, 0, 0, 255))
            image.save(source)
            with self.assertRaisesRegex(ValueError, "crop boundary"):
                normalize(source, Path(tmp) / "result.png", [20, 10, 90, 90])

    def test_manifest_and_gallery_are_consistent(self):
        result = validate()
        self.assertTrue(result["ok"], result["errors"])
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        gallery = (MANIFEST.parent / "index.html").read_text(encoding="utf-8")
        self.assertEqual(len(manifest["factions"]), 64)
        self.assertIn("The Arborec", gallery)
        self.assertIn("The Nokar Sellships", gallery)
        self.assertIn("faction-assets-manifest.json", gallery)

    def test_segmentation_metrics_flag_residue_without_changing_pixels(self):
        from image_metrics import metrics
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "components.png"
            image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((10, 10, 40, 40), fill=(255, 255, 255, 255))
            draw.rectangle((70, 70, 85, 85), fill=(255, 255, 255, 255))
            image.save(source)
            before = sha256(source)
            result = metrics(source)
            self.assertEqual(result["componentCount"], 2)
            self.assertIn("MULTIPLE_LARGE_COMPONENTS_REVIEW", result["warnings"])
            self.assertEqual(before, sha256(source))

    def test_gallery_contains_three_stages_and_required_filters(self):
        gallery = (MANIFEST.parent / "index.html").read_text(encoding="utf-8")
        for text in ("SOURCE ORIGINAL", "ISOLATED / INTERMEDIATE", "FINAL NORMALIZED",
                     'data-source="atlas"', 'data-source="token"', 'data-source="ds"',
                     'data-status="ready"', 'data-status="manual"', 'data-status="warnings"'):
            self.assertIn(text, gallery)


if __name__ == "__main__":
    unittest.main(verbosity=2)
