#!/usr/bin/env bash
# Zamanlanmis gunluk calismanin ayni gun ikinci kez yapilmasini onler.
#   $1  : github.event_name
#   YOL : "oncesi" ya da "kayit" -- canli-kayit dalinda bakilacak klasor
# Elle tetiklemede (workflow_dispatch) her zaman calisir.
# Zamanlanmis calismada:
#   - 06:00'dan once calismaz (gece yarisindan sonra tarama yok),
#   - o gunun dosyasi (oncesi/GG.AA.YYYY.json ya da kayit/...) varsa,
#     yani is bugun zaten yapildiysa atlanir.
set -uo pipefail
cikti() { echo "calis=$1" >> "$GITHUB_OUTPUT"; }

if [ "${1:-}" != "schedule" ]; then
  cikti true; exit 0
fi
if [ "$(date +%H)" -lt 6 ]; then
  echo "Saat $(date +%H:%M): gece yarisindan sonra zamanlanmis calisma yok."
  cikti false; exit 0
fi
DOSYA="${YOL}/$(date +%d.%m.%Y).json"
if gh api "repos/${GITHUB_REPOSITORY}/contents/${DOSYA}?ref=canli-kayit" --silent 2>/dev/null; then
  echo "Bugun zaten yapilmis (${DOSYA} var), atlaniyor."
  cikti false
else
  echo "Bugun henuz yapilmamis (${DOSYA} yok), calisiyor."
  cikti true
fi
