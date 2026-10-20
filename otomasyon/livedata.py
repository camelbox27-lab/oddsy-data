"""vd.mackolik.com/livedata'dan MS oranlari.

Neden: Mackolik'in mac sayfalari (/mac/.../iddaa/<id>) GitHub'in veri merkezi
IP'lerinden 403 donuyor, bu yuzden oranlar cekilemiyordu ve gunluk bulten
tek maca dusmustu. vd.mackolik.com ayri bir alt alan adi ve engellenmemis.

Kapsam: bu akis yalnizca MAC SONUCU oranlarini guvenilir sekilde veriyor.
Dizideki [21]/[22] alanlari da oran gibi duruyor ama HTML'den dogrulanmis
degerlerle eslesmedi, yani hangi market olduklari belirsiz; yanlis etiketli
oran eksik orandan kotu oldugu icin BILEREK alinmiyor.

Alan konumlari PSG-Barcelona (iddaa kodu 3224058) uzerinden HTML'den cekilmis
gercek oranlarla karsilastirilarak dogrulandi:
    [14] iddaa kodu   [16] saat   [18] MS1   [19] MS0   [20] MS2   [35] tarih
"""
import datetime as dt

import requests

KAYNAK = "https://vd.mackolik.com/livedata"
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

KOD, SAAT, MS1, MS0, MS2 = 14, 16, 18, 19, 20
GEREKEN = MS2 + 1          # diziden en az bu kadar oge olmali


def _oran(v):
    """'2.14' gibi gecerli bir oran mi? '0.0'/'0'/'' bos sayilir."""
    s = str(v or '').strip()
    if not s:
        return ''
    try:
        return s if float(s.replace(',', '.')) > 1 else ''
    except ValueError:
        return ''


def oranlar(gun: dt.date, timeout: int = 30) -> dict:
    """{iddaa_kodu: {'ms1','ms0','ms2','mac_saati'}} dondurur.

    Hata halinde bos sozluk doner; cagiran taraf calismaya devam edebilsin.
    """
    try:
        y = requests.get(f"{KAYNAK}?date={gun:%d/%m/%Y}",
                         headers={'User-Agent': UA, 'Accept': '*/*'},
                         timeout=timeout)
        y.raise_for_status()
        maclar = y.json().get('m', [])
    except Exception as e:
        print(f"[livedata] alinamadi: {e}", flush=True)
        return {}

    sonuc = {}
    for m in maclar:
        if not isinstance(m, list) or len(m) <= GEREKEN:
            continue
        kod = str(m[KOD] or '').strip()
        if not kod or kod == '0':
            continue
        satir = {'ms1': _oran(m[MS1]), 'ms0': _oran(m[MS0]), 'ms2': _oran(m[MS2])}
        # UCU BIRDEN dolu degilse hic alinmaz. Konumsal bir dizide eksik tek
        # alan, o kaydin dizilimi kaymis olabilecegi anlamina gelir; yarim bir
        # ucluyu yayinlamak yanlis oran gostermek demektir.
        if not all(satir.values()):
            continue
        saat = str(m[SAAT] or '').strip()
        if saat:
            satir['mac_saati'] = saat
        sonuc[kod] = satir

    print(f"[livedata] {len(sonuc)} mac icin MS orani alindi", flush=True)
    return sonuc
