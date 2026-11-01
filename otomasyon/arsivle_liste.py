"""Gunun Ilk Yari Gol listesini arsive kopyalar.

NEDEN: data/halfTimeGoals.json her calismada uzerine yazilyor. Ertesi gun
"dun hangi maclari vermistik, kaci tuttu" sorusunu cevaplayabilmek icin
listenin o gunku hali saklanmali.

Arsiv: data/gecmis/halfTimeGoals_GG.AA.YYYY.json
Tarih kayitlarin kendi 'tarih' alanindan okunur; dosya hangi gune aitse
o isimle saklanir (calisma saati degil).

Var olan bir arsiv dosyasinin uzerine yazilir: ayni gun birden fazla kez
BULTEN YUKLE'ye basilirsa en son liste gecerlidir.
"""
import collections
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
KAYNAK = KOK / "data" / "halfTimeGoals.json"
ARSIV = KOK / "data" / "gecmis"
TUT_GUN = 60          # bu kadar gunden eski arsivler silinir


def main():
    if not KAYNAK.exists():
        print("[arsiv] halfTimeGoals.json yok, atlandi.")
        return 0
    try:
        kayitlar = json.loads(KAYNAK.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[arsiv] okunamadi: {e}")
        return 0
    if not kayitlar:
        print("[arsiv] liste bos, arsivlenmedi.")
        return 0

    # Kayitlarin cogunlukla hangi tarihe ait oldugunu al
    sayac = collections.Counter(
        (k.get("tarih") or "").strip() for k in kayitlar if k.get("tarih"))
    if not sayac:
        print("[arsiv] kayitlarda tarih yok, arsivlenmedi.")
        return 0
    tarih = sayac.most_common(1)[0][0]

    ARSIV.mkdir(parents=True, exist_ok=True)
    hedef = ARSIV / f"halfTimeGoals_{tarih}.json"
    shutil.copyfile(KAYNAK, hedef)
    print(f"[arsiv] {hedef.name} ({len(kayitlar)} mac)")

    # Eski arsivleri temizle; depo surekli sismesin
    simdi = dt.date.today()
    silinen = 0
    for d in ARSIV.glob("halfTimeGoals_*.json"):
        try:
            g = dt.datetime.strptime(d.stem.split("_", 1)[1], "%d.%m.%Y").date()
        except (ValueError, IndexError):
            continue
        if (simdi - g).days > TUT_GUN:
            d.unlink()
            silinen += 1
    if silinen:
        print(f"[arsiv] {silinen} eski dosya silindi ({TUT_GUN} gunden eski)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
