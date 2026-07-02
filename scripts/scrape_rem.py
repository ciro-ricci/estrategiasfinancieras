#!/usr/bin/env python3
"""
Scrapea el REM (Relevamiento de Expectativas de Mercado) del BCRA.
Fuente oficial: historico-relevamiento-expectativas-mercado.xlsx (URL estable,
se actualiza todos los meses con la ultima encuesta incluida), hoja
"Base de Datos Completa".
Salida: data/rem.json (solo las 3 variables usadas en la pestana Proyecciones:
inflacion general, TAMAR, tipo de cambio nominal - ultimo relevamiento disponible).
"""
import json
import ssl
import urllib.request
from datetime import datetime, timezone

import openpyxl

URL = "https://www.bcra.gob.ar/archivos/Pdfs/PublicacionesEstadisticas/informes/historico-relevamiento-expectativas-mercado.xlsx"
OUT_PATH = "data/rem.json"
TMP_PATH = "/tmp/_rem_historico.xlsx"

VARIABLES = {
    "inflacion": "Precios minoristas (IPC nivel general; INDEC)",
    "tasas": "Tasa de interés (TAMAR)",
    "dolar": "Tipo de cambio nominal",
}

MESES_ES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def download():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=CTX) as resp:
        data = resp.read()
    with open(TMP_PATH, "wb") as f:
        f.write(data)


def period_info(periodo, referencia):
    """Devuelve (tipo, label) legible para un valor de la columna Periodo."""
    if isinstance(periodo, datetime):
        return "mensual", f"{MESES_ES[periodo.month - 1].capitalize()} {periodo.year}"
    if isinstance(periodo, str) and "12 meses" in periodo:
        return "proximos_12m", "Próx. 12 meses"
    if isinstance(periodo, str) and "24 meses" in periodo:
        return "proximos_24m", "Próx. 24 meses"
    if isinstance(periodo, (int, float)):
        return "anual", f"Cierre {int(periodo)}"
    return "otro", str(periodo)


def main():
    download()
    wb = openpyxl.load_workbook(TMP_PATH, data_only=True, read_only=True)
    ws = wb["Base de Datos Completa"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[1]
    body = rows[2:]

    fechas = sorted(set(r[0] for r in body if r[0]))
    ultima_fecha = fechas[-1]

    out_vars = {}
    for key, nombre_var in VARIABLES.items():
        periodos = []
        for r in body:
            if r[0] != ultima_fecha or r[1] != nombre_var:
                continue
            tipo, label = period_info(r[3], r[2])
            periodos.append({
                "tipo": tipo,
                "periodo": label,
                "referencia": r[2],
                "mediana": r[4],
                "promedio": r[5],
                "desvio": r[6],
                "maximo": r[7],
                "minimo": r[8],
                "p90": r[9],
                "p75": r[10],
                "p25": r[11],
                "p10": r[12],
                "participantes": r[13],
            })
        # orden: mensuales primero (ya vienen en orden cronologico en el archivo),
        # despues proximos_12m/24m, despues anuales
        orden_tipo = {"mensual": 0, "proximos_12m": 1, "proximos_24m": 2, "anual": 3, "otro": 4}
        periodos.sort(key=lambda p: orden_tipo.get(p["tipo"], 9))
        out_vars[key] = {"nombre": nombre_var, "periodos": periodos}

    out = {
        "fuente": "BCRA - REM (historico-relevamiento-expectativas-mercado.xlsx, hoja Base de Datos Completa)",
        "fecha_relevamiento": ultima_fecha.strftime("%Y-%m-%d"),
        "actualizado": datetime.now(timezone.utc).isoformat(),
        "variables": out_vars,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"OK: relevamiento {out['fecha_relevamiento']}, variables: {list(out_vars.keys())}")
    for k, v in out_vars.items():
        print(f"  {k}: {len(v['periodos'])} periodos")


if __name__ == "__main__":
    main()
