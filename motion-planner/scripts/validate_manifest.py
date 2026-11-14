#!/usr/bin/env python3
"""Valida um manifest de plano de movimento.

Faz duas coisas:
  1. Valida a estrutura contra schema/manifest.schema.json (se `jsonschema` estiver instalado).
  2. Roda checagens semânticas que JSON Schema não expressa: referências, ciclos,
     limites da imagem, regras de `verified`, bob duplicado entre pai e filho.

JSON válido prova estrutura, NÃO qualidade visual. Este script não olha a imagem.

Uso:
  python validate_manifest.py manifest.json [--schema ../schema/manifest.schema.json]

Saída: erros (exit 1) e avisos (exit 0). Imprime também um resumo de pendências.
"""
import argparse
import json
import sys
from pathlib import Path

TRACKED_ENTITY_FIELDS = ("transform_parent", "draw_order", "bbox")
INHERITED_PRESETS = {"bob", "roll", "sway_body"}  # movimentos de corpo que filhos herdam via transform_parent


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_schema(manifest, schema_path):
    try:
        import jsonschema
    except ImportError:
        return [], ["jsonschema não instalado: validação estrutural pulada (pip install jsonschema). Checagens semânticas rodaram."]
    schema = load(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(manifest), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "(raiz)"
        errors.append(f"schema: {loc}: {err.message}")
    return errors, []


def check_tracked(label, field, errors, warnings, null_is_meaningful=False):
    """Regras de status/provenance/value para qualquer campo rastreado.

    null_is_meaningful=True é para campos em que null é um valor legítimo
    (transform_parent: null = raiz). Nos demais, null significa 'não sei' e exige status unknown."""
    if not isinstance(field, dict):
        return
    status = field.get("status")
    prov = field.get("provenance")
    value = field.get("value")
    if status == "unknown" and value is not None:
        errors.append(f"{label}: status 'unknown' exige value null")
    if not null_is_meaningful and status != "unknown" and value is None and "value" in field:
        errors.append(f"{label}: value null exige status 'unknown' (não finja um valor)")
    if status == "verified":
        if prov not in ("measured", "human"):
            errors.append(f"{label}: 'verified' exige provenance measured ou human (veio '{prov}')")
        if not field.get("evidence"):
            errors.append(f"{label}: 'verified' exige campo evidence")
    if prov == "measured" and not field.get("evidence"):
        warnings.append(f"{label}: provenance 'measured' sem evidence (diga qual ferramenta mediu)")


def check_bbox(label, bbox_field, width, height, errors):
    v = bbox_field.get("value") if isinstance(bbox_field, dict) else None
    if v is None:
        return None
    x0, y0, x1, y1 = v
    if not (x0 < x1 and y0 < y1):
        errors.append(f"{label}: bbox invalida (precisa x0<x1 e y0<y1): {v}")
        return None
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        errors.append(f"{label}: bbox fora da imagem {width}x{height}: {v}")
    return v


def to_image_space(point_field, owner_bbox):
    if not point_field or point_field.get("value") is None:
        return None
    x, y = point_field["value"]
    if point_field.get("space") == "bbox_local":
        if owner_bbox is None:
            return None
        return (owner_bbox[0] + x, owner_bbox[1] + y)
    return (x, y)


def inside(pt, bbox, tol):
    return (bbox[0] - tol <= pt[0] <= bbox[2] + tol) and (bbox[1] - tol <= pt[1] <= bbox[3] + tol)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--schema", default=str(Path(__file__).resolve().parent.parent / "schema" / "manifest.schema.json"))
    args = ap.parse_args()

    manifest = load(args.manifest)
    errors, warnings = check_schema(manifest, args.schema)

    src = manifest.get("source", {})
    width, height = src.get("width", 0), src.get("height", 0)
    entities = manifest.get("entities", [])
    regions = manifest.get("motion_regions", [])

    # ids únicos
    ent_ids, reg_ids = {}, {}
    for e in entities:
        if e["id"] in ent_ids:
            errors.append(f"entity '{e['id']}': id duplicado")
        ent_ids[e["id"]] = e
    for r in regions:
        if r["id"] in reg_ids:
            errors.append(f"region '{r['id']}': id duplicado")
        reg_ids[r["id"]] = r

    # entidades: campos rastreados, bbox, pai
    ent_bbox = {}
    for e in entities:
        eid = e["id"]
        for fname in TRACKED_ENTITY_FIELDS:
            check_tracked(f"entity '{eid}'.{fname}", e.get(fname), errors, warnings,
                          null_is_meaningful=(fname == "transform_parent"))
        ent_bbox[eid] = check_bbox(f"entity '{eid}'.bbox", e.get("bbox"), width, height, errors)
        parent = (e.get("transform_parent") or {}).get("value")
        if parent is not None and parent not in ent_ids:
            errors.append(f"entity '{eid}': transform_parent '{parent}' não existe")
        for occ in e.get("occluded_by", []):
            if occ not in ent_ids:
                errors.append(f"entity '{eid}': occluded_by '{occ}' não existe")
        if e.get("visibility") == "partial" and not e.get("occluded_by"):
            warnings.append(f"entity '{eid}': visibility 'partial' sem occluded_by (o que esconde a parte faltante?)")
        mask = e.get("mask")
        if mask:
            check_tracked(f"entity '{eid}'.mask", mask, errors, warnings)
            if not Path(args.manifest).resolve().parent.joinpath(mask["path"]).exists():
                warnings.append(f"entity '{eid}': mask.path '{mask['path']}' não encontrado ao lado do manifest")

    # oclusão coerente: quem oculta precisa ser desenhado depois (draw_order maior)
    for e in entities:
        mine = (e.get("draw_order") or {}).get("value")
        for occ in e.get("occluded_by", []):
            theirs = (ent_ids.get(occ, {}).get("draw_order") or {}).get("value")
            if mine is not None and theirs is not None and theirs <= mine:
                warnings.append(
                    f"entity '{e['id']}': occluded_by '{occ}', mas '{occ}' é desenhado antes ou junto "
                    f"(draw_order {theirs} <= {mine}). Ordem errada ou a entidade '{occ}' precisa ser dividida (layer_split)."
                )

    # ciclos em transform_parent
    for e in entities:
        seen, cur = [], e["id"]
        while cur is not None:
            if cur in seen:
                errors.append(f"ciclo em transform_parent: {' -> '.join(seen + [cur])}")
                break
            seen.append(cur)
            cur = (ent_ids.get(cur, {}).get("transform_parent") or {}).get("value")

    # regiões
    regions_by_entity = {}
    for r in regions:
        rid, eid = r["id"], r["entity_id"]
        regions_by_entity.setdefault(eid, []).append(r)
        if eid not in ent_ids:
            errors.append(f"region '{rid}': entity_id '{eid}' não existe")
            continue
        rb = check_bbox(f"region '{rid}'.region_bbox", r.get("region_bbox"), width, height, errors)
        check_tracked(f"region '{rid}'.region_bbox", r.get("region_bbox"), errors, warnings)
        m = r.get("motion", {})
        check_tracked(f"region '{rid}'.motion", {"status": m.get("status"), "provenance": m.get("provenance"),
                                                  "value": "x", "evidence": m.get("evidence")}, errors, warnings)
        eb = ent_bbox.get(eid)
        if rb and eb and not (eb[0] <= rb[0] and eb[1] <= rb[1] and rb[2] <= eb[2] and rb[3] <= eb[3]):
            warnings.append(f"region '{rid}': region_bbox sai do bbox da entidade '{eid}'")
        pivot = r.get("pivot")
        if pivot:
            check_tracked(f"region '{rid}'.pivot", pivot, errors, warnings)
            pt = to_image_space(pivot, eb)
            if pt and rb and not inside(pt, rb, tol=0.15 * max(rb[2] - rb[0], rb[3] - rb[1])):
                warnings.append(f"region '{rid}': pivot {pt} longe da região {rb}")
        att = r.get("attachment")
        if att:
            check_tracked(f"region '{rid}'.attachment", att["point"], errors, warnings)
            tgt = att["attach_to"]
            if tgt not in ent_ids:
                errors.append(f"region '{rid}': attach_to '{tgt}' não existe")
            else:
                pt = to_image_space(att["point"], ent_bbox.get(tgt))
                tb = ent_bbox.get(tgt)
                if pt and tb and not inside(pt, tb, tol=0.05 * max(tb[2] - tb[0], tb[3] - tb[1])):
                    warnings.append(f"region '{rid}': attachment {pt} fora do bbox de '{tgt}' {tb}")
        for c in r.get("coupling", []):
            if c["region_id"] not in reg_ids:
                errors.append(f"region '{rid}': coupling aponta região '{c['region_id']}' que não existe")
        if m.get("preset") == "custom" and not m.get("note"):
            warnings.append(f"region '{rid}': preset 'custom' sem note explicando")

    # movimento duplicado: pai e descendente com o mesmo movimento de corpo
    for r in regions:
        preset = r["motion"].get("preset")
        if preset not in INHERITED_PRESETS or r["entity_id"] not in ent_ids:
            continue
        cur = (ent_ids[r["entity_id"]].get("transform_parent") or {}).get("value")
        while cur is not None:
            for anc in regions_by_entity.get(cur, []):
                if anc["motion"].get("preset") == preset:
                    warnings.append(
                        f"region '{r['id']}': '{preset}' duplicado com '{anc['id']}' (ancestral '{cur}'). "
                        "Filhos herdam via transform_parent; remova ou torne independente de propósito."
                    )
            cur = (ent_ids.get(cur, {}).get("transform_parent") or {}).get("value")

    # limites
    limits = manifest.get("limits", {})
    if manifest.get("scope") == "planning_only" and limits.get("render_ready") is not False:
        errors.append("limits.render_ready deve ser false em planning_only")
    if limits.get("human_review_performed") is False:
        for e in entities:
            for fname in TRACKED_ENTITY_FIELDS:
                f = e.get(fname) or {}
                if f.get("provenance") == "human":
                    errors.append(f"entity '{e['id']}'.{fname}: provenance 'human' mas human_review_performed é false")

    # resumo
    status_count = {}
    for e in entities:
        for fname in TRACKED_ENTITY_FIELDS:
            s = (e.get(fname) or {}).get("status", "?")
            status_count[s] = status_count.get(s, 0) + 1
    need_mask = [r["id"] for r in regions if "mask" in r.get("requires", []) and not (ent_ids.get(r["entity_id"], {}).get("mask"))]

    print(f"manifest: {args.manifest}")
    print(f"imagem: {width}x{height} | entidades: {len(entities)} | regiões de movimento: {len(regions)}")
    print(f"campos críticos das entidades por status: {status_count}")
    print(f"regiões que precisam de máscara e não têm: {len(need_mask)}")
    for w in warnings:
        print(f"AVISO: {w}")
    for e in errors:
        print(f"ERRO: {e}")
    print(f"resultado: {len(errors)} erro(s), {len(warnings)} aviso(s)")
    print("Lembrete: validação estrutural não prova qualidade visual; confira o overlay.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
