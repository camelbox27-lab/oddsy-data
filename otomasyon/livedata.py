"""vd.mackolik.com/livedata'dan MS oranlari.

Neden: Mackolik'in mac sayfalari (/mac/.../iddaa/<id>) GitHub'in veri merkezi
IP'lerinden 403 donuyor, bu yuzden oranlar cekilemiyordu ve gunluk bulten
tek maca dusmustu. vd.mackolik.com ayri bir alt alan adi ve engellenmemis.

Alan konumlari, iddaa bulteninde oranlari DOLU olan maclarla karsilastirilarak
dogrulandi (bkz. otomasyon/livedata_kesif.py):
    [14] iddaa kodu   [16] saat   [18] MS1   [19] MS0   [20] MS2
    [21] 2.5 ALT      [22] 2.5 UST                       [35] tarih

[21]/[22] onceden "belirsiz" sayiliyordu. 01.11.2026'da 6 dogrulama maci
uzerinde olculdu: 5'inde %4 tolerans icinde, 3'unde rakami rakamina ayni
cikti. Tutmayan tek macta (Lazio-Cagliari) MS oranlari da kaymisti, yani
oran gercekten hareket etmis; livedata canli, iddaa dosyasi eski bir anlik
goruntu. Karsilastirma olarak: zaten guvendigimiz MS1 de ayni testte 5/6.

NOT: oranlar() ciktisindaki her anahtar iddaa_cek.py tarafindan satira
kopyalaniyor; oraya yeni alan EKLENMEMELI. 2.5 oranlari bu yuzden ayri
fonksiyonda (ust_alt_25) duruyor.
"""
import datetime as dt

import requests

KAYNAK = "https://vd.mackolik.com/livedata"
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

KOD, SAAT, MS1, MS0, MS2 = 14, 16, 18, 19, 20
ALT25, UST25 = 21, 22
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


def _indir(gun: dt.date, timeout: int) -> list:
    """Gunun ham mac dizilerini doner; hata halinde bos liste."""
    try:
        y = requests.get(f"{KAYNAK}?date={gun:%d/%m/%Y}",
                         headers={'User-Agent': UA, 'Accept': '*/*'},
                         timeout=timeout)
        y.raise_for_status()
        return y.json().get('m', [])
    except Exception as e:
        print(f"[livedata] alinamadi: {e}", flush=True)
        return []


def ust_alt_25(gun: dt.date, timeout: int = 30) -> dict:
    """{iddaa_kodu: {'alt25','ust25'}} dondurur (iddaa'nin 2.5 oranlari).

    IKISI BIRDEN gecerli degilse kayit alinmaz: konumsal bir dizide tek
    basina duran bir deger, dizilimin kaymis olabilecegi anlamina gelir.
    """
    sonuc = {}
    for m in _indir(gun, timeout):
        if not isinstance(m, list) or len(m) <= UST25:
            continue
        kod = str(m[KOD] or '').strip()
        if not kod or kod == '0':
            continue
        alt, ust = _oran(m[ALT25]), _oran(m[UST25])
        if not (alt and ust):
            continue
        sonuc[kod] = {'alt25': alt, 'ust25': ust}

    print(f"[livedata] {len(sonuc)} mac icin 2.5 alt/ust orani alindi", flush=True)
    return sonuc


def oranlar(gun: dt.date, timeout: int = 30) -> dict:
    """{iddaa_kodu: {'ms1','ms0','ms2','mac_saati'}} dondurur.

    Hata halinde bos sozluk doner; cagiran taraf calismaya devam edebilsin.
    DIKKAT: buraya yeni anahtar eklenmemeli (bkz. modul basligi).
    """
    maclar = _indir(gun, timeout)
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
