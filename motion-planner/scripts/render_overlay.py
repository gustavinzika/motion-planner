#!/usr/bin/env python3
"""Desenha o manifest em cima da imagem original, para revisão visual.

O overlay é gerado SEMPRE a partir do JSON (nunca à mão), então o que você vê é o
que está no manifest. Ele melhora a inspeção; não prova que as caixas estão certas.

Convenções:
  - caixa de entidade, rotulada E1, E2...  (cor = status do bbox)
  - caixa tracejada fina de região de movimento, rotulada R1, R2...
  - cruz ciano = pivot da região; losango magenta = attachment (ponto de fixação)
  - bbox com status 'unknown' não é desenhada

Uso:
  python render_overlay.py manifest.json imagem.png out/overlay.png
  python render_overlay.py manifest.json imagem.png out/overlay.png --only ship_hull,sail_main
  python render_overlay.py manifest.json imagem.png out/crop.png --crop sail_main --pad 30 --scale 3

Também grava <out>.legend.md com a tabela número -> id -> status -> provenance.
Ampliação usa vizinho mais próximo (NEAREST) para não suavizar pixels.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STATUS_COLOR = {
    "proposed": (255, 170, 0),
    "needs_review": (255, 60, 60),
    "verified": (60, 220, 90),
    "unknown": (150, 150, 150),
}
PIVOT_COLOR = (0, 230, 255)
ATTACH_COLOR = (255, 60, 255)


def get_font(size):
    for candidate in ("DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def point_image_space(pf, owner_bbox):
    if not pf or pf.get("value") is None:
        return None
    x, y = pf["value"]
    if pf.get("space") == "bbox_local":
        if not owner_bbox:
            return None
        return (owner_bbox[0] + x, owner_bbox[1] + y)
    return (x, y)


def dashed_rect(draw, box, color, width=1, dash=8):
    x0, y0, x1, y1 = box
    for x in range(int(x0), int(x1), dash * 2):
        draw.line([(x, y0), (min(x + dash, x1), y0)], fill=color, width=width)
        draw.line([(x, y1), (min(x + dash, x1), y1)], fill=color, width=width)
    for y in range(int(y0), int(y1), dash * 2):
        draw.line([(x0, y), (x0, min(y + dash, y1))], fill=color, width=width)
        draw.line([(x1, y), (x1, min(y + dash, y1))], fill=color, width=width)


def label(draw, xy, text, color, font):
    x, y = xy
    l, t, r, b = draw.textbbox((x, y), text, font=font)
    draw.rectangle([l - 2, t - 1, r + 2, b + 1], fill=(0, 0, 0))
    draw.text((x, y), text, fill=color, font=font)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("--only", help="ids de entidades separados por vírgula (regiões dessas entidades vêm juntas)")
    ap.add_argument("--crop", help="id de entidade: recorta ao redor do bbox")
    ap.add_argument("--pad", type=int, default=24)
    ap.add_argument("--scale", type=int, default=1, help="ampliação inteira, vizinho mais próximo")
    ap.add_argument("--no-regions", action="store_true")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    img = Image.open(args.image).convert("RGB")
    sw, sh = manifest["source"]["width"], manifest["source"]["height"]
    if img.size != (sw, sh):
        raise SystemExit(f"A imagem tem {img.size}, mas o manifest declara {(sw, sh)}. Não é a mesma imagem.")

    entities = manifest["entities"]
    regions = manifest["motion_regions"]
    ent_bbox = {e["id"]: (e["bbox"]["value"] if e["bbox"]["value"] else None) for e in entities}
    only = set(args.only.split(",")) if args.only else None

    canvas = img.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = get_font(max(12, round(sh / 60)))
    legend = ["| # | id | tipo | status | provenance |", "|---|----|------|--------|------------|"]

    for i, e in enumerate(entities, 1):
        if only and e["id"] not in only:
            continue
        b = e["bbox"]
        if b["value"] is None:
            legend.append(f"| E{i} | {e['id']} | entidade | unknown | {b['provenance']} (não desenhada) |")
            continue
        color = STATUS_COLOR.get(b["status"], (255, 255, 255))
        x0, y0, x1, y1 = b["value"]
        draw.rectangle([x0, y0, x1, y1], outline=color + (255,), width=2)
        label(draw, (x0 + 3, y0 + 2), f"E{i}", color, font)
        legend.append(f"| E{i} | {e['id']} | entidade | {b['status']} | {b['provenance']} |")

    if not args.no_regions:
        for j, r in enumerate(regions, 1):
            if only and r["entity_id"] not in only:
                continue
            rb = r["region_bbox"]
            if rb["value"] is not None:
                x0, y0, x1, y1 = rb["value"]
                dashed_rect(draw, (x0, y0, x1, y1), (255, 255, 255, 230), width=1)
                label(draw, (x1 - 3 - font.size * 2, y1 - font.size - 4), f"R{j}", (255, 255, 255), font)
            eb = ent_bbox.get(r["entity_id"])
            piv = point_image_space(r.get("pivot"), eb)
            if piv:
                x, y = piv
                draw.line([(x - 7, y), (x + 7, y)], fill=PIVOT_COLOR + (255,), width=2)
                draw.line([(x, y - 7), (x, y + 7)], fill=PIVOT_COLOR + (255,), width=2)
            att = r.get("attachment")
            if att:
                tgt_bb = ent_bbox.get(att["attach_to"])
                p = point_image_space(att["point"], tgt_bb)
                if p:
                    x, y = p
                    draw.polygon([(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)], outline=ATTACH_COLOR + (255,), fill=ATTACH_COLOR + (110,))
            legend.append(f"| R{j} | {r['id']} (de {r['entity_id']}) | região | {r['region_bbox']['status']} | {r['region_bbox']['provenance']} |")

    if args.crop:
        bb = ent_bbox.get(args.crop)
        if not bb:
            raise SystemExit(f"entidade '{args.crop}' não existe ou não tem bbox")
        x0, y0, x1, y1 = bb
        box = (max(0, x0 - args.pad), max(0, y0 - args.pad), min(sw, x1 + args.pad), min(sh, y1 + args.pad))
        canvas = canvas.crop(box)

    if args.scale > 1:
        canvas = canvas.resize((canvas.width * args.scale, canvas.height * args.scale), Image.NEAREST)

    # faixa de legenda de cores embaixo (só estados; o mapeamento número->id fica no .legend.md)
    bar_h = font.size * 2 + 8
    final = Image.new("RGB", (canvas.width, canvas.height + bar_h), (12, 12, 18))
    final.paste(canvas, (0, 0))
    d2 = ImageDraw.Draw(final)
    x = 8
    items = [(s, c) for s, c in STATUS_COLOR.items()] + [("pivot", PIVOT_COLOR), ("attachment", ATTACH_COLOR)]
    for name, c in items:
        d2.rectangle([x, canvas.height + 8, x + font.size, canvas.height + 8 + font.size], fill=c)
        d2.text((x + font.size + 6, canvas.height + 6), name, fill=(230, 230, 230), font=font)
        x += font.size + 24 + int(d2.textlength(name, font=font))
    d2.text((x + 10, canvas.height + 6), "R = região de movimento (tracejado branco)", fill=(200, 200, 200), font=font)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    final.save(out)
    legend_path = out.with_suffix(".legend.md")
    legend_path.write_text("\n".join(legend) + "\n", encoding="utf-8")
    print(f"overlay: {out} ({final.width}x{final.height})")
    print(f"legenda: {legend_path}")


if __name__ == "__main__":
    main()
