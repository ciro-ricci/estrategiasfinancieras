#!/usr/bin/env python3
"""
Scrapea el REM (Relevamiento de Expectativas de Mercado) del BCRA.
Fuente oficial: historico-relevamiento-expectativas-mercado.xlsx (URL estable,
se actualiza todos los meses con la ultima encuesta incluida), hoja
"Base de Datos Completa".
Salida: data/rem.json (solo las 3 variables usadas en la pestana Proyecciones:
inflacion general, TAMAR, tipo de cambio nominal - ultimo relevamiento disponible).
Usa siempre el consolidado Top 10 (analistas con mejor track record historico),
no el total de participantes.
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

# El archivo del BCRA a veces guarda el periodo mensual como texto libre
# (ej. "sept-26") en lugar de fecha. Mapeo de abreviaturas -> mes (1-12).
MES_ABREV_A_NUM = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12,
}

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
    """Devuelve (tipo, label, anio) legible para un valor de la columna Periodo.
    La columna viene con tipos mezclados segun la fila: datetime, texto tipo
    "sept-26", texto "2026", o "proximos 12/24 meses"."""
    if isinstance(periodo, datetime):
        return "mensual", f"{MESES_ES[periodo.month - 1].capitalize()} {periodo.year}", None

    if isinstance(periodo, str):
        s = periodo.strip()
        low = s.lower()

        if "12 meses" in low:
            return "proximos_12m", "Próx. 12 meses", None
        if "24 meses" in low:
            return "proximos_24m", "Próx. 24 meses", None

        if s.isdigit() and len(s) == 4:
            return "anual", f"Cierre {s}", int(s)

        # formato tipo "sept-26", "ene-27"
        if "-" in low:
            abrev, _, yy = low.partition("-")
            abrev = abrev.strip()
            yy = yy.strip()
            if abrev in MES_ABREV_A_NUM and yy.isdigit():
                anio = 2000 + int(yy) if len(yy) == 2 else int(yy)
                mes_num = MES_ABREV_A_NUM[abrev]
                return "mensual", f"{MESES_ES[mes_num - 1].capitalize()} {anio}", None

    if isinstance(periodo, (int, float)):
        return "anual", f"Cierre {int(periodo)}", int(periodo)

    return "otro", str(periodo), None


def main():
    download()
    wb = openpyxl.load_workbook(TMP_PATH, data_only=True, read_only=True)
    # Se usa siempre el consolidado de los 10 analistas con mejor track record
    # (Top 10), no el total de participantes. OJO: en esta hoja las columnas
    # Promedio y Mediana vienen en orden invertido respecto a "Base de Datos Completa".
    ws = wb["Base Completa TOP-10"]
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
            tipo, label, anio = period_info(r[3], r[2])
            periodos.append({
                "tipo": tipo,
                "periodo": label,
                "anio": anio,
                "referencia": r[2],
                "promedio": r[4],
                "mediana": r[5],
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
        "fuente": "BCRA - REM (historico-relevamiento-expectativas-mercado.xlsx, hoja Base Completa TOP-10)",
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
