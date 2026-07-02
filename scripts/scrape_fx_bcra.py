#!/usr/bin/env python3
"""
Scrapea tipo de cambio oficial (minorista) y mayorista (A3500) desde la API oficial del BCRA.
Fuente: https://api.bcra.gob.ar/estadisticas/v4.0/monetarias (idVariable 4 y 5)
Salida: data/fx_bcra.json
"""
import json
import ssl
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
SERIES = {
    "oficial_minorista": 4,
    "mayorista_a3500": 5,
}
OUT_PATH = "data/fx_bcra.json"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch_serie(id_variable, limit=90):
    url = f"{BASE}/{id_variable}?limit={limit}"
    with urllib.request.urlopen(url, timeout=30, context=CTX) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["results"][0]["detalle"]


def main():
    out = {"actualizado": datetime.now(timezone.utc).isoformat(), "series": {}}
    for nombre, id_var in SERIES.items():
        out["series"][nombre] = fetch_serie(id_var)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("OK:", {k: v[0] for k, v in out["series"].items()})


if __name__ == "__main__":
    main()
