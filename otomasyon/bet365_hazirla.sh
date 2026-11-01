#!/usr/bin/env bash
# Bugunun bet365 verisi (bet365/GGAAYYYY.json) yoksa ceker ve main'e gonderir.
# Tahmin butonlari (mac oncesi + canli) bu dosyaya bagli; boylece sabah
# Wondiyo'dan bet365 butonuna basmak zorunlu olmaz.
# Dosya varsa hicbir sey yapmaz (oranlar o sabahki cekimden kullanilir).
set -euo pipefail

DOSYA="bet365/$(date +%d%m%Y).json"
if [ -f "$DOSYA" ]; then
  echo "bet365 verisi hazir: $DOSYA"
  exit 0
fi

echo "Bugunun bet365 verisi yok, Flashscore'dan cekiliyor..."
pip install --quiet -r otomasyon/requirements.txt
(
  cd otomasyon
  python bet365_cek.py
  python excel_to_json_ci.py bet365 "$(date +%Y-%m-%d)"
)

if [ ! -f "$DOSYA" ]; then
  echo "HATA: bet365 verisi cekilemedi."
  exit 1
fi

git config user.name  "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add bet365/
if git diff --cached --quiet; then
  exit 0
fi
git commit -q -m "veri: bet365 guncellendi (tahmin, $(date +'%d.%m.%Y %H:%M'))"
for deneme in 1 2 3 4; do
  if git push -q origin HEAD:main; then
    echo "bet365 verisi main'e gonderildi."
    exit 0
  fi
  git pull -q --rebase origin main || true
  sleep $((deneme * 3))
done
# Gonderilemese de veri bu calismada kullanilabilir; isi durdurma.
echo "UYARI: bet365 verisi main'e gonderilemedi (bu calismada yine kullanilacak)."
