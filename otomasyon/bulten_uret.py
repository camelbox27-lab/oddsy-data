"""Mobil icin gunun bultenini Flashscore'dan uretir.

NEDEN: bot pipeline'inin 3. adimi (SofaScore) ve 5. adimi (Mackolik mac
sayfalari) GitHub'in veri merkezi IP'lerinden 403 aliyor. Ikisi de kritik
adim oldugu icin zincir duruyordu.

Bet365Pro'nun Flashscore yolu ayni oranlari veriyor ve GitHub'dan CALISIYOR.
Birlestirilmis dosyanin ihtiyac duydugu her alan orada mevcut, yani
3-5-6. adimlar yerine tek kaynaktan dogrudan merged dosyasi uretilebilir.

Cikti, match_merger_bot.py'nin urettigi dosyayla AYNI bicimde yazilir;
boylece 7/8/9. adimlar (clean, clear_predictions, filter_bot) hic
degismeden calisir ve site ayni JSON'lari gorur.

Bu script YALNIZCA mobil (CI) yolunda calisir; PC'deki pipeline'a
dokunulmaz, orada SofaScore + Mackolik eskisi gibi kullanilir.
"""
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

KAYNAK = Path(__file__).resolve().parent / "kaynak"
sys.path.insert(0, str(KAYNAK))
import cekirdek                      # noqa: E402

BOT = Path(__file__).resolve().parent / "bot"
CIKTI_KLASOR = BOT / "merged" / "merged_json"

# Flashscore kolonu -> merged alani. Kapanis (_K) tercih edilir, yoksa acilis (_A).
ESLEME = {
    'beraberlik_orani': 'MS0',
    'kg_var':           'KGVAR',
    '2_5_ust':          'UST25',
    '3_5_ust':          'UST35',
    'ms_5_5_ust':       'UST55',
    'iy_kg_var':        'IY_KGVAR',
    'iy_kg_yok':        'IY_KGYOK',
}


def _sayi(deger):
    """'2.45' -> 2.45 ; bos/0/gecersiz -> None."""
    if deger in (None, ''):
        return None
    try:
        s = float(str(deger).replace(',', '.'))
    except (TypeError, ValueError):
        return None
    return s if s > 1 else None


def uret(gun: dt.date) -> int:
    with tempfile.TemporaryDirectory() as gecici:
        db_yolu = Path(gecici) / "data.db"
        shutil.copy2(KAYNAK / "data.db", db_yolu)
        db = cekirdek.Veritabani(str(db_yolu))

        def log(m):
            print(f"[bulten] {m}", flush=True)

        son = [0]

        def ilerleme(bitti, toplam):
            if toplam and (bitti == toplam or bitti - son[0] >= 25):
                son[0] = bitti
                print(f"[bulten]   {bitti}/{toplam} islendi", flush=True)

        cekici = cekirdek.Cekici(db, log, ilerleme)
        try:
            cekici.gunluk(gun, gun, bitmis=False)   # baslamamis maclar
        except Exception as e:
            print(f"[bulten] UYARI: cekme yarida kesildi: {e}", flush=True)

        satirlar = db.tarih_araligi(gun, gun)
        kolon = {ad: i for i, ad in enumerate(db.kolonlar)}

    def al(satir, ad):
        """Once kapanis orani, yoksa acilis."""
        for sonek in ('_K', '_A'):
            i = kolon.get(ad + sonek)
            if i is not None:
                v = _sayi(satir[i])
                if v is not None:
                    return v
        return None

    maclar = []
    for s in satirlar:
        tarih = s[kolon['Tarih']]
        saat = ''
        if tarih:
            try:
                saat = dt.datetime.fromisoformat(str(tarih)).strftime('%H:%M')
            except ValueError:
                saat = str(tarih)[11:16]

        kayit = {
            'event_id':  s[kolon['MatchCode']],
            'date_time': str(tarih) if tarih else '',
            'home_team': s[kolon['Ev']],
            'away_team': s[kolon['Dep']],
            'league':    s[kolon['Lig']] or '',
            'saat':      saat,
        }
        kayit.update({alan: al(s, sut) for alan, sut in ESLEME.items()})

        # Beraberlik orani olmayan mac filtrelerde zaten kullanilamaz
        if kayit['beraberlik_orani'] is None:
            continue
        maclar.append(kayit)

    CIKTI_KLASOR.mkdir(parents=True, exist_ok=True)
    hedef = CIKTI_KLASOR / f"merged_{gun:%d.%m.%Y}.json"
    hedef.write_text(json.dumps({
        'date': f"{gun:%d.%m.%Y}",
        'timestamp': dt.datetime.now().isoformat(),
        'total_merged': len(maclar),
        'matches': maclar,
        'kaynak': 'flashscore (mobil)',   # PC ciktisindan ayirt edilebilsin
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"[bulten] OK -> {hedef.name} ({len(maclar)} mac)", flush=True)
    return len(maclar)


if __name__ == "__main__":
    gun = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    sys.exit(0 if uret(gun) else 1)
