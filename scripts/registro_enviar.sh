#!/usr/bin/env bash
# Faz commit e push da pasta ./registro no branch `registro` (só se houver mudança).
set -euo pipefail
cd registro
git config user.email "actions@github.com"
git config user.name "Bot Loterias"
git add -A
if git diff --staged --quiet; then
  echo "Nada novo para registrar."
  exit 0
fi
git commit -q -m "Registro: $1 ($(date -u +'%Y-%m-%d %H:%M') UTC)"
for i in 1 2 3; do
  git push origin HEAD:registro && exit 0
  git pull --rebase origin registro || true
done
exit 1
