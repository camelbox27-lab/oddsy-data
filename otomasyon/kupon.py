"""Gunun kuponu: 4 mac, hepsi 'maç sonucu 2.5 üst', Iddaa oraniyla.

ADAYLAR: bet365 beraberlik orani TAM OLARAK su basamaklardan birine esit
olan bugunku maclar (aralik degil):
    4.10  4.33  4.50  4.75  5.00  5.25
Bu, sitedeki "Gunun Tercihleri" mantiginin ayni kaynagi ve ayni tam
eslesme yaklasimi.

ORAN: Iddaa'nin 2.5 Ust orani. Iddaa gunluk bulteninde bu alan GitHub'dan
cekildiginde neredeyse hep bos (asil kaynagi olan Mackolik mac sayfalari
403 veriyor), bu yuzden oran Mackolik'in engellenmemis livedata akisindan
aliniyor (bkz. otomasyon/livedata.py, [22] = 2.5 UST).

ESLESTIRME: bet365 tarafi Flashscore'dan geldigi icin takim adlari
Almanca; Iddaa tarafi Turkce. Adlar normalize edilip benzerlik oraniyla
eslestiriliyor, ayni baslama saati ek puan sayiliyor. Eslesmeyen mac
kupona alinmaz -- yanlis mac yazmaktansa az mac yazmak yeglenir.

SECIM: toplam oran HEDEF araliginda (4.00 - 10.00) kalacak sekilde 4 mac.
Bu araliga dusen butun 4'lu kombinasyonlar cikarilir, aralarindan rastgele
biri secilir. Rastgelelik GUNE gore sabit: ayni gun butona tekrar
basildiginda ayni kupon cikar.

Adaylarin 2.5 ust oranlari genelde dusuktur (beraberlik orani 4.10-5.25
olan maclarda belirgin bir favori vardir, gol beklentisi yuksektir), bu
yuzden bazi gunlerde 4.00'e ulasilamayabilir. O durumda carpimi en yuksek
dortlu secilir ve mesajda hedefe ulasilamadigi belirtilir.
"""
import datetime as dt
import json
import itertools
import random
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import livedata                           # noqa: E402

BET365 = KOK / "bet365"
IDDAA = KOK / "iddaa" / "gunluk" / "gunlukmaclar.json"

BERABERLIK = [4.10, 4.33, 4.50, 4.75, 5.00, 5.25]
MAC_SAYISI = 4
HEDEF_ALT, HEDEF_UST = 4.00, 10.00
EN_FAZLA_ADAY = 28     # C(28,4)=20475; kombinasyon sayisi makul kalsin
ESIK = 0.72            # takim adi benzerligi alt siniri

_ONEK = re.compile(r'\b(fc|sk|ac|as|sc|cd|fk|if|bk|il|afc|cf|ca|sv|vfl|vfb|'
                   r'rc|ud|cs|us|ss|sd|ask|tsv|fsv|bsc)\b')


def _nrm(s):
    s = (s or "").lower()
    for a, b in (('ı', 'i'), ('ş', 's'), ('ğ', 'g'), ('ü', 'u'),
                 ('ö', 'o'), ('ç', 'c'), ('â', 'a'), ('î', 'i')):
        s = s.replace(a, b)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = _ONEK.sub(' ', s)
    return re.sub(r'[^a-z0-9]', '', s)


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
    for k in ("MS0 K", "MS0 A", "MS0_K", "MS0_A"):
        v = _sayi(r.get(k))
        if v is not None:
            return v
    return None


def adaylar(gun: dt.date):
    """Beraberlik orani tam eslesen bugunku maclar."""
    dosya = BET365 / f"{gun:%d%m%Y}.json"
    if not dosya.exists():
        print(f"[kupon] {dosya.name} yok", flush=True)
        return []
    try:
        ham = json.loads(dosya.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[kupon] {dosya.name} okunamadi: {e}", flush=True)
        return []

    simdi = dt.datetime.now()
    hepsi, baslamamis = [], []
    for r in ham:
        o = _ms0(r)
        if o is None or round(o, 2) not in BERABERLIK:
            continue
        z = _zaman(r.get("Tarih"))
        if z is None or z.date() != gun:
            continue
        k = {
            "kod": str(r.get("MatchCode") or "").strip(),
            "ev": r.get("Ev") or "",
            "dep": r.get("Dep") or "",
            "saat": z.strftime("%H:%M"),
            "beraberlik": round(o, 2),
        }
        hepsi.append(k)
        if z > simdi:
            baslamamis.append(k)
    # Baslamamis mac varsa onlar; yoksa gunun tamami (gec basilmis olabilir)
    secilen = baslamamis or hepsi
    print(f"[kupon] {len(hepsi)} aday, {len(baslamamis)} tanesi baslamamis",
          flush=True)
    return secilen


def _iddaa_eslestir(maclar):
    """Her maca iddaa kaydini ekler (bulunabilenlere)."""
    if not IDDAA.exists():
        print("[kupon] iddaa bulteni yok", flush=True)
        return
    try:
        idd = json.loads(IDDAA.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[kupon] iddaa bulteni okunamadi: {e}", flush=True)
        return

    hazir = [(_nrm(i.get("Ev Sahibi")), _nrm(i.get("Konuk Ekip")), i)
             for i in idd]
    for m in maclar:
        e, d = _nrm(m["ev"]), _nrm(m["dep"])
        en_iyi, puan_iyi = None, 0.0
        for ne, nd, i in hazir:
            p = (SequenceMatcher(None, e, ne).ratio()
                 + SequenceMatcher(None, d, nd).ratio()) / 2
            if str(i.get("Saat") or "").strip() == m["saat"]:
                p += 0.10          # ayni baslama saati guclu ipucu
            if p > puan_iyi:
                en_iyi, puan_iyi = i, p
        if en_iyi is not None and puan_iyi >= ESIK:
            m["iddaa"] = en_iyi
            m["eslesme"] = round(puan_iyi, 2)


def kupon(gun: dt.date):
    maclar = adaylar(gun)
    if not maclar:
        return None
    _iddaa_eslestir(maclar)
    eslesen = [m for m in maclar if m.get("iddaa")]
    print(f"[kupon] {len(eslesen)} mac iddaa bulteninde bulundu", flush=True)
    if not eslesen:
        return None

    oranlar = livedata.ust_alt_25(gun)
    uygun = []
    for m in eslesen:
        kod = str(m["iddaa"].get("MS Kodu") or "").strip()
        ust = _sayi((oranlar.get(kod) or {}).get("ust25"))
        if ust is None:
            # livedata vermediyse bultenin kendi alani (cogu zaman bos)
            ust = _sayi(m["iddaa"].get("AU 2.5 Ust"))
        if ust is None:
            continue
        uygun.append({
            "kod": m.get("kod", ""),
            "ev": m["iddaa"].get("Ev Sahibi") or m["ev"],
            "dep": m["iddaa"].get("Konuk Ekip") or m["dep"],
            "saat": m["saat"],
            "lig": m["iddaa"].get("Lig") or "",
            "beraberlik": m["beraberlik"],
            "ust25": round(ust, 2),
        })

    print(f"[kupon] {len(uygun)} macin 2.5 ust orani bulundu", flush=True)
    if not uygun:
        return None

    secim, toplam, hedefte = _dortlu_sec(uygun, gun)
    secim = sorted(secim, key=lambda m: m["saat"])
    return {"tarih": f"{gun:%d.%m.%Y}", "maclar": secim,
            "toplam": round(toplam, 2), "aday_sayisi": len(uygun),
            "hedefte": hedefte}


def _carpim(dortlu):
    t = 1.0
    for m in dortlu:
        t *= m["ust25"]
    return t


def _dortlu_sec(uygun, gun):
    """(secim, toplam_oran, hedef_araliginda_mi)"""
    rastgele = random.Random(f"{gun:%Y-%m-%d}")

    if len(uygun) <= MAC_SAYISI:
        return uygun, _carpim(uygun), HEDEF_ALT <= _carpim(uygun) <= HEDEF_UST

    # Kombinasyon sayisini sinirlamak gerekirse, orani hedefe en uygun
    # olanlari tut. "En yuksek oranlilar" demek yanlis olurdu: oranlarin
    # hepsi yuksekse carpim hedefin USTUNE tasar, o zaman dusuk oranlilara
    # ihtiyac olur. Dort macin ortalama hedefi, araligin ortasinin 4. koku.
    hedef_tek = ((HEDEF_ALT * HEDEF_UST) ** 0.5) ** (1 / MAC_SAYISI)
    havuz = sorted(uygun, key=lambda m: abs(m["ust25"] - hedef_tek))[:EN_FAZLA_ADAY]

    def uzaklik(t):
        if t < HEDEF_ALT:
            return HEDEF_ALT - t
        if t > HEDEF_UST:
            return t - HEDEF_UST
        return 0.0

    hedefteki = []
    en_iyi, en_iyi_uzaklik, en_iyi_carpim = None, float("inf"), 0.0
    for c in itertools.combinations(havuz, MAC_SAYISI):
        t = _carpim(c)
        if HEDEF_ALT <= t <= HEDEF_UST:
            hedefteki.append(c)
        u = uzaklik(t)
        if u < en_iyi_uzaklik:
            en_iyi, en_iyi_uzaklik, en_iyi_carpim = c, u, t

    if hedefteki:
        secim = rastgele.choice(hedefteki)
        print(f"[kupon] hedef araliga dusen {len(hedefteki)} kombinasyon, "
              f"biri secildi", flush=True)
        return list(secim), _carpim(secim), True

    print(f"[kupon] UYARI: {HEDEF_ALT}-{HEDEF_UST} araligina ulasilamadi; "
          f"hedefe en yakin carpim {en_iyi_carpim:.2f}", flush=True)
    return list(en_iyi), en_iyi_carpim, False


def main():
    gun = dt.date.today()
    if len(sys.argv) > 1:
        gun = dt.datetime.strptime(sys.argv[1], "%d.%m.%Y").date()
    k = kupon(gun)
    if not k:
        print("Kupon olusturulamadi.")
        return 1
    print(f"\nGUNUN KUPONU  {k['tarih']}  ({k['aday_sayisi']} aday icinden)")
    for m in k["maclar"]:
        print(f"  {m['saat']}  {m['ev']} - {m['dep']}  "
              f"maç sonucu 2.5 üst > {m['ust25']:.2f}")
    print(f"  TOPLAM ORAN: {k['toplam']:.2f}"
          + ("" if k["hedefte"] else f"  (hedef {HEDEF_ALT}-{HEDEF_UST} disi)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
