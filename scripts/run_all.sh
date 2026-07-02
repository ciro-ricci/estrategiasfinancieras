#!/usr/bin/env bash
# Corre los 3 scrapers, y si algo cambio, commitea y pushea a GitHub.
# Pensado para ejecutarse una vez por dia (ej. 18:00) via cron / Task Scheduler
# en la maquina del usuario. Requiere que este repo ya tenga configuradas
# credenciales de git con permiso de push (ssh key o PAT en el remote).
set -e
cd "$(dirname "$0")/.."

python3 scripts/scrape_futuros_dolar.py
python3 scripts/scrape_fx_bcra.py
python3 scripts/scrape_fx_financiero.py
python3 scripts/scrape_rem.py

if ! git diff --quiet -- data/; then
  git add data/
  git commit -m "data: actualizacion automatica $(date '+%Y-%m-%d %H:%M')"
  git push origin main
  echo "Cambios pusheados a GitHub."
else
  echo "Sin cambios en los datos, no se commitea nada."
fi
