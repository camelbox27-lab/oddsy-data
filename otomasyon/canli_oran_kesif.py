"""Canli oran testi: Flashscore oran servisi bet365 oranlarini mac icinde
guncelliyor mu? Yalnizca loga yazar, hicbir yere gondermez/kaydetmez.

Canli maclardan (oncelik ilk yari) en fazla 8 tanesi secilir, TUR kez
YOKLAMA saniye arayla bet365 'Alt/Ust' oranlari cekilir:
  IY 1.5 Ust / IY 0.5 Ust (FIRST_HALF) ve MS 2.5 Ust (FULL_TIME).
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
import flashscore_kaynak as fk  # noqa: E402

TUR, YOKLAMA = 13, 60


def ham_oranlar(k, kod):
    r = k._get(fk.ODDS, params={"_hash": "oce", "eventId": kod, "projectId": fk.PROJECT_ID,
                                "geoIpCode": fk.GEO, "geoIpSubdivisionCode": fk.GEO_SUB})
    return r.json()


def ozet(veri):
    o = (veri.get("data") or {}).get("findOddsByEventId") or {}
    b365 = [g for g in (o.get("odds") or []) if g.get("bookmakerId") == fk.BET365_ID]
    s = {}
    for g in b365:
        if g.get("bettingType") != "OVER_UNDER":
            continue
        kap = {"FIRST_HALF": "IY", "FULL_TIME": "MS"}.get(g.get("bettingScope"))
        for it in g.get("odds") or []:
            h = (it.get("handicap") or {}).get("value")
            if it.get("selection") == "OVER" and kap and (kap, h) in (("IY", "0.5"), ("IY", "1.5"), ("MS", "2.5"), ("MS", "3.5")):
                s[f"{kap}{h}U"] = f"{it.get('value')}" + ("" if it.get("active", True) else "(kapali)")
    return s, b365, o


def main():
    k = fk.FlashscoreKaynak()
    maclar = [m for m in k.gunun_maclari(0) if m.get("AB") == "2"]
    maclar.sort(key=lambda m: (m.get("AC") != "12", m.get("_lig", "")))
    secim = maclar[:8]
    print(f"canli mac: {len(maclar)}, izlenen: {len(secim)}", flush=True)
    for m in secim:
        print(f"  {m['AA']}  {m.get('_lig','')[:40]} | {m.get('AE','')} - {m.get('AF','')}", flush=True)

    ilk = True
    onceki = {}
    for tur in range(TUR):
        simdi = time.time()
        akis = {m["AA"]: m for m in k.gunun_maclari(0)}
        print(f"\n===== tur {tur + 1}  {time.strftime('%H:%M:%S')}", flush=True)
        for m in secim:
            kod = m["AA"]
            c = akis.get(kod, m)
            ac = c.get("AC")
            bas = int(c.get("AO") or c.get("AD") or 0)
            dk = (int(simdi) - bas) // 60 + 1 + (45 if ac == "13" else 0)
            faz = {"12": "1Y", "38": "DA", "13": "2Y"}.get(ac, ac)
            try:
                veri = ham_oranlar(k, kod)
            except Exception as e:
                print(f"  {kod} HATA {e}", flush=True)
                continue
            s, b365, o = ozet(veri)
            if ilk:
                print(f"  [{kod}] ust anahtarlar: {list(o.keys())}", flush=True)
                tipler = sorted({(g.get('bettingType'), g.get('bettingScope')) for g in b365})
                print(f"  [{kod}] bet365 pazarlari: {tipler}", flush=True)
                for g in b365:
                    if g.get("bettingType") == "OVER_UNDER" and g.get("odds"):
                        print(f"  [{kod}] ornek oran kaydi: {json.dumps(g['odds'][0], ensure_ascii=False)[:400]}", flush=True)
                        print(f"  [{kod}] grup alanlari: {[x for x in g.keys() if x != 'odds']}", flush=True)
                        break
                diger = sorted({g.get("bookmakerId") for g in (o.get("odds") or [])})
                print(f"  [{kod}] oran veren bookmaker id'leri: {diger}", flush=True)
            degisim = "" if onceki.get(kod) in (None, s) else "  <-- DEGISTI"
            onceki[kod] = s
            print(f"  {kod} {faz} {dk:>3}' {c.get('AG','?')}-{c.get('AH','?')}  {s}{degisim}", flush=True)
        ilk = False
        if tur + 1 < TUR:
            time.sleep(max(1, YOKLAMA - (time.time() - simdi)))


if __name__ == "__main__":
    main()
