"""Gunun kuponu: 4 mac, gunun mac oncesi tercihlerinden en olasilari.

    1 x Maç sonucu 3.5 Üst     (3.5 Üst listesinden)
    1 x İlk yarı 1.5 Üst       (ayni listeden, baska bir mac)
    2 x Maç sonucu 2.5 Üst     (2.5 Üst listesinden)

"En olasi" = bet365'te o bahsin orani en dusuk olan (bahis sirketinin en
yuksek olasilik verdigi). Oranlar bet365 bulteninin guncel (K) oranidir.
Ayni mac kuponda iki kez yer almaz.

Listede yeterli mac yoksa (hafif gunler) eksik kalan yer, lig filtresine
uyan baslamamis diger maclardan ayni bahsin en dusuk oranlisiyla doldurulur.
Oranin cok dusuk oldugu (1.15 alti) secimler alinmaz; kupona katki yok.
"""
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# bahis anahtari -> (bet365 alani, mesajdaki ad, tercih listesi)
BAHISLER = {
    "ust35": ("UST35", "Maç sonucu 3.5 Üst", "ust35"),
    "iy15": ("IYUST15", "İlk yarı 1.5 Üst", "ust35"),
    "ust25": ("UST25", "Maç sonucu 2.5 Üst", "ust25"),
}
SIRA = ["ust35", "iy15", "ust25", "ust25"]
EN_DUSUK = 1.15


def _secenekler(t, genel, bahis, kullanilan):
    alan, _, liste = BAHISLER[bahis]
    for havuz in (t.get(liste, []), genel):
        uygun = [m for m in havuz
                 if m["kod"] not in kullanilan and ((m.get("oran") or {}).get(alan) or 0) >= EN_DUSUK]
        if uygun:
            return sorted(uygun, key=lambda m: (m["oran"][alan], m["saat"])), havuz is not genel
    return [], False


def kupon(gun, t, genel):
    """t: tahmin_oncesi.tercihler(); genel: ayni kosullarda (lig, baslamamis)
    butun maclar. Her mac kaydinda "oran" = {"UST25":..,"UST35":..,"IYUST15":..}."""
    secim, kullanilan = [], set()
    for bahis in SIRA:
        adaylar, listeden = _secenekler(t, genel, bahis, kullanilan)
        if not adaylar:
            print(f"[kupon] {bahis} icin uygun mac yok", flush=True)
            continue
        m = adaylar[0]
        alan = BAHISLER[bahis][0]
        kullanilan.add(m["kod"])
        secim.append({"kod": m["kod"], "saat": m["saat"], "ev": m["ev"], "dep": m["dep"],
                      "lig": m.get("lig", ""), "bahis": bahis, "oran": m["oran"][alan],
                      "listeden": listeden})
        print(f"[kupon] {bahis}: {m['ev']} - {m['dep']} {m['oran'][alan]}"
              f"{'' if listeden else ' (listede yoktu, genel bultenden)'}", flush=True)
    if not secim:
        return None
    toplam = 1.0
    for m in secim:
        toplam *= m["oran"]
    return {"tarih": f"{gun:%d.%m.%Y}", "maclar": sorted(secim, key=lambda m: m["saat"]),
            "toplam": round(toplam, 2)}


def main():
    import tahmin_oncesi as to
    gun = dt.date.today()
    if len(sys.argv) > 1:
        gun = dt.datetime.strptime(sys.argv[1], "%d.%m.%Y").date()
    t = to.tercihler(gun)
    k = kupon(gun, t, to.genel_maclar(gun)) if t else None
    if not k:
        print("Kupon olusturulamadi.")
        return 1
    print(f"\nGUNUN KUPONU  {k['tarih']}")
    for m in k["maclar"]:
        print(f"  {m['saat']}  {m['ev']} - {m['dep']}  {BAHISLER[m['bahis']][1]}  {m['oran']:.2f}")
    print(f"  TOPLAM ORAN: {k['toplam']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
