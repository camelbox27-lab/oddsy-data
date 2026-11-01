"""Canli maclarda Flashscore istatistik akisi: xG / tempo verisi var mi?

Gun akisi (f_1_...) yalnizca skor ve durum tasiyor. Mac basina ayri bir
istatistik akisi (df_st_1_<kod>) var; bu script canli maclar icin onu
okur ve:
  - hangi istatistiklerin geldigini (sut, isabetli sut, tehlikeli atak,
    xG ...) ilk yari / mac bolumleriyle basar,
  - incelenen canli maclarin kacinda xG, kacinda sut verisi oldugunu sayar.
Buyuk ligler one alinir (xG kapsami orada beklenir).

Veri yazmaz, sadece rapor basar.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
import flashscore_kaynak as fk           # noqa: E402

BUYUK = ("ENGLAND", "SPANIEN", "ITALIEN", "DEUTSCHLAND", "FRANKREICH",
         "NIEDERLANDE", "PORTUGAL", "TÜRKEI", "BELGIEN", "SCHOTTLAND",
         "DÄNEMARK", "SCHWEDEN", "ÖSTERREICH", "SCHWEIZ", "NORWEGEN")
INCELE = 30          # kapsam sayimi icin en fazla bu kadar canli mac
DOK = 4              # tam istatistigi basilacak mac sayisi


def coz(metin):
    kayitlar = []
    for kayit in metin.split("¬~"):
        d = {}
        for alan in kayit.split("¬"):
            if "÷" in alan:
                k, v = alan.split("÷", 1)
                d[k] = v
        if d:
            kayitlar.append(d)
    return kayitlar


def istatistikler(kayitlar):
    """[(bolum, ad, ev, dep)] -- bolum basligi SE, satirlar SG/SH/SI."""
    bolum, sonuc = None, []
    for d in kayitlar:
        if "SE" in d:
            bolum = d["SE"]
        if "SG" in d:
            sonuc.append((bolum, d["SG"], d.get("SH"), d.get("SI")))
    return sonuc


def main():
    k = fk.FlashscoreKaynak()
    maclar = k.gunun_maclari(0)
    canli = [m for m in maclar if m.get("AB") == "2"]
    canli.sort(key=lambda m: (not (m.get("_lig") or "").upper().startswith(BUYUK),
                              m.get("_lig") or ""))
    print(f"canli mac: {len(canli)}, incelenecek: {min(INCELE, len(canli))}")

    sayac = collections.Counter()
    ad_sayac = collections.Counter()
    for i, m in enumerate(canli[:INCELE]):
        kod = m["AA"]
        try:
            r = k._get(f"{fk.FEED}df_st_1_{kod}")
        except Exception as e:
            print(f"  {kod}: alinamadi ({e})")
            sayac["hata"] += 1
            continue
        kay = coz(r.text)
        ist = istatistikler(kay)
        adlar = {ad for _, ad, _, _ in ist}
        ad_sayac.update(adlar)
        xg = any("xg" in a.lower() or "expected" in a.lower() or "erwartet" in a.lower()
                 for a in adlar)
        sut = any("schüsse" in a.lower() or "shots" in a.lower() or "torsch" in a.lower()
                  for a in adlar)
        sayac["istatistik var" if ist else "istatistik yok"] += 1
        sayac["xG var"] += xg
        sayac["sut var"] += sut

        if i < DOK:
            print(f"\n=== {m.get('_lig')} | {m.get('AE')} - {m.get('AF')} "
                  f"| AC={m.get('AC')} skor {m.get('AG')}-{m.get('AH')}")
            if not ist:
                print(f"  (SG satiri yok) ham: {r.text[:300]!r}")
            for bolum, ad, ev, dep in ist:
                print(f"  [{bolum}] {ad}: {ev} - {dep}")

    print("\n--- KAPSAM ---")
    for a, n in sayac.items():
        print(f"  {a:16s} {n}")
    print("\n--- istatistik adlari (kac macta) ---")
    for a, n in ad_sayac.most_common(40):
        print(f"  {n:3d}  {a}")


if __name__ == "__main__":
    main()
