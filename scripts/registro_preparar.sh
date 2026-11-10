#!/usr/bin/env bash
# Deixa a pasta ./registro com o branch `registro` (cria órfão se não existir).
set -euo pipefail
URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
if git ls-remote --exit-code --heads "$URL" registro >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch registro "$URL" registro
else
  mkdir registro
  git -C registro init -q -b registro
  git -C registro remote add origin "$URL"
  printf '# Registro\n\nPacotes gerados e conferências. Escrito pelos workflows game-day e conferir.\n' > registro/README.md
fi
