# Estrategias Financieras

Sitio con landing comercial en la raíz y dashboard financiero (HTML/CSS/JS
embebido en un único archivo, con gate de login vía Netlify Identity) en
`/dashboard`, siguiendo la misma estructura que
[Estrategias al Grano](https://estrategiasalgrano.com/).

## Cómo funciona

1. `index.html` (raíz) es la landing comercial: presentación, último informe,
   comunidad de WhatsApp, planes de asesoramiento. El botón "Ingresar al
   Dashboard" lleva a `/dashboard`.
2. Los scripts en `scripts/` scrapean distintas fuentes públicas y escriben
   archivos JSON en `data/`.
3. `dashboard/index.html` lee esos JSON en el navegador (`fetch`, con rutas
   absolutas `/data/...json`) y renderiza el dashboard.
4. Una tarea programada corre `scripts/run_all.sh` una vez por día (17:00),
   que actualiza los JSON y hace `git commit` + `git push` a `main`.
5. Netlify está conectado a este repo y redeploya automáticamente en cada push
   a `main`. **Nunca se toca Netlify directamente** — todo pasa por GitHub.

## Estructura

```
index.html              -> landing comercial (raíz del sitio)
dashboard/
  index.html             -> dashboard financiero (requiere login, Netlify Identity)
data/
  futuros_dolar.json    -> curva de futuros dólar (Matba Rofex, via Google Sheet pública)
  fx_bcra.json           -> oficial (minorista) y mayorista (A3500), API BCRA
  fx_financiero.json     -> MEP y CCL, via bonistas.com (AL30/GD30 24hs)
  rem.json                -> proyecciones REM (inflación, TAMAR, dólar), BCRA
  bonos.json              -> LECAP/BONCAP (tasa fija), CER, Dollar Linked y Soberanos: bonistas.com. Obligaciones Negociables: planilla propia del usuario
scripts/
  scrape_futuros_dolar.py
  scrape_fx_bcra.py
  scrape_fx_financiero.py
  scrape_rem.py           -> requiere `pip install openpyxl`
  scrape_bonos.py
  run_all.sh              -> corre los 5 scrapers + commit + push
```

## Landing (`index.html`)

Reutiliza el mismo template comercial que ya está en producción en
[estrategiasalgrano.com](https://estrategiasalgrano.com/), con el botón de
"Ingresar al Dashboard" apuntando a `/dashboard` en vez de a otro dominio.
El resto del contenido (marca "Estrategias al Grano", curvas de soja/maíz/trigo
en el mockup, links de WhatsApp e informe en PDF/audio) se dejó igual al
original a pedido del usuario — falta revisar si corresponde adaptarlo a la
temática financiera. La sección de sponsor (Grupo Depetris) se sacó
temporalmente porque falta el archivo de logo.

## Fuentes de datos

| Dato | Fuente | Tipo |
|---|---|---|
| Oficial (minorista) | BCRA API `estadisticas/v4.0/monetarias` (idVariable 4) | Oficial |
| Mayorista / A3500 | BCRA API `estadisticas/v4.0/monetarias` (idVariable 5) | Oficial |
| MEP / CCL | `bonistas.com/api/fx/fx` (AL30/GD30 24hs) | Pública, no documentada — puede cambiar sin aviso |
| Futuros dólar | Google Sheet pública del usuario (Matba Rofex, rezago ~24hs) | Pública |
| Proyecciones REM (inflación, TAMAR, dólar) | BCRA, `historico-relevamiento-expectativas-mercado.xlsx` | Oficial |
| LECAP/BONCAP (tasa fija), CER, Dollar Linked y Soberanos | `bonistas.com/api/bonds` (liquidación 24hs) | Pública, no documentada |
| Obligaciones Negociables (TIR, duration) | Planilla propia del usuario (Google Sheet, pestaña "Corpo AAA") | Privada del usuario, calculada manualmente |

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

## Programar la actualización diaria (17:00)

La actualización diaria corre como una tarea programada de Claude (no un cron
local): clona el repo, corre los 5 scrapers y pushea los cambios a `main` todos
los días a las 17:00.

Para que el `git push` funcione sin pedir usuario/contraseña, el remoto de este
repo debe tener configuradas credenciales (SSH key o Personal Access Token)
en la máquina donde corre la tarea programada.

## Netlify Identity

El gate de login usa Netlify Identity. Para que funcione en producción hay que
habilitar "Identity" en el panel de Netlify del sitio (Site settings → Identity
→ Enable Identity) e invitar a los usuarios que puedan acceder. Mientras el
sitio no esté conectado a Netlify o Identity no esté habilitado, `index.html`
muestra el dashboard directamente sin pedir login (fallback para desarrollo local).
