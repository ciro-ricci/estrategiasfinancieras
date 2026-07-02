#!/usr/bin/env python3
"""
Scrapea MEP y CCL desde el endpoint interno (no documentado) de bonistas.com.
Fuente publica, sin login, elegida por el usuario. Puede cambiar sin aviso -
si falla, revisar si cambio la forma de bonistas.com de exponer sus datos.
Convencion: MEP de referencia = AL30 24hs, CCL de referencia = GD30 24hs.
Salida: data/fx_financiero.json
"""
import json
import urllib.request
from datetime import datetime, timezone

URL = "https://bonistas.com/api/fx/fx"
OUT_PATH = "data/fx_financiero.json"

REF_MEP_TICKER = "AL30_24hs"
REF_CCL_TICKER = "GD30_24hs"


def main():
    with urllib.request.urlopen(URL, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    por_ticker = {item["ticker"]: item for item in data}

    mep = por_ticker.get(REF_MEP_TICKER, {}).get("mep_last")
    ccl = por_ticker.get(REF_CCL_TICKER, {}).get("cable")

    out = {
        "fuente": "bonistas.com (endpoint interno, no oficial/no documentado)",
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "mep": {"valor": mep, "ticker_referencia": REF_MEP_TICKER},
        "ccl": {"valor": ccl, "ticker_referencia": REF_CCL_TICKER},
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK: MEP={mep} CCL={ccl}")


if __name__ == "__main__":
    main()
