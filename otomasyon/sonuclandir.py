"""Dunun Ilk Yari Gol listesini sonuclandirir.

KURAL: update_results.py'deki 'Ilk Yari Gol' kategorisiyle AYNI --
ilk yarida atilan toplam gol > 0 ise KAZANDI. Burada yeniden
yorumlanmaz, ayni kural uygulanir.

DUNUN LISTESI nereden gelir:
  1. data/gecmis/halfTimeGoals_GG.AA.YYYY.json  (arsivle_liste.py yazar)
  2. Arsiv yoksa bet365/GGAAYYYY.json'dan yeniden kurulur. O dosya gunun
     butun maclarini ve beraberlik oranlarini tasiyor; filter_bot.py ile
     ayni oran listesi uygulanirsa o gunku liste birebir geri elde edilir.
     (Arsiv ozelligi eklenmeden onceki gunler icin gereklidir.)

SKORLAR Flashscore'dan taze cekilir; GitHub'dan erisilebiliyor. Yalnizca
listedeki maclarin ilk yari skoru istenir, gunun tamaminin degil.
"""
import concurrent.futures as cf
import datetime as dt
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
KAYNAK_DIZIN = KOK / "otomasyon" / "kaynak"
sys.path.insert(0, str(KAYNAK_DIZIN))
import flashscore_kaynak as fk            # noqa: E402

ARSIV = KOK / "data" / "gecmis"
BET365 = KOK / "bet365"

# filter_bot.py'deki ilk_yari_gol_oranlari ile AYNI olmali.
ORANLAR = [3.50, 4.00, 4.10, 4.33, 4.50, 4.75,
           5.00, 5.25, 5.75, 6.00, 7.00, 8.00]


def _sayi(v):
    s = str(v or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return f if f > 1 else None


def _zaman(v):
    """bet365 JSON'unda Tarih, milisaniye cinsinden epoch olarak duruyor.
    Eski/alternatif bicimler (ISO metin) de kabul edilir. None -> coz0lemedi.
    """
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)) or str(v).strip().isdigit():
        try:
            # bet365 JSON'unda Tarih, Turkiye saatini UTC'ymis gibi yazilmis epoch'tur
            # (pandas naive datetime'i boyle serilestiriyor). UTC olarak okunmali;
            # yerel saat diliminde okumak +3 saat kaydirir.
            return dt.datetime.fromtimestamp(int(v) / 1000, dt.timezone.utc).replace(tzinfo=None)
        except (ValueError, OSError, OverflowError):
            return None
    try:
        return dt.datetime.fromisoformat(str(v))
    except ValueError:
        return None


def _ms0(r):
    """bet365 kaydindan beraberlik orani (once kapanis, yoksa acilis)."""
    for k in ("MS0 K", "MS0 A", "MS0_K", "MS0_A"):
        v = _sayi(r.get(k))
        if v is not None:
            return v
    return None


def dunun_listesi(gun: dt.date):
    """(kayitlar, kaynak_aciklamasi) doner."""
    arsiv = ARSIV / f"halfTimeGoals_{gun:%d.%m.%Y}.json"
    if arsiv.exists():
        try:
            k = json.loads(arsiv.read_text(encoding="utf-8"))
            if k:
                return k, "arsiv"
        except Exception as e:
            print(f"[sonuc] arsiv okunamadi: {e}", flush=True)

    dosya = BET365 / f"{gun:%d%m%Y}.json"
    if not dosya.exists():
        return [], "yok"
    try:
        ham = json.loads(dosya.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[sonuc] {dosya.name} okunamadi: {e}", flush=True)
        return [], "yok"

    kayitlar = []
    for r in ham:
        o = _ms0(r)
        if o is None or round(o, 2) not in ORANLAR:
            continue
        z = _zaman(r.get("Tarih"))
        # Dosya baska gunlerin maclarini da tasiyabilir; yalnizca o gun alinir
        if z is None or z.date() != gun:
            continue
        kayitlar.append({
            "event_id": str(r.get("MatchCode") or "").strip(),
            "home_team": r.get("Ev") or "",
            "away_team": r.get("Dep") or "",
            "league": r.get("Lig") or "",
            "saat": z.strftime("%H:%M"),
        })
    return kayitlar, "bet365 arsivinden yeniden kuruldu"


def ilk_yari_skorlari(gun: dt.date, kodlar: set):
    """{kod: 'e-d'} -- yalnizca istenen kodlar icin, bitmis maclardan."""
    kaynak = fk.FlashscoreKaynak()
    bugun = dt.date.today()
    fark = (gun - bugun).days
    maclar = {}
    for f in (fark - 1, fark, fark + 1):
        if not -7 <= f <= 7:
            continue
        try:
            for m in kaynak.gunun_maclari(f):
                kod = m.get("AA")
                if kod in kodlar and fk.mac_bitti_mi(m):
                    maclar[kod] = m
        except Exception as e:
            print(f"[sonuc] gun {f} listesi alinamadi: {e}", flush=True)

    print(f"[sonuc] {len(maclar)}/{len(kodlar)} mac bitmis olarak bulundu",
          flush=True)

    def tek(oge):
        kod, m = oge
        try:
            iy, _ms = fk.skorlar(m, kaynak.ilk_yari_skoru(kod))
            return kod, iy
        except Exception:
            return kod, ""

    sonuc = {}
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for kod, iy in ex.map(tek, maclar.items()):
            if iy:
                sonuc[kod] = iy
    print(f"[sonuc] {len(sonuc)} macin ilk yari skoru alindi", flush=True)
    return sonuc


def sonuclandir(gun: dt.date):
    kayitlar, kaynak = dunun_listesi(gun)
    if not kayitlar:
        return None

    kodlar = {str(k.get("event_id") or "").strip() for k in kayitlar}
    kodlar.discard("")
    skorlar = ilk_yari_skorlari(gun, kodlar)

    maclar, tutan, tutmayan = [], 0, 0
    for k in kayitlar:
        iy = skorlar.get(str(k.get("event_id") or "").strip())
        if not iy:
            continue
        try:
            e, d = (int(x) for x in iy.split("-", 1))
        except ValueError:
            continue
        tuttu = (e + d) > 0          # update_results.py ile ayni kural
        tutan += tuttu
        tutmayan += not tuttu
        maclar.append({
            "saat": k.get("saat") or "",
            "home_team": k.get("home_team") or "",
            "away_team": k.get("away_team") or "",
            "league": k.get("league") or "",
            "iy": iy,
            "tuttu": tuttu,
        })

    sonuclanan = tutan + tutmayan
    return {
        "tarih": f"{gun:%d.%m.%Y}",
        "kaynak": kaynak,
        "toplam": len(kayitlar),
        "sonuclanan": sonuclanan,
        "tutan": tutan,
        "tutmayan": tutmayan,
        "yuzde": round(100 * tutan / sonuclanan, 1) if sonuclanan else 0.0,
        "maclar": sorted(maclar, key=lambda m: (m["saat"] == "", m["saat"])),
    }


def main():
    gun = dt.date.today() - dt.timedelta(days=1)
    if len(sys.argv) > 1:
        gun = dt.datetime.strptime(sys.argv[1], "%d.%m.%Y").date()
    r = sonuclandir(gun)
    if not r:
        print("Sonuclandirilacak liste bulunamadi.")
        return 1
    print(f"\n{r['tarih']}  (liste kaynagi: {r['kaynak']})")
    print(f"  listedeki mac : {r['toplam']}")
    print(f"  sonuclanan    : {r['sonuclanan']}")
    print(f"  TUTAN         : {r['tutan']}")
    print(f"  tutmayan      : {r['tutmayan']}")
    print(f"  basari        : %{r['yuzde']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
