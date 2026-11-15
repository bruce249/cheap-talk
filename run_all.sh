#!/usr/bin/env bash
# Cheap Talk: full pipeline. Needs OPENAI_API_KEY, XAI_API_KEY, HF_TOKEN (only for the providers in models.txt).
# BUDGET caps total spend across pilot + main run (default $3.80).
set -euo pipefail
BUDGET="${BUDGET:-3.8}"
python -m scripts.check_models
python -m src.items
python -m src.build
python -m src.run --budget "$BUDGET"
python -m src.run --budget "$BUDGET" --concurrency 8      # retry pass for any errors
python -m src.score
python -m src.analyze
python -m src.extra
echo "Done. Read results/main_summary.md and figures/. Next: python -m src.label sample --n 60"
