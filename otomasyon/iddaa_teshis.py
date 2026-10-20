"""Mackolik oranlari icin engellenmeyen bir yol var mi? Olcer.

Bilinen: /mac/.../iddaa/<id> HTML sayfasi GitHub IP'sinden 403.
Bilinen: /perform/p0/ajax/.../livescores/json ayni IP'den 200.
Yani engel yola/hosta bagli. Bu script alternatif uclari ve ucretsiz bir
aracli getirme servisini deneyip hangisi oranlari donduruyor, gosterir.
"""
import re
import sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "kaynak"))
import tkinter_stub                      # noqa: E402
tkinter_stub.kur()
import iddaapro as ip                    # noqa: E402
import requests as std                   # noqa: E402

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
BASLIK = {'User-Agent': UA,
          'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
          'Accept-Language': 'tr,en;q=0.7'}

print("=" * 70)
print("  MACKOLIK ALTERNATIF UC TARAMASI")
print("=" * 70)

gun = dt.date.today()
ozetler = ip.fetch_matches_api(gun, lig_filtre=ip._get_all_league_keys(),
                               uefa_kupalari=True)
print(f"\nListe API: {len(ozetler)} mac")
if not ozetler:
    sys.exit("Liste bos, test edilemiyor.")

link = ozetler[0]['iddaa_link']
mid = link.rstrip('/').split('/')[-1]
print(f"Test maci : {ozetler[0].get('ev_sahibi')} - {ozetler[0].get('konuk_ekip')}")
print(f"mac id    : {mid}")
print(f"HTML link : {link}")

ORAN_IZI = (ip.MARKET_ITEM_CLASS, 'iddaa', 'odd', 'oran', '"o":', 'markets')


def dene(ad, url, baslik=None, timeout=25):
    s = std.Session(); s.headers.update(baslik or BASLIK)
    try:
        y = s.get(url, timeout=timeout)
    except Exception as e:
        print(f"\n--- {ad}\n    HATA: {e}")
        return
    g = y.text or ""
    izler = [t for t in ORAN_IZI if t in g]
    print(f"\n--- {ad}")
    print(f"    durum    : {y.status_code}{'   <-- 200' if y.status_code == 200 else ''}")
    print(f"    uzunluk  : {len(g)}")
    print(f"    oran izi : {izler if izler else 'YOK'}")
    if y.status_code == 200 and len(g) < 400:
        print(f"    govde    : {g[:300]}")


# 1) Kontrol: engellenen HTML sayfasi
dene("A) /mac/.../iddaa/ HTML (kontrol, 403 bekleniyor)", link)

# 2) Ayni ajax on eki (livescores burada calisiyor)
dene("B) perform/p0/ajax matchHeader",
     f"https://www.mackolik.com/perform/p0/ajax/components/match/matchHeader"
     f"?matchId={mid}&sdapiLanguageCode=tr-mk&ajaxViewName=match-details"
     f"&ajaxPartialViewName=match-details-status&displayMode=all")

dene("C) perform/p0/ajax matchHeader (ajaxViewName=iddaa)",
     f"https://www.mackolik.com/perform/p0/ajax/components/match/matchHeader"
     f"?matchId={mid}&sdapiLanguageCode=tr-mk&ajaxViewName=iddaa"
     f"&ajaxPartialViewName=iddaa&displayMode=all")

dene("D) ajax/football/key-events",
     f"https://www.mackolik.com/ajax/football/key-events?ajaxViewName=events&matchId={mid}")

# 3) Farkli alt alan adi: canli veri akisi (tarihsel olarak iddaa oranlari icerir)
dene("E) vd.mackolik.com/livedata (farkli host)",
     f"https://vd.mackolik.com/livedata?date={gun:%d/%m/%Y}")

# 4) Ucretsiz aracli getirme servisi (proxy satin almadan)
dene("F) r.jina.ai araciligi (ucretsiz servis)",
     f"https://r.jina.ai/{link}",
     baslik={**BASLIK, 'x-respond-with': 'html'}, timeout=45)

print("\n" + "=" * 70)
print("  YORUM")
print("  B/C/D/E 200 + oran izi -> engellenmeyen uc bulundu, proxy gerekmez")
print("  F 200 + oran izi       -> ucretsiz aracla bugun idare edilebilir")
print("  hepsi 403/bos          -> proxy sart")
print("=" * 70)
