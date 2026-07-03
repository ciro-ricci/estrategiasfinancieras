#!/usr/bin/env python3
"""
Scrapea LECAPs/BONCAPs (tasa fija), bonos CER, y bonos soberanos hard-dollar
bajo jurisdiccion local (Ley Argentina) + BOPREAL, desde el endpoint interno
(no documentado) de bonistas.com. Fuente publica, sin login, elegida por
el usuario. Puede cambiar sin aviso.
Convencion: se toma la liquidacion 24hs (mismo criterio que fx_financiero.py).
Para los soberanos y BOPREAL se usa la variante "D" (precio en dolares) de
cada ticker, ya que son bonos hard-dollar y la TIR debe calcularse sobre el
precio en dolares, no en pesos (evita mezclar expectativa de FX en el yield).
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

# Soberanos ley Argentina (variante "D", precio en dolares) + BOPREAL (idem).
SOBERANOS_TICKERS_D = ["AL29D", "AL30D", "AL35D", "AE38D", "AL41D"]
# Excluidos de Soberanos a pedido del usuario.
SOBERANOS_EXCLUIDOS = {"BPA8D", "BPA7D", "BPB7D"}

# Obligaciones Negociables: mismas familias que el resto, liquidacion 24hs.
FAMILIAS["on"] = ["ONS", "ONS-CABLE"]


def build_item(b):
    return {
        "ticker": b.get("ticker"),
        "familia": b.get("bond_family"),
        "vencimiento": b.get("end_date"),
        "tna": b.get("tna"),
        "tir": b.get("tir"),
        "duration": b.get("modified_duration"),
        "precio": b.get("last_price"),
        "paridad": b.get("parity"),
        "descripcion": b.get("short_description"),
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
            ticker = b.get("ticker") or ""
            if ticker in TICKERS_EXCLUIDOS.get(key, set()):
                continue
            if key == "cer" and not ticker.startswith("T"):
                continue
            if key == "on" and not ticker.endswith("D"):
                continue  # solo variante en dolares (igual criterio que Soberanos)
            items.append(build_item(b))
        items.sort(key=lambda x: x["vencimiento"] or "")
        out_cats[key] = items

    # Soberanos ley Argentina (AL29D/AL30D/AL35D/AE38D/AL41D) + BOPREAL variante D,
    # excluyendo las series _PUT (son la opcion, no el bono).
    soberanos = []
    for b in data:
        ticker = b.get("ticker") or ""
        if b.get("settlement") != SETTLEMENT:
            continue
        if not b.get("performing", True):
            continue
        if ticker in SOBERANOS_EXCLUIDOS:
            continue  # excluidos a pedido del usuario
        es_al_arg = ticker in SOBERANOS_TICKERS_D
        es_bopreal_d = b.get("bond_family") == "BOPREAL" and not ticker.endswith("_PUT")
        if es_al_arg or es_bopreal_d:
            soberanos.append(build_item(b))
    soberanos.sort(key=lambda x: x["vencimiento"] or "")
    out_cats["soberanos"] = soberanos

    out = {
        "fuente": "bonistas.com (endpoint interno, no oficial/no documentado), liquidacion 24hs",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "categorias": out_cats,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK: tasa_fija={len(out_cats['tasa_fija'])} cer={len(out_cats['cer'])} soberanos={len(out_cats['soberanos'])}")


if __name__ == "__main__":
    main()
