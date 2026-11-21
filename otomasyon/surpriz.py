"""Gunun surprizleri (Oto-BOT, mac oncesi akisinda kupondan once gider).

1) 6+ GOL (Maç sonucu 5.5 Üst)
   bet365 beraberlik orani 5.00 ve ustu olan maclar arasindan, ayni ACILIS
   1-X-2 oranli gecmis maclarda (en az ALTI_ESLESME_MIN mac) en az
   ALTI_GORULME_MIN kez 6+ gol cikmis olanlar; 6+ orani en yuksek 3 mac.
   (21.11: eslesmesi olmayan ya da hic 6+ gormemis maclar da secilip
   kartta bos / tutmayan ornekle gidiyordu.) Uygun mac yoksa gonderilmez.

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
ALTI_ESLESME_MIN = 8
ALTI_GORULME_MIN = 2
IYMS_IZINLI = ("1/0", "2/0", "1/2", "2/1")
IYMS_SAYI = 5
ESLESME_MIN = 20
SURPRIZ_MIN = 2

_GECMIS = None
_ORNEK = None      # acilis oran uclusu -> [(tarih, lig, ev, dep, iy, ms, iyms)]


def _oran(r, ad, son=" K"):
    try:
        v = float(r.get(ad + son))
    except (TypeError, ValueError):
        return None
    return round(v, 2) if v > 1 else None


def gecmis():
    """(acilis1, acilis0, acilis2) -> Counter(IY/MS). Ayni mac bir kez sayilir."""
    global _GECMIS, _ORNEK
    if _GECMIS is not None:
        return _GECMIS
    g, gorulen, ornek = defaultdict(Counter), set(), defaultdict(list)
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
            ornek[k].append((str(m.get("Tarih") or "")[:10], m.get("Lig") or "",
                             m.get("Ev Sahibi") or "", m.get("Deplasman") or "",
                             str(m.get("İlk Yarı Skor") or ""), str(m.get("Maç Sonucu Skor") or ""), im))
    print(f"[surpriz] gecmis: {len(gorulen)} mac, {len(g)} farkli acilis oran uclusu", flush=True)
    _GECMIS, _ORNEK = g, ornek
    return g


def _gol(skor):
    try:
        e, d = (int(x) for x in skor.split("-"))
        return e + d
    except (ValueError, AttributeError):
        return -1


def ornekler(acilis, iyms_=None, adet=5, tutan=3):
    """Ayni acilis oranli gecmis maclardan ornekler: 'tutan' tanesi tahminle
    biten (IY/MS'te o sonuc, 6+'da en gollu maclar), kalani farkli bitenler
    (en yeni). Hepsi tarihe gore, en yeni once."""
    gecmis()
    satir = _ORNEK.get(tuple(acilis), [])
    if iyms_:
        ok = lambda x: x[6] == iyms_
        ust = sorted((x for x in satir if ok(x)), key=lambda x: x[0], reverse=True)
    else:
        ok = lambda x: _gol(x[5]) >= 6
        ust = sorted((x for x in satir if ok(x)), key=lambda x: x[0], reverse=True)
    secilen = ust[:tutan]
    diger = sorted((x for x in satir if x not in secilen and not ok(x)), key=lambda x: x[0], reverse=True)
    secilen += diger[:adet - len(secilen)]
    secilen.sort(key=lambda x: x[0], reverse=True)
    return [dict(zip(("tarih", "lig", "ev", "dep", "iy", "ms", "iyms"), x)) for x in secilen]


def alti_gol(maclar):
    """maclar: [(bet365 kaydi, mac)] -- lig filtreli, baslamamis."""
    gecmis()
    aday = []
    for r, m in maclar:
        ms0, u55 = _oran(r, "MS0"), _oran(r, "UST55")
        if ms0 is None or ms0 < ALTI_BERABERLIK_MIN:
            continue
        acilis = [_oran(r, f"MS{t}", " A") for t in "102"]
        satir = _ORNEK.get(tuple(acilis), [])
        alti = sum(1 for x in satir if _gol(x[5]) >= 6)
        if len(satir) < ALTI_ESLESME_MIN or alti < ALTI_GORULME_MIN:
            continue
        aday.append({**{k: m[k] for k in ("kod", "saat", "ev", "dep", "lig")}, "oran": u55,
                     "acilis": acilis, "eslesme": len(satir), "gorulme": alti})
    aday.sort(key=lambda m: (-m["gorulme"] / m["eslesme"], -m["gorulme"], m["saat"]))
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
                     "iyms": c, "eslesme": toplam, "gorulme": sur[c], "acilis": list(k),
                     "oran": _oran(r, "IYMS " + c.replace("/", "E"))})
    aday.sort(key=lambda m: (-m["eslesme"], -m["gorulme"]))
    return sorted(aday[:IYMS_SAYI], key=lambda m: m["saat"])
