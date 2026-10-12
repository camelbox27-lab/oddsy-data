"""IddaaPro gunluk bulten -> iddaa/gunluk/gunlukmaclar.xlsx

Masaustu uygulamasindaki GUNLUK BULTEN butonunun yaptigi isi sunucuda yapar:
Mackolik API'den gunun maclarini alir, her macin oran sayfasini cekip parse eder,
baslamis maclari eler ve Excel'e yazar. Kolon duzeni export_excel'den geldigi
icin masaustu cikti ile birebir aynidir.
"""
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import tkinter_stub

tkinter_stub.kur()          # iddaapro import'undan ONCE calismali

sys.path.insert(0, str(Path(__file__).parent / "kaynak"))
import iddaapro as ip       # noqa: E402

PARALEL = 5                 # masaustu uygulamasiyla ayni
CIKTI = Path(__file__).resolve().parent.parent / "iddaa" / "gunluk" / "gunlukmaclar.xlsx"


def cek(gun: dt.date) -> list[dict]:
    """gun icin baslamamis maclari oranlariyla dondurur."""
    simdi = dt.datetime.now()
    ligler = ip._get_all_league_keys()

    # UEFA kupa maclari lig secimine bakilmadan alinir (masaustuyle ayni davranis)
    ozetler = ip.fetch_matches_api(gun, lig_filtre=ligler, uefa_kupalari=True)
    print(f"[iddaa] {gun:%d.%m.%Y}: API'den {len(ozetler)} mac geldi", flush=True)
    if not ozetler:
        return []

    satirlar, atlanan_baslamis, gecersiz = [], 0, 0
    with ThreadPoolExecutor(max_workers=PARALEL) as pool:
        isler = [pool.submit(ip.scrape_match_fast, o, match_date=gun, market_keys=None)
                 for o in ozetler]
        for bitti, is_ in enumerate(as_completed(isler), 1):
            try:
                r = is_.result()
            except Exception as e:
                print(f"[iddaa]   mac hatasi: {e}", flush=True)
                continue
            if ip._mac_baslamis_mi(r, gun, simdi):
                atlanan_baslamis += 1
                continue
            if not ip._row_is_valid_gunluk(r, None):
                gecersiz += 1
                continue
            satirlar.append(r)
            if bitti % 25 == 0 or bitti == len(isler):
                print(f"[iddaa]   {bitti}/{len(isler)} islendi, {len(satirlar)} gecerli",
                      flush=True)

    print(f"[iddaa] {len(satirlar)} baslamamis mac "
          f"({atlanan_baslamis} baslamis atlandi, {gecersiz} oransiz atlandi)", flush=True)
    return satirlar


def main() -> int:
    gun = dt.date.today()
    if len(sys.argv) > 1:                       # elle test icin: python iddaa_cek.py 2026-10-13
        gun = dt.date.fromisoformat(sys.argv[1])

    satirlar = cek(gun)
    if not satirlar:
        # Bos Excel yazip siteyi bos bultenle ezmek yerine hata ver.
        print("[iddaa] HATA: hic mac bulunamadi, dosya yazilmadi.", flush=True)
        return 1

    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    ip.export_excel(satirlar, CIKTI, market_keys=None)
    print(f"[iddaa] OK -> {CIKTI.name} ({len(satirlar)} mac)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
