"""Sessiz moddaki xG kurallarinin basari raporu (Telegram'a gitmez).

Kullanim: python otomasyon/xg_rapor.py [gun_sayisi=7]
canli-kayit dalindaki kayit/GG.AA.YYYY.json dosyalarinin "gozlem"
alanlarini okur, farkli esiklerin isabet oranlarini yazar.
"""
import datetime as dt
import json
import sys
import urllib.request

HAM = "https://raw.githubusercontent.com/camelbox27-lab/oddsy-data/canli-kayit/kayit/{}.json"
R4 = {(2, 1), (1, 2), (3, 0), (0, 3)}


def gunler(n):
    bugun = dt.date.today()
    for i in range(n, -1, -1):
        g = (bugun - dt.timedelta(days=i)).strftime("%d.%m.%Y")
        try:
            with urllib.request.urlopen(HAM.format(g), timeout=20) as r:
                yield g, json.load(r)
        except Exception:
            continue


def oran(liste):
    if not liste:
        return "   -"
    return f"{sum(liste)}/{len(liste)} = %{100 * sum(liste) / len(liste):.0f}"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    k5, da = [], []
    for g, v in gunler(n):
        for kod, st in v.get("maclar", {}).items():
            o = st.get("gozlem") or {}
            if "sonuc" in o.get("k5", {}):
                k5.append(o["k5"])
            if "ms" in o.get("da", {}):
                da.append(o["da"])
    print(f"Son {n} gun · k5 gozlem: {len(k5)} mac · devre arasi gozlem: {len(da)} mac\n")

    print("KURAL 5 · 0-0 iken İY 0.5 Üst (ilk olcumde esik gecildiyse oynanir)")
    print("  tum 0-0 maclar (dk 20):", oran([e["sonuc"] for e in k5 if "20" in e["olcum"]]))
    for esik in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        sec = [e["sonuc"] for e in k5 if any((x.get("xg") or 0) >= esik for x in e["olcum"].values())]
        print(f"  xG >= {esik:.1f}:", oran(sec))
    for esik in (3, 4, 5):
        sec = [e["sonuc"] for e in k5 if any(x.get("xg") is None and (x.get("isb") or 0) >= esik
                                            for x in e["olcum"].values())]
        print(f"  xG yok, isabetli sut >= {esik}:", oran(sec))
    sec = [e["sonuc"] for e in k5 if any(x.get("xg") is None and (x.get("buy") or 0) >= 2
                                        for x in e["olcum"].values())]
    print("  xG yok, buyuk firsat >= 2:", oran(sec))

    print("\nKURAL 4 · İY 2-1/1-2/3-0/0-3 -> MS 4.5 Üst")
    r4 = [e for e in da if tuple(e["iy"]) in R4]
    print("  mevcut kural (suzgecsiz):", oran([e["ms"] >= 5 for e in r4]))
    for esik in (1.4, 1.6, 1.8, 2.0, 2.2):
        print(f"  + xG >= {esik:.1f}:", oran([e["ms"] >= 5 for e in r4 if (e.get("xg") or 0) >= esik]))
    print("  + xG yok, isabetli sut >= 7:",
          oran([e["ms"] >= 5 for e in r4 if e.get("xg") is None and (e.get("isb") or 0) >= 7]))

    print("\nKURAL 6 · İY toplam gol <= 1 -> 2. Yarı 0.5 Üst")
    r6 = [e for e in da if sum(e["iy"]) <= 1]
    print("  tum maclar:", oran([e["y2"] >= 1 for e in r6]))
    for esik in (1.0, 1.2, 1.3, 1.5, 1.8):
        print(f"  xG >= {esik:.1f}:", oran([e["y2"] >= 1 for e in r6 if (e.get("xg") or 0) >= esik]))
    print("  xG yok, isabetli sut >= 6:",
          oran([e["y2"] >= 1 for e in r6 if e.get("xg") is None and (e.get("isb") or 0) >= 6]))


if __name__ == "__main__":
    main()
