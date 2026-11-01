"""Canli mac takibi icin: akislarda hangi alanlar var, onu raporlar.

Amac: "dk 15, skor 1-1" gibi bir bildirim kurabilmek icin CANLI maclarda
dakika ve anlik skorun hangi alanda geldigini tespit etmek.

Iki kaynak birden denenir:
  - Flashscore gun akisi (zaten kullandigimiz kaynak)
  - vd.mackolik.com/livedata (engellenmemis, canli veri icin tasarlanmis)

Veri yazmaz, sadece rapor basar.
"""
import collections
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
import flashscore_kaynak as fk           # noqa: E402
import requests                          # noqa: E402

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def flashscore():
    print("=" * 66)
    print("  FLASHSCORE gun akisi")
    print("=" * 66)
    k = fk.FlashscoreKaynak()
    try:
        maclar = k.gunun_maclari(0)
    except Exception as e:
        print(f"  alinamadi: {e}")
        return
    print(f"  bugun {len(maclar)} mac")

    durum = collections.Counter(m.get("AB") for m in maclar)
    print(f"  AB dagilimi: {dict(durum)}   (1=baslamamis, 3=bitmis beklenir)")

    canli = [m for m in maclar
             if not fk.mac_baslamadi_mi(m) and not fk.mac_bitti_mi(m)]
    bitmis = [m for m in maclar if fk.mac_bitti_mi(m)]
    print(f"  canli gorunen: {len(canli)} | bitmis: {len(bitmis)}")

    # Skor/dakika adayi alanlar: tum maclarda hangi anahtarlar var
    anahtarlar = collections.Counter()
    for m in maclar:
        for a, v in m.items():
            if not a.startswith("_") and v not in (None, ""):
                anahtarlar[a] += 1
    print(f"  dolu anahtarlar (anahtar: kac macta): "
          f"{dict(sorted(anahtarlar.items()))}")

    def tek_satir(m, etiket):
        # Tek satirda bas: log kuyrugu kesse bile ortadan bolunmesin
        alanlar = " ".join(f"{a}={v}" for a, v in sorted(m.items())
                           if not a.startswith("_") and v not in (None, "")
                           and len(str(v)) < 30)
        print(f"\n  [{etiket}] {m.get('AE')} - {m.get('AF')} :: {alanlar}")

    for m in canli[:3]:
        tek_satir(m, "CANLI")
    if not canli:
        print("\n  (su an canli mac yok)")
    for m in bitmis[:1]:
        tek_satir(m, "BITMIS")
    baslamamis = [m for m in maclar if fk.mac_baslamadi_mi(m)]
    for m in baslamamis[:1]:
        tek_satir(m, "BASLAMAMIS")


def mackolik():
    print()
    print("=" * 66)
    print("  MACKOLIK livedata")
    print("=" * 66)
    gun = dt.date.today()
    try:
        y = requests.get("https://vd.mackolik.com/livedata",
                         params={"date": f"{gun:%d/%m/%Y}"},
                         headers={"User-Agent": UA, "Accept": "*/*"},
                         timeout=30)
        y.raise_for_status()
        maclar = y.json().get("m", [])
    except Exception as e:
        print(f"  alinamadi: {e}")
        return
    print(f"  {len(maclar)} mac, dizi uzunlugu "
          f"{sorted({len(m) for m in maclar if isinstance(m, list)})}")

    # Skor gibi duran alanlari ara: tam sayi ya da '1-1' bicimi
    ornek = [m for m in maclar if isinstance(m, list) and len(m) > 22][:400]
    doluluk = collections.Counter()
    for m in ornek:
        for i, v in enumerate(m):
            if v not in (None, "", "0.0"):
                doluluk[i] += 1
    print("  dolu olan alanlar (konum: kac macta):")
    print("   ", dict(sorted(doluluk.items())))

    # Baslamis gorunen maclari hedefle: [6]/[7] yalnizca bir kisminda dolu,
    # bunlar buyuk olasilikla skor. Bos ve dolu ornekleri yan yana basiyoruz.
    def bos_mu(v):
        return v in (None, "", 0, "0", "0.0")

    baslamis = [m for m in ornek
                if not bos_mu(m[6]) or not bos_mu(m[7])
                or any(not bos_mu(m[i]) for i in range(8, 14))]
    print(f"\n  baslamis/bitmis gorunen: {len(baslamis)} / {len(ornek)}")

    def dok(m, baslik):
        print(f"\n  --- {baslik}: {m[2]} - {m[4]}  ({m[16]})")
        for i, v in enumerate(m):
            if bos_mu(v):
                continue
            print(f"      [{i:2d}] {str(v)[:90]}")

    for m in baslamis[:4]:
        dok(m, "BASLAMIS")
    if not baslamis:
        print("  (su an baslamis mac yok, maç saatinde tekrar bak)")
    for m in ornek[:1]:
        dok(m, "BASLAMAMIS (karsilastirma)")


if __name__ == "__main__":
    flashscore()
    mackolik()
