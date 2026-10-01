"""Generate compact visual review sheets for Discordant Stars intermediates."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
MAPPING = ROOT / "docs" / "faction-assets-qa" / "discordant-stars-mapping.json"
ENTRIES = json.loads(MAPPING.read_text(encoding="utf-8"))["factions"]
TILE_W, TILE_H = 224, 248
COLS = 6

for theme, background, foreground in (
    ("light", (224, 224, 224, 255), (15, 15, 15)),
    ("dark", (28, 32, 42, 255), (240, 240, 240)),
):
    rows = (len(ENTRIES) + COLS - 1) // COLS
    sheet = Image.new("RGBA", (COLS * TILE_W, rows * TILE_H), background)
    draw = ImageDraw.Draw(sheet)
    for index, entry in enumerate(ENTRIES):
        x = index % COLS * TILE_W
        y = index // COLS * TILE_H
        image = Image.open(ROOT / entry["intermediate"]).convert("RGBA")
        image.thumbnail((204, 204), Image.Resampling.LANCZOS)
        sheet.alpha_composite(image, (x + (TILE_W - image.width) // 2, y + 8 + (204 - image.height) // 2))
        label = entry["slug"].replace("the-", "", 1)
        if len(label) > 25:
            label = label[:24] + "…"
        draw.text((x + 8, y + 219), label, fill=foreground)
    output = ROOT / "docs" / "faction-assets-qa" / f"discordant-contact-{theme}.png"
    sheet.convert("RGB").save(output, optimize=True)
    print(output)
