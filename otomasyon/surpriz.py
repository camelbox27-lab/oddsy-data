"""Gunun surprizleri (Oto-BOT, mac oncesi akisinda kupondan once gider).

1) 6+ GOL (Maç sonucu 5.5 Üst)
   bet365 beraberlik orani 5.00 ve ustu olan maclar; en olasi 3 tanesi
   (5.5 Ust orani en dusuk olanlar). Beraberlik orani yuksek = belirgin
   favori + gol beklentisi yuksek. 12.10-20.11 verisinde beraberlik
   4.50-8.00 kurali %16 tuttu, ortalama oran ~6.8.

2) İY/MS SÜRPRİZİ (sitedeki "Yapay Zeka Analiz" ile ayni mantik)
   Macin bet365 ACILIS 1-X-2 oranlariyla birebir ayni acilis oranli
   gecmis maclar ligler_json'dan (2002-2026, ~300 bin mac) bulunur.
   Bu maclardaki IY/MS sonuclarindan yalnizca 1/0, 2/0, 1/2, 2/1 sayilir;
   en cok tekrar eden secilir. En cok eslesen (gecmis mac sayisi en fazla)
   en fazla 5 mac gonderilir. En az ESLESME_MIN eslesme ve surprizin en az
   SURPRIZ_MIN kez gorulmus olmasi gerekir.
   Geriye donuk test (12.10-20.11, lig filtreli, gunde 5): 156 tahmin,
   12 tuttu (%7.7), bet365 IY/MS oraniyla +%10.
"""
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
LIGLER_JSON = KOK / "ligler_json"

ALTI_BERABERLIK_MIN = 5.00
ALTI_SAYI = 3
IYMS_IZINLI = ("1/0", "2/0", "1/2", "2/1")
IYMS_SAYI = 5
ESLESME_MIN = 20
SURPRIZ_MIN = 2

_GECMIS = None


def _oran(r, ad, son=" K"):
    try:
        v = float(r.get(ad + son))
    except (TypeError, ValueError):
        return None
    return round(v, 2) if v > 1 else None


def gecmis():
    """(acilis1, acilis0, acilis2) -> Counter(IY/MS). Ayni mac bir kez sayilir."""
    global _GECMIS
    if _GECMIS is not None:
        return _GECMIS
    g, gorulen = defaultdict(Counter), set()
    for f in glob.glob(str(LIGLER_JSON / "*.json")):
        metin = re.sub(r":\s*-?NaN", ": null", Path(f).read_text(encoding="utf-8"))
        for m in json.loads(metin):
            try:
                k = tuple(round(float(m[f"Bet365 Açılış {t}"]), 2) for t in "102")
            except (TypeError, ValueError, KeyError):
                continue
            im = str(m.get("İY/MS") or "")
            if not re.fullmatch(r"[012]/[012]", im):
                continue
            imza = (m.get("Tarih"), m.get("Ev Sahibi"), m.get("Deplasman"))
            if imza in gorulen:
                continue
            gorulen.add(imza)
            g[k][im] += 1
    print(f"[surpriz] gecmis: {len(gorulen)} mac, {len(g)} farkli acilis oran uclusu", flush=True)
    _GECMIS = g
    return g


def alti_gol(maclar):
    """maclar: [(bet365 kaydi, mac)] -- lig filtreli, baslamamis."""
    aday = []
    for r, m in maclar:
        ms0, u55 = _oran(r, "MS0"), _oran(r, "UST55")
        if ms0 is None or ms0 < ALTI_BERABERLIK_MIN or u55 is None:
            continue
        aday.append({**{k: m[k] for k in ("kod", "saat", "ev", "dep", "lig")}, "oran": u55})
    aday.sort(key=lambda m: (m["oran"], m["saat"]))
    return sorted(aday[:ALTI_SAYI], key=lambda m: m["saat"])


def iyms(maclar):
    g = gecmis()
    aday = []
    for r, m in maclar:
        k = tuple(_oran(r, f"MS{t}", " A") for t in "102")
        if None in k or k not in g:
            continue
        h = g[k]
        toplam = sum(h.values())
        sur = {c: h[c] for c in IYMS_IZINLI if h[c]}
        if toplam < ESLESME_MIN or not sur:
            continue
        c = max(sur, key=lambda x: (sur[x], -IYMS_IZINLI.index(x)))
        if sur[c] < SURPRIZ_MIN:
            continue
        aday.append({**{k_: m[k_] for k_ in ("kod", "saat", "ev", "dep", "lig")},
                     "iyms": c, "eslesme": toplam, "gorulme": sur[c],
                     "oran": _oran(r, "IYMS " + c.replace("/", "E"))})
    aday.sort(key=lambda m: (-m["eslesme"], -m["gorulme"]))
    return sorted(aday[:IYMS_SAYI], key=lambda m: m["saat"])
