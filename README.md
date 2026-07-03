# Estrategias Financieras

Dashboard financiero estático (un único `index.html` con HTML/CSS/JS embebido),
con gate de login vía Netlify Identity, siguiendo la misma estructura que
[Estrategias al Grano](https://estrategiasalgrano.com/).

## Cómo funciona

1. Los scripts en `scripts/` scrapean distintas fuentes públicas y escriben
   archivos JSON en `data/`.
2. `index.html` lee esos JSON en el navegador (`fetch`) y renderiza el dashboard.
3. Una tarea programada en tu máquina corre `scripts/run_all.sh` una vez por día
   (18:00), que actualiza los JSON y hace `git commit` + `git push` a `main`.
4. Netlify está conectado a este repo y redeploya automáticamente en cada push
   a `main`. **Nunca se toca Netlify directamente** — todo pasa por GitHub.

## Estructura

```
index.html              -> dashboard (single file)
data/
  futuros_dolar.json    -> curva de futuros dólar (Matba Rofex, via Google Sheet pública)
  fx_bcra.json           -> oficial (minorista) y mayorista (A3500), API BCRA
  fx_financiero.json     -> MEP y CCL, via bonistas.com (AL30/GD30 24hs)
  rem.json                -> proyecciones REM (inflación, TAMAR, dólar), BCRA
  bonos.json              -> LECAP/BONCAP (tasa fija) y CER, bonistas.com
scripts/
  scrape_futuros_dolar.py
  scrape_fx_bcra.py
  scrape_fx_financiero.py
  scrape_rem.py           -> requiere `pip install openpyxl`
  scrape_bonos.py
  run_all.sh              -> corre los 5 scrapers + commit + push
```

## Fuentes de datos

| Dato | Fuente | Tipo |
|---|---|---|
| Oficial (minorista) | BCRA API `estadisticas/v4.0/monetarias` (idVariable 4) | Oficial |
| Mayorista / A3500 | BCRA API `estadisticas/v4.0/monetarias` (idVariable 5) | Oficial |
| MEP / CCL | `bonistas.com/api/fx/fx` (AL30/GD30 24hs) | Pública, no documentada — puede cambiar sin aviso |
| Futuros dólar | Google Sheet pública del usuario (Matba Rofex, rezago ~24hs) | Pública |
| Proyecciones REM (inflación, TAMAR, dólar) | BCRA, `historico-relevamiento-expectativas-mercado.xlsx` | Oficial |
| LECAP/BONCAP (tasa fija), CER, Soberanos y Obligaciones Negociables | `bonistas.com/api/bonds` (liquidación 24hs) | Pública, no documentada |

## Correr los scrapers localmente

Requiere Python 3 (sin dependencias externas, solo librería estándar).

```bash
pip install openpyxl  # solo necesario para scrape_rem.py
python3 scripts/scrape_futuros_dolar.py
python3 scripts/scrape_fx_bcra.py
python3 scripts/scrape_fx_financiero.py
python3 scripts/scrape_rem.py
python3 scripts/scrape_bonos.py
```

O todo junto (incluye commit + push si hay cambios):

```bash
bash scripts/run_all.sh
```

## Programar la actualización diaria (18:00)

**Windows (Task Scheduler):**
Crear una tarea que ejecute `bash scripts/run_all.sh` (via Git Bash o WSL)
todos los días a las 18:00, con "Start in" apuntando a la carpeta del repo.

**macOS/Linux (cron):**
```
0 18 * * 1-5 cd /ruta/al/repo && bash scripts/run_all.sh >> /ruta/al/repo/logs/cron.log 2>&1
```

Para que el `git push` funcione sin pedir usuario/contraseña, el remoto de este
repo debe tener configuradas credenciales (SSH key o Personal Access Token)
en la máquina donde corre la tarea programada.

## Netlify Identity

El gate de login usa Netlify Identity. Para que funcione en producción hay que
habilitar "Identity" en el panel de Netlify del sitio (Site settings → Identity
→ Enable Identity) e invitar a los usuarios que puedan acceder. Mientras el
sitio no esté conectado a Netlify o Identity no esté habilitado, `index.html`
muestra el dashboard directamente sin pedir login (fallback para desarrollo local).
