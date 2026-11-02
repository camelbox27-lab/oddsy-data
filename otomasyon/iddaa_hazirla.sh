#!/usr/bin/env bash
# Gunun kuponu, maclari Iddaa bulteniyle eslestiriyor. Bulten bugune ait
# degilse (sabah Wondiyo'dan iddaa'ya basilmadiysa) burada cekilir.
# Sonuc yalnizca bu calismada kullanilir, main'e GONDERILMEZ: sitenin iddaa
# verisine dokunulmasin; o yine Wondiyo'daki iddaa butonuyla guncellenir.
set -uo pipefail

DOSYA="iddaa/gunluk/gunlukmaclar.json"
GUN="$(date +%d.%m.%Y)"
if [ -f "$DOSYA" ] && python3 - "$DOSYA" "$GUN" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
sys.exit(0 if any(r.get("Tarih") == sys.argv[2] for r in d) else 1)
PY
then
  echo "Iddaa bulteni guncel ($GUN)."
  exit 0
fi

echo "Iddaa bulteni bugune ait degil, kupon icin cekiliyor..."
pip install --quiet -r otomasyon/requirements.txt
if ( cd otomasyon && python iddaa_cek.py && python excel_to_json_ci.py iddaa ); then
  echo "Iddaa bulteni cekildi (yalnizca bu calisma icin)."
else
  # Kupon olusmasa da liste ve raporlar gitsin; isi durdurma.
  echo "UYARI: iddaa bulteni cekilemedi; kupon olusmayabilir."
fi
exit 0
