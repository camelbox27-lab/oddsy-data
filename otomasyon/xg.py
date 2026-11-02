"""Flashscore mac istatistikleri: ilk yari xG / isabetli sut / buyuk firsat.

Akis: <FEED>df_st_1_<kod>. Kayitlar SE (bolum: "Spiel", "1. Hälfte",
"2. Hälfte") ve SG/SH/SI (ad / ev / deplasman) alanlariyla gelir
(01.11.2026'da canli maclarda dogrulandi, bkz. xg_kesif.py).
xG yalnizca buyuk liglerde var; yoksa None doner.
"""
import re

ILK_YARI = "1. Hälfte"
ADLAR = {"xg": "Expected Goals (xG)", "isb": "Schüsse aufs Tor", "buy": "Großchance"}


def _sayi(v):
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(v or ""))
    return float(m.group(1)) if m else None


def ilk_yari(kaynak, fk, kod):
    """{"xg": toplam|None, "isb": toplam|None, "buy": toplam|None}"""
    r = kaynak._get(f"{fk.FEED}df_st_1_{kod}")
    bolum, sonuc = None, {}
    for kayit in r.text.split("¬~"):
        d = dict(a.split("÷", 1) for a in kayit.split("¬") if "÷" in a)
        if "SE" in d:
            bolum = d["SE"]
        if bolum != ILK_YARI or "SG" not in d:
            continue
        for anahtar, ad in ADLAR.items():
            if d["SG"] == ad and anahtar not in sonuc:
                e, dep = _sayi(d.get("SH")), _sayi(d.get("SI"))
                if e is not None and dep is not None:
                    sonuc[anahtar] = round(e + dep, 2)
    return {k: sonuc.get(k) for k in ADLAR}
