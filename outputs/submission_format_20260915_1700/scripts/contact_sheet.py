#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--thumb-width", type=int, default=520)
    ap.add_argument("--columns", type=int, default=2)
    args = ap.parse_args()
    items = []
    for path in args.images:
        image = Image.open(path).convert("RGB")
        height = round(image.height * args.thumb_width / image.width)
        image = image.resize((args.thumb_width, height))
        items.append((Path(path).name, image))
    label_h = 34
    cell_h = max(im.height for _, im in items) + label_h
    rows = (len(items) + args.columns - 1) // args.columns
    sheet = Image.new("RGB", (args.columns * args.thumb_width, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(items):
        x = (i % args.columns) * args.thumb_width
        y = (i // args.columns) * cell_h
        draw.text((x + 8, y + 8), label, fill="black")
        sheet.paste(im, (x, y + label_h))
    sheet.save(args.output)


if __name__ == "__main__":
    main()
