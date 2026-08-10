#!/usr/bin/env python3
"""
Scrapea MEP y CCL desde el endpoint interno (no documentado) de bonistas.com.
Fuente publica, sin login, elegida por el usuario. Puede cambiar sin aviso -
si falla, revisar si cambio la forma de bonistas.com de exponer sus datos.
Convencion: MEP de referencia = AL30 CI, CCL de referencia = AL30 24hs.
Alineado con la propia pagina de bonistas.com (seccion "Variables de
Referencia" -> "Dolar MEP: Dolar Bolsa AL30 CI" / "Dolar CCL: Contado con
Liquidacion AL30"). Antes se usaba AL30 24hs para el MEP y GD30 24hs para
el CCL, lo que generaba una diferencia de varios pesos contra los valores
que bonistas.com muestra como MEP/CCL oficiales.

Control interno: antes de escribir el JSON de salida, el script valida que
los tickers de referencia sean efectivamente del bono AL30 y que los valores
obtenidos sean numeros positivos dentro de un rango razonable. Si algo de
esto falla, el script NO sobreescribe data/fx_financiero.json y termina con
error (para que la corrida programada quede marcada como fallida en vez de
publicar un dato incorrecto o desactualizado en silencio).
Salida: data/fx_financiero.json
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone

URL = "https://bonistas.com/api/fx/fx"
OUT_PATH = "data/fx_financiero.json"

REF_MEP_TICKER = "AL30_CI"
REF_CCL_TICKER = "AL30_24hs"

# Rango de sanidad para MEP/CCL en pesos. Ajustar si la macro cambia mucho,
# pero sirve como red de seguridad ante datos corruptos o tickers erroneos.
VALOR_MIN = 100
VALOR_MAX = 10000

# Divergencia maxima tolerada entre MEP y CCL. Historicamente estan cerca;
# una diferencia enorme suele indicar que se esta leyendo el bono equivocado.
MAX_DIVERGENCIA_PCT = 0.15


def validar_ticker_al30(nombre, ticker):
    if not ticker.startswith("AL30"):
        raise ValueError(
            f"Control interno fallido: {nombre}='{ticker}' no corresponde "
            f"al bono AL30. Se espera siempre usar AL30 como referencia "
            f"(ver docstring). Revisar REF_MEP_TICKER/REF_CCL_TICKER."
        )


def validar_valor(nombre, valor):
    if valor is None:
        raise ValueError(
            f"Control interno fallido: no se encontro valor para {nombre} "
            f"en la respuesta de bonistas.com (posible cambio de ticker o "
            f"de formato del endpoint)."
        )
    if not (VALOR_MIN < valor < VALOR_MAX):
        raise ValueError(
            f"Control interno fallido: {nombre}={valor} esta fuera del "
            f"rango de sanidad ({VALOR_MIN}-{VALOR_MAX}). No se publica."
        )


def main():
    validar_ticker_al30("REF_MEP_TICKER", REF_MEP_TICKER)
    validar_ticker_al30("REF_CCL_TICKER", REF_CCL_TICKER)

    with urllib.request.urlopen(URL, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    por_ticker = {item["ticker"]: item for item in data}

    mep = por_ticker.get(REF_MEP_TICKER, {}).get("mep_last")
    ccl = por_ticker.get(REF_CCL_TICKER, {}).get("cable")

    validar_valor("MEP", mep)
    validar_valor("CCL", ccl)

    divergencia = abs(ccl - mep) / mep
    if divergencia > MAX_DIVERGENCIA_PCT:
        raise ValueError(
            f"Control interno fallido: MEP={mep} y CCL={ccl} divergen "
            f"{divergencia:.1%}, mas del {MAX_DIVERGENCIA_PCT:.0%} tolerado. "
            f"Posible ticker equivocado en el endpoint de bonistas.com. "
            f"No se publica el dato."
        )

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
    try:
        main()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
