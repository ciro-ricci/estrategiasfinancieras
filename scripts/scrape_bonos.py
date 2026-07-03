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

# Exclusiones pedidas por el usuario para que la curva quede legible (sacan
# outliers de duration muy larga que aplastaban el resto de la escala):
# - tasa fija: se excluye TY30P
# - CER: solo se consideran tickers que empiezan con "T" (se excluyen los
#   "X..." de corto plazo y los bonos viejos tipo DICP/DIP0/PARP/PAP0/CUAP)
TICKERS_EXCLUIDOS = {"tasa_fija": {"TY30P"}, "cer": set()}


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
            ticker = b.get("ticker") or ""
            if ticker in TICKERS_EXCLUIDOS.get(key, set()):
                continue
            if key == "cer" and not ticker.startswith("T"):
                continue
            items.append({
                "ticker": b.get("ticker"),
                "familia": b.get("bond_family"),
                "vencimiento": b.get("end_date"),
                "tna": b.get("tna"),
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
