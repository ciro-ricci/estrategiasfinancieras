#!/usr/bin/env python3
"""
Control de frescura y sanidad de los datos del dashboard (data/*.json).

Corre al final del workflow diario, DESPUES de los scrapers y del commit. Los
scrapers tienen continue-on-error (para que uno caido no frene a los demas),
asi que un fallo de scraper queda silencioso y el dashboard sigue mostrando el
dato viejo (paso con el A3500: el BCRA devolvia 403 y el valor quedo congelado
varios dias sin que nadie se enterara). Este control detecta ese tipo de
problemas mirando el resultado, no los pasos:

  - que cada archivo exista y se pueda leer,
  - que su marca "actualizado" no sea vieja,
  - que la fecha del dato mas reciente no sea vieja,
  - que los valores clave sean numericos y razonables.

Salida: imprime un reporte; si hay algun ERROR sale con codigo 1 (el workflow
lo usa para marcar la corrida como fallida y avisar). Los AVISOS no fallan.

Uso: python3 scripts/verificar_datos.py [--reporte reporte.md]
"""
import json
import sys
from datetime import datetime, timezone, date

DATA = "data"
AHORA = datetime.now(timezone.utc)
HOY = AHORA.date()

errores = []
avisos = []


def err(archivo, msg):
    errores.append(f"{archivo}: {msg}")


def aviso(archivo, msg):
    avisos.append(f"{archivo}: {msg}")


def cargar(nombre):
    try:
        with open(f"{DATA}/{nombre}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        err(nombre, "no existe el archivo")
    except json.JSONDecodeError as e:
        err(nombre, f"JSON invalido ({e})")
    return None


def parse_dt(s):
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def parse_d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def chequear_actualizado(nombre, valor, max_dias, campo="actualizado", como_error=True):
    dt = parse_dt(valor)
    if dt is None:
        err(nombre, f"'{campo}' ausente o ilegible ({valor!r})")
        return
    dias = (AHORA - dt).total_seconds() / 86400
    if dias > max_dias:
        msg = (f"'{campo}' tiene {dias:.1f} dias (maximo {max_dias}). "
               f"El scraper no esta actualizando este archivo.")
        (err if como_error else aviso)(nombre, msg)


def chequear_fecha_dato(nombre, valor, max_dias, que, como_error=True):
    d = parse_d(valor)
    if d is None:
        err(nombre, f"fecha de {que} ausente o ilegible ({valor!r})")
        return
    dias = (HOY - d).days
    if dias > max_dias:
        msg = (f"{que} es del {d.isoformat()} ({dias} dias; maximo {max_dias}). "
               f"El dato esta desactualizado.")
        (err if como_error else aviso)(nombre, msg)


def numero(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x


# ---------------------------------------------------------------------------
def chk_fx_bcra():
    n = "fx_bcra"
    d = cargar(n)
    if not d:
        return
    chequear_actualizado(n, d.get("actualizado"), 2)
    series = d.get("series", {})
    for clave, etiqueta in (("mayorista_a3500", "A3500"), ("oficial_minorista", "Oficial minorista")):
        s = series.get(clave) or []
        if len(s) < 2:
            err(n, f"serie {etiqueta} vacia o con menos de 2 puntos")
            continue
        ult = s[0]
        # fines de semana + feriados largos: hasta 6 dias sin dato nuevo es normal
        chequear_fecha_dato(n, ult.get("fecha"), 6, f"ultimo dato de {etiqueta}")
        v = ult.get("valor")
        if not numero(v) or not (100 < v < 100000):
            err(n, f"valor de {etiqueta} fuera de rango o no numerico ({v!r})")
        elif numero(s[1].get("valor")) and s[1]["valor"] > 0:
            salto = abs(v / s[1]["valor"] - 1)
            if salto > 0.15:
                aviso(n, f"{etiqueta} salto {salto*100:.1f}% contra el dato anterior ({s[1]['valor']} -> {v})")


def chk_futuros():
    n = "futuros_dolar"
    d = cargar(n)
    if not d:
        return
    chequear_actualizado(n, d.get("actualizado"), 2)
    c = d.get("contratos") or []
    if len(c) < 5:
        err(n, f"solo {len(c)} contratos (se esperan al menos 5). Revisar la planilla fuente.")
        return
    malos = [x.get("contrato") for x in c if not numero(x.get("ajuste")) or not (100 < x["ajuste"] < 100000)]
    if malos:
        err(n, f"ajuste no numerico o fuera de rango en: {', '.join(map(str, malos[:5]))}")
    fechas = [parse_d(x.get("fecha_datos")) for x in c if parse_d(x.get("fecha_datos"))]
    if not fechas:
        err(n, "ningun contrato tiene fecha_datos")
    else:
        chequear_fecha_dato(n, max(fechas).isoformat(), 6, "fecha_datos mas reciente")
    if not any((parse_d(x.get("vencimiento")) or date.min) >= HOY for x in c):
        err(n, "todos los contratos estan vencidos")


def chk_fx_financiero():
    n = "fx_financiero"
    d = cargar(n)
    if not d:
        return
    chequear_actualizado(n, d.get("actualizado"), 2)
    mep = (d.get("mep") or {}).get("valor")
    ccl = (d.get("ccl") or {}).get("valor")
    if not numero(mep) or not numero(ccl) or mep <= 0 or ccl <= 0:
        err(n, f"MEP/CCL ausentes o no numericos (mep={mep!r}, ccl={ccl!r})")
    elif not (0.8 < ccl / mep < 1.3):
        aviso(n, f"relacion CCL/MEP inusual ({ccl / mep:.3f})")


def chk_historico():
    n = "fx_historico"
    d = cargar(n)
    if not d:
        return
    chequear_actualizado(n, d.get("actualizado"), 2)
    s = d.get("serie") or []
    if len(s) < 300:
        err(n, f"serie con {len(s)} puntos (se esperan >= 300): se perdio historia")
        return
    chequear_fecha_dato(n, s[-1].get("fecha"), 6, "ultimo punto de la serie")


def chk_bonos():
    n = "bonos"
    d = cargar(n)
    if not d:
        return
    chequear_actualizado(n, d.get("actualizado"), 2)
    cats = d.get("categorias") or {}
    minimos = {"tasa_fija": 3, "cer": 5, "dollar_linked": 2, "soberanos": 3, "on": 15}
    for cat, minimo in minimos.items():
        lista = cats.get(cat) or []
        if len(lista) < minimo:
            err(n, f"categoria '{cat}' con {len(lista)} instrumentos (minimo {minimo})")
            continue
        sin_tir = [x.get("ticker") for x in lista if not numero(x.get("tir"))]
        if len(sin_tir) > len(lista) * 0.5:
            err(n, f"categoria '{cat}': {len(sin_tir)} de {len(lista)} sin TIR numerica")
    on = {x.get("ticker") for x in cats.get("on") or []}
    # tickers que usa la Cartera Recomendada del dashboard
    usados = ["YMCX", "IRCP", "VSCV", "PLC5", "MGCO", "PN35", "TTC9"]
    faltan = [t for t in usados if t not in on]
    if faltan:
        err(n, f"faltan en la hoja de ON tickers que usa la Cartera Recomendada: {', '.join(faltan)}")


def chk_rem():
    n = "rem"
    d = cargar(n)
    if not d:
        return
    chequear_actualizado(n, d.get("actualizado"), 2)
    # El REM es mensual y se publica con rezago: solo aviso si pasa mucho tiempo.
    chequear_fecha_dato(n, d.get("fecha_relevamiento"), 75, "ultimo relevamiento", como_error=False)
    if not (d.get("variables") or {}):
        err(n, "sin variables")


def chk_tasas():
    n = "tasas_referencia"
    d = cargar(n)
    if not d:
        return
    # web: semanal (lunes). pdf: se revisa los dias 1 y 16.
    chequear_actualizado(n, d.get("actualizado_web"), 10, campo="actualizado_web")
    chequear_actualizado(n, d.get("actualizado_pdf"), 25, campo="actualizado_pdf", como_error=False)
    items = d.get("items") or []
    if len(items) < 10:
        err(n, f"solo {len(items)} items (se esperan 13)")
    sin_tna = [i.get("nombre") for i in items if not numero(i.get("tna"))]
    if sin_tna:
        err(n, f"items sin TNA numerica: {', '.join(map(str, sin_tna[:5]))}")


# ---------------------------------------------------------------------------
def main():
    for f in (chk_fx_bcra, chk_futuros, chk_fx_financiero, chk_historico, chk_bonos, chk_rem, chk_tasas):
        try:
            f()
        except Exception as e:  # un control roto no debe tapar a los demas
            err(f.__name__, f"el control fallo con una excepcion: {e!r}")

    lineas = [f"## Control de datos del dashboard ({AHORA.strftime('%Y-%m-%d %H:%M')} UTC)", ""]
    if errores:
        lineas.append(f"### ERRORES ({len(errores)})")
        lineas += [f"- {e}" for e in errores]
        lineas.append("")
    if avisos:
        lineas.append(f"### Avisos ({len(avisos)})")
        lineas += [f"- {a}" for a in avisos]
        lineas.append("")
    if not errores and not avisos:
        lineas.append("Todo en orden: todos los archivos estan frescos y con valores razonables.")
    texto = "\n".join(lineas)
    print(texto)

    if "--reporte" in sys.argv:
        ruta = sys.argv[sys.argv.index("--reporte") + 1]
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto + "\n")

    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
