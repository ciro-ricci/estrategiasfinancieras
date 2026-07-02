#!/usr/bin/env python3
"""
Scrapea la curva de futuros de dolar desde la Google Sheet publica del usuario.
Fuente: Google Sheet (rezago ~24hs) -> export gviz/tq CSV, sin login.
Salida: data/futuros_dolar.json
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

SHEET_ID = "1j-ZrWBO-fCkGUPqWtWRsGgGswMRCm2mnMhsPmX6osLI"
GID = "2027743157"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={GID}"

OUT_PATH = "data/futuros_dolar.json"


def parse_number(raw):
    if raw is None or raw.strip() in ("", "N/A"):
        return None
    return float(raw.strip().replace(".", "").replace(",", "."))


def parse_date(raw):
    raw = raw.strip()
    try:
        return datetime.strptime(raw, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def main():
    with urllib.request.urlopen(URL, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    reader = csv.reader(io.StringIO(raw))
    rows = [r for r in reader if r]
    header = rows[0]
    data_rows = rows[1:]

    contratos = []
    for row in data_rows:
        if len(row) < 13:
            continue
        contrato, vto, producto, margen, moneda, tipo, putcall, ajuste, vol, oi, var_oi, fecha_datos, fecha_act = row[:13]

        if tipo.strip() != "Futuro":
            continue  # opciones se dejan para otra pestana

        contratos.append({
            "contrato": contrato.strip(),
            "vencimiento": parse_date(vto),
            "producto": producto.strip(),
            "moneda": moneda.strip(),
            "ajuste": parse_number(ajuste),
            "volumen": parse_number(vol),
            "interes_abierto": parse_number(oi),
            "fecha_datos": parse_date(fecha_datos),
        })

    contratos.sort(key=lambda c: c["vencimiento"] or "")

    out = {
        "fuente": "Google Sheet publica (Matba Rofex, rezago ~24hs)",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "contratos": contratos,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK: {len(contratos)} contratos escritos en {OUT_PATH}")


if __name__ == "__main__":
    main()
