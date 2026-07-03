#!/usr/bin/env python3
"""
Scrapea LECAPs/BONCAPs (tasa fija) y bonos CER desde el endpoint interno
(no documentado) de bonistas.com. Fuente publica, sin login, elegida por
el usuario. Puede cambiar sin aviso.
Convencion: se toma la liquidacion 24hs (mismo criterio que fx_financiero.py).
Salida: data/bonos.json
"""
import json
import urllib.request
from datetime import datetime, timezone

URL = "https://bonistas.com/api/bonds"
OUT_PATH = "data/bonos.json"
SETTLEMENT = "24hs"

FAMILIAS = {
    "tasa_fija": ["LETRAS-FIJO", "BONO-FIJA"],
    "cer": ["LETRAS-CER", "BONO-CER"],
}


def main():
    with urllib.request.urlopen(URL, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    out_cats = {}
    for key, familias in FAMILIAS.items():
        items = []
        for b in data:
            if b.get("bond_family") not in familias:
                continue
            if b.get("settlement") != SETTLEMENT:
                continue
            if not b.get("performing", True):
                continue
            items.append({
                "ticker": b.get("ticker"),
                "familia": b.get("bond_family"),
                "vencimiento": b.get("end_date"),
                "tir": b.get("tir"),
                "duration": b.get("modified_duration"),
                "precio": b.get("last_price"),
                "paridad": b.get("parity"),
                "descripcion": b.get("short_description"),
            })
        items.sort(key=lambda x: x["vencimiento"] or "")
        out_cats[key] = items

    out = {
        "fuente": "bonistas.com (endpoint interno, no oficial/no documentado), liquidacion 24hs",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "categorias": out_cats,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK: tasa_fija={len(out_cats['tasa_fija'])} cer={len(out_cats['cer'])}")


if __name__ == "__main__":
    main()
