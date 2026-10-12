"""Bet365Pro gunluk (baslamayan) maclar -> bet365/GGAAYYYY.xlsx

Masaustu uygulamasindaki BASLAMAYAN MACLARI CEK + TUMUNU AKTAR akisini sunucuda
yapar. Flashscore'dan gunun maclarini ve bet365 oranlarini ceker, gecici bir
SQLite'a yazar, sonra 227 kolonluk "Tum Veriler" Excel'ini uretir.

Her calisma temiz bir veritabani sablonundan baslar: cikti o gune ait tek gunluk
veri olur (mevcut 12102026.xlsx ile ayni yapi).
"""
import datetime as dt
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "kaynak"))
import cekirdek              # noqa: E402
import excel_aktar           # noqa: E402

KAYNAK = Path(__file__).resolve().parent / "kaynak"
SABLON_DB = KAYNAK / "data.db"
CIKTI_KLASOR = Path(__file__).resolve().parent.parent / "bet365"


def main() -> int:
    gun = dt.date.today()
    if len(sys.argv) > 1:                       # elle test icin: python bet365_cek.py 2026-10-13
        gun = dt.date.fromisoformat(sys.argv[1])

    with tempfile.TemporaryDirectory() as gecici:
        db_yolu = Path(gecici) / "data.db"
        shutil.copy2(SABLON_DB, db_yolu)        # sablonu boz(ma)madan calis

        db = cekirdek.Veritabani(str(db_yolu))

        def log(metin):
            print(f"[bet365] {metin}", flush=True)

        son = [0]

        def ilerleme(bitti, toplam):
            if toplam and (bitti == toplam or bitti - son[0] >= 25):
                son[0] = bitti
                print(f"[bet365]   {bitti}/{toplam} islendi", flush=True)

        cekici = cekirdek.Cekici(db, log, ilerleme)

        # Flashscore gun akisi bugun/dun/yarin icin ayri ayri cekilir; biri
        # koparsa o ana kadar veritabanina yazilanla devam edilir (kismi veri,
        # hic veri yoktan iyidir). Hicbir sey gelmediyse asagida hata verilir.
        eksik = None
        try:
            cekici.gunluk(gun, gun, bitmis=False)   # baslamayan maclar
        except Exception as e:
            eksik = e
            print(f"[bet365] UYARI: cekme yarida kesildi: {e}", flush=True)

        satirlar = db.tarih_araligi(gun, gun)
        if not satirlar:
            print("[bet365] HATA: hic mac bulunamadi, dosya yazilmadi.", flush=True)
            return 1
        if eksik:
            print(f"[bet365] UYARI: veri kismi olabilir ({len(satirlar)} mac yazildi).",
                  flush=True)

        CIKTI_KLASOR.mkdir(parents=True, exist_ok=True)
        cikti = CIKTI_KLASOR / f"{gun:%d%m%Y}.xlsx"
        excel_aktar.tum_verileri_yaz(db.kolonlar, satirlar, cikti)
        print(f"[bet365] OK -> {cikti.name} ({len(satirlar)} mac)", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
