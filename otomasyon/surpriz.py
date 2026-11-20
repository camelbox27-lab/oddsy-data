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
        ust = sorted(satir, key=lambda x: (_gol(x[5]), x[0]), reverse=True)
    secilen = ust[:tutan]
    diger = sorted((x for x in satir if x not in secilen and not ok(x)), key=lambda x: x[0], reverse=True)
    secilen += diger[:adet - len(secilen)]
    secilen.sort(key=lambda x: x[0], reverse=True)
    return [dict(zip(("tarih", "lig", "ev", "dep", "iy", "ms", "iyms"), x)) for x in secilen]
