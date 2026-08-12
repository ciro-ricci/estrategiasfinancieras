#!/usr/bin/env python3
"""
Actualiza los items "fuente": "web" de data/tasas_referencia.json (BADLAR y
Adelantos en cuenta desde la API oficial del BCRA, Caucion desde el indice
publico de BYMA). Corre una vez por semana (lunes), no a diario, porque estas
tasas de referencia no varian tanto intradia como el dolar.

Los items "fuente": "pdf" de ese mismo archivo (Documentos a sola firma,
Documentos descontados, Cheque pago diferido, y todo el bloque de creditos
bancarios/productivos) NO se tocan aca: se actualizan aparte, cuando sale un
informe nuevo, porque no tienen fuente publica scrapeable.

Fuentes:
- BCRA: https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{idVariable}
  - BADLAR de bancos privados: idVariable 7
  - Adelantos en cuenta corriente (acuerdo 1-7 dias, >=10M, sector privado): idVariable 145
- BYMA (portal de datos abiertos, sin login): POST a
  https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/getBymaIndexsMep
  - Indice de tasa de caucion a 1 dia: symbol "IDXCAUTIONB"

Control interno: antes de escribir, valida que los 3 valores sean numeros
positivos dentro de un rango de sanidad. Si algo falla, no sobreescribe el
JSON y termina con error (para que la corrida programada quede marcada
como fallida en vez de publicar datos incorrectos o vacios en silencio).

Salida: data/tasas_referencia.json (solo pisa los items fuente="web")
"""
import json
import ssl
import sys
import urllib.request
from datetime import datetime, timezone

OUT_PATH = "data/tasas_referencia.json"

BCRA_BASE = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
BCRA_SERIES = {
    "BADLAR": 7,
    "Adelantos en cuenta": 145,
}

BYMA_URL = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/getBymaIndexsMep"

VALOR_MIN = 0.1
VALOR_MAX = 200  # las tasas de este bloque son TNA en % (no precios en pesos)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def fetch_bcra(id_variable):
    url = f"{BCRA_BASE}/{id_variable}?limit=1"
    with urllib.request.urlopen(url, timeout=30, context=CTX) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["results"][0]["detalle"][0]["valor"]


def fetch_byma_caucion():
    req = urllib.request.Request(
        BYMA_URL,
        data=json.dumps({}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Origin": "https://open.bymadata.com.ar",
            "Referer": "https://open.bymadata.com.ar/",
            "User-Agent": "Mozilla/5.0 (compatible; estrategiasfinancieras-bot/1.0)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30, context=CTX) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    for item in data.get("data", []):
        if item.get("symbol") == "IDXCAUTIONB":
            return item.get("price")
    raise ValueError("No se encontro IDXCAUTIONB en la respuesta de BYMA")


def validar_valor(nombre, valor):
    if valor is None:
        raise ValueError(f"Control interno fallido: no se encontro valor para {nombre}.")
    if not (VALOR_MIN < valor < VALOR_MAX):
        raise ValueError(
            f"Control interno fallido: {nombre}={valor} esta fuera del rango de "
            f"sanidad ({VALOR_MIN}-{VALOR_MAX}). No se publica."
        )


def main():
    badlar = fetch_bcra(BCRA_SERIES["BADLAR"])
    adelantos = fetch_bcra(BCRA_SERIES["Adelantos en cuenta"])
    caucion = fetch_byma_caucion()

    validar_valor("BADLAR", badlar)
    validar_valor("Adelantos en cuenta", adelantos)
    validar_valor("Caución", caucion)

    nuevos_valores = {
        "BADLAR": badlar,
        "Adelantos en cuenta": adelantos,
        "Caución": caucion,
    }

    with open(OUT_PATH, "r", encoding="utf-8") as f:
        out = json.load(f)

    actualizados = []
    for item in out.get("items", []):
        if item.get("fuente") == "web" and item.get("nombre") in nuevos_valores:
            item["tna"] = round(nuevos_valores[item["nombre"]], 2)
            actualizados.append(item["nombre"])

    faltantes = set(nuevos_valores) - set(actualizados)
    if faltantes:
        raise ValueError(
            f"Control interno fallido: no se encontraron en el JSON los items "
            f"{faltantes} con fuente='web'. Revisar data/tasas_referencia.json."
        )

    out["actualizado_web"] = datetime.now(timezone.utc).isoformat()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK: {nuevos_valores}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, urllib.error.URLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
