#!/usr/bin/env python3
"""
Mantiene la serie historica diaria de dolar (A3500/Mayorista, MEP, CCL y la
brecha MEP/CCL) en data/fx_historico.json, para el grafico que se abre desde
las tarjetas de la pestana Futuros Dolar.

No scrapea nada por su cuenta: toma el dato del dia que YA dejaron escritos
los scrapers que corren antes en el mismo workflow (data/fx_bcra.json para
A3500/mayorista, data/fx_financiero.json para MEP/CCL) y hace upsert de la
fecha de hoy en la serie historica. Si ya existe una entrada para hoy (por
ejemplo si el workflow se corrio mas de una vez el mismo dia), la
sobreescribe en vez de duplicarla.

Historia base: 2025-08-19 a 2026-08-18, cargada a mano por el usuario a
partir de su propia planilla. De ahi en adelante la serie se reconstruye
sola, un punto por dia.

Salida: data/fx_historico.json
"""
import json
import sys
from datetime import datetime, timezone

FX_BCRA_PATH = "data/fx_bcra.json"
FX_FINANCIERO_PATH = "data/fx_financiero.json"
OUT_PATH = "data/fx_historico.json"


def main():
    with open(FX_BCRA_PATH, "r", encoding="utf-8") as f:
        fx_bcra = json.load(f)
    with open(FX_FINANCIERO_PATH, "r", encoding="utf-8") as f:
        fx_fin = json.load(f)

    a3500_entry = fx_bcra["series"]["mayorista_a3500"][0]
    a3500 = a3500_entry["valor"]
    fecha = a3500_entry["fecha"]  # ya viene en formato YYYY-MM-DD

    mep = fx_fin["mep"]["valor"]
    ccl = fx_fin["ccl"]["valor"]

    if not all(isinstance(v, (int, float)) for v in (a3500, mep, ccl)):
        raise ValueError(
            f"Control interno fallido: algun valor no es numerico "
            f"(a3500={a3500}, mep={mep}, ccl={ccl}). No se actualiza la serie."
        )

    brecha = (ccl / mep - 1) * 100

    with open(OUT_PATH, "r", encoding="utf-8") as f:
        historico = json.load(f)

    nuevo_punto = {
        "fecha": fecha,
        "a3500": round(a3500, 4),
        "mep": round(mep, 4),
        "ccl": round(ccl, 4),
        "brecha_mep_ccl": round(brecha, 1),
    }

    serie = historico.get("serie", [])
    # Upsert: si ya hay un punto con esta fecha, lo reemplaza; si no, lo agrega.
    reemplazado = False
    for i, p in enumerate(serie):
        if p.get("fecha") == fecha:
            serie[i] = nuevo_punto
            reemplazado = True
            break
    if not reemplazado:
        serie.append(nuevo_punto)

    serie.sort(key=lambda p: p["fecha"])
    historico["serie"] = serie
    historico["actualizado"] = datetime.now(timezone.utc).isoformat()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

    print(f"OK: {'actualizado' if reemplazado else 'agregado'} punto {fecha} -> {nuevo_punto}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
