"""CANLI MAÇ TARAMA -> tahmin grubu.

ADAYLAR: bet365 beraberlik orani TAM OLARAK su basamaklardan birine esit
olan gunun maclari: 3.50  4.00  4.10  4.33  4.50  4.75
(Kaynak bet365/GGAAYYYY.json; mac kodu Flashscore'un kodu.)

KURALLAR (hepsi ayni maca ayri ayri uygulanabilir):
  1) İY 0.5 Üst  -- macin 2-3. dakikasinda, skor 0-0 iken.
                    Gol olmadigi surece 25. dakikaya kadar gonderilebilir
                    (tarama gec baslarsa); 25'ten sonra gonderilmez.
  2) İY 1.5 Üst  -- ilk 5 dakikada gol olmussa (skor tek gol iken).
                    60 sn'lik yoklama araligi icin 6. dakikaya kadar
                    gorulen gol sayilir.
  3) İY 2.5 Üst  -- ilk 20 dakikada 2 gol olmussa (skor iki gol iken).
                    Ayni pay ile 21. dakikaya kadar.
  4) MS 4.5 Üst  -- ilk yari 2-1, 1-2, 3-0 ya da 0-3 bittiyse.
                    Devre arasinda gonderilir; tarama gec baslarsa
                    ikinci yarinin 60. dakikasina kadar.
  Zaten kazanmis bir bahis gonderilmez (or. 2. dk'da 1-0 ise İY 0.5 Üst).

MAÇ ÖNCESİ LİSTESİ (MAÇ ÖNCESİ TERCİHLER'in arsivledigi liste):
  Her baslama saatinden 5 dk once o saatin maclari hatirlatilir; listedeki
  bahis tuttugu an KAZANDI olarak hatirlatmaya yanit duser. Kaybedenler
  ertesi sabahki "dunun tercihleri" ozetinde.

SONUCLANDIRMA (tahmin mesajina yanit olarak):
  İY bahisleri: esik asildigi an KAZANDI; ilk yari esik altinda biterse
                KAYBETTI.
  MS 4.5 Üst:   5. gol geldigi an KAZANDI; mac 4 golun altinda biterse
                KAYBETTI.

VERI: Flashscore gun akisi, 60 sn'de bir.
  AB=1 baslamamis, AB=2 canli, AB=3 bitti
  AC=12 ilk yari, AC=38 devre arasi, AC=13 ikinci yari
  AO  = icinde bulunulan periyodun basladigi an -> dakika buradan
  AG/AH anlik skor, BC/BD ikinci yari golleri -> ilk yari = AG-BC / AH-BD
(01.11.2026'da canli maclar uzerinde dogrulandi, bkz. canli_kesif.py.)

KAYIT: gonderilen/sonuclanan bahisler 'canli-kayit' dalinda
kayit/GG.AA.YYYY.json olarak tutulur (main'e commit atip Pages'i her
dakika yeniden derletmemek icin ayri dal). Tarama yeniden baslatilsa da
ayni bildirim iki kez gitmez.

SURE: GitHub'da bir is en fazla 6 saat surer. Butce dolunca bitmemis mac
varsa tarama kendini yeniden tetikler.
"""
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
import flashscore_kaynak as fk       # noqa: E402
import tg                            # noqa: E402
import tr_isim                       # noqa: E402

KOK = Path(__file__).resolve().parent.parent
BET365 = KOK / "bet365"

BERABERLIK = [3.50, 4.00, 4.10, 4.33, 4.50, 4.75]

R1_BAS, R1_SON = 2, 25       # İY 0.5 Üst gonderim penceresi (dk)
R2_SON = 6                   # ilk gol en gec bu dakikada gorulmus olmali
R3_SON = 21                  # ikinci gol en gec bu dakikada
R4_SKORLAR = {(2, 1), (1, 2), (3, 0), (0, 3)}
R4_SON = 60                  # MS 4.5 Üst en gec bu dakikada gonderilir

BAHIS = {
    # anahtar: (gorunen ad, kapsam, kazanma esigi = toplam gol)
    "iy05": ("İY 0.5 Üst", "iy", 1),
    "iy15": ("İY 1.5 Üst", "iy", 2),
    "iy25": ("İY 2.5 Üst", "iy", 3),
    "ms45": ("MS 4.5 Üst", "ms", 5),
}

YOKLAMA = 60                 # sn
BUTCE = int(os.environ.get("TARAMA_BUTCE_DK", "340")) * 60
VAZGEC_DK = 150              # akista hic gorunmeyen mac icin baslamadan sonra

DAL = "canli-kayit"
API = "https://api.github.com"


# ----------------------------------------------------------------- adaylar
def _sayi(v):
    s = str(v if v is not None else "").strip().replace(",", ".")
    try:
        f = float(s)
    except ValueError:
        return None
    return round(f, 2) if f > 1 else None


def _ms0(r):
    for k in ("MS0 K", "MS0 A"):
        v = _sayi(r.get(k))
        if v is not None:
            return v
    return None


def _zaman(v):
    # bet365 JSON'unda Tarih, Turkiye saatini UTC'ymis gibi yazan epoch'tur;
    # UTC olarak okunmali (bkz. kupon.py).
    try:
        return dt.datetime.fromtimestamp(int(v) / 1000, dt.timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def adaylar(gun):
    dosya = BET365 / f"{gun:%d%m%Y}.json"
    if not dosya.exists():
        return None
    sonuc = {}
    for r in json.loads(dosya.read_text(encoding="utf-8")):
        o = _ms0(r)
        z = _zaman(r.get("Tarih"))
        kod = str(r.get("MatchCode") or "").strip()
        if not kod or o not in BERABERLIK or z is None or z.date() != gun:
            continue
        sonuc[kod] = {"ev": r.get("Ev") or "", "dep": r.get("Dep") or "",
                      "lig": r.get("Lig") or "", "baslama": z,
                      "beraberlik": o}
    return sonuc


# ------------------------------------------------------------ kayit (dal)
class Kayit:
    """canli-kayit dalinda tutulan gunluk kayit. GITHUB_TOKEN yoksa yerel."""

    def __init__(self, gun, klasor="kayit"):
        self.yol = f"{klasor}/{gun:%d.%m.%Y}.json"
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.repo = os.environ.get("GITHUB_REPOSITORY", "")
        self.sha = None
        self.veri = {"tarih": f"{gun:%d.%m.%Y}", "maclar": {}}
        # GITHUB_TOKEN yoksa (yerel deneme) kayit diske yazilir; gun basina ayri dosya
        self.yerel = Path(os.environ.get("KAYIT_DIZIN", "/tmp")) / self.yol.replace("/", "_")

    def _api(self, yontem, yol, govde=None):
        istek = urllib.request.Request(
            f"{API}/repos/{self.repo}/{yol}", method=yontem,
            data=json.dumps(govde).encode() if govde is not None else None,
            headers={"Authorization": f"Bearer {self.token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"})
        with urllib.request.urlopen(istek, timeout=30) as c:
            ham = c.read().decode()
            return json.loads(ham) if ham else {}

    def _dal_hazirla(self):
        try:
            self._api("GET", f"git/ref/heads/{DAL}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            ana = self._api("GET", "git/ref/heads/main")["object"]["sha"]
            self._api("POST", "git/refs", {"ref": f"refs/heads/{DAL}", "sha": ana})
            print(f"[kayit] '{DAL}' dali olusturuldu", flush=True)

    def oku(self):
        if not (self.token and self.repo):
            if self.yerel.exists():
                self.veri = json.loads(self.yerel.read_text(encoding="utf-8"))
            return
        self._dal_hazirla()
        try:
            c = self._api("GET", f"contents/{self.yol}?ref={DAL}")
            self.sha = c["sha"]
            self.veri = json.loads(base64.b64decode(c["content"]).decode())
            print(f"[kayit] okundu: {len(self.veri['maclar'])} mac", flush=True)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            print("[kayit] bugun icin kayit yok, yeni baslaniyor", flush=True)

    def yaz(self):
        metin = json.dumps(self.veri, ensure_ascii=False, indent=1)
        if not (self.token and self.repo):
            self.yerel.write_text(metin, encoding="utf-8")
            return
        govde = {"message": f"canli kayit {self.veri['tarih']}",
                 "content": base64.b64encode(metin.encode()).decode(),
                 "branch": DAL}
        if self.sha:
            govde["sha"] = self.sha
        for _ in range(3):
            try:
                self.sha = self._api("PUT", f"contents/{self.yol}", govde)["content"]["sha"]
                return
            except urllib.error.HTTPError as e:
                if e.code == 409:       # sha eskimis: guncelini al, tekrar dene
                    self.sha = self._api("GET", f"contents/{self.yol}?ref={DAL}")["sha"]
                    govde["sha"] = self.sha
                    continue
                print(f"[kayit] yazilamadi: {e.code}", flush=True)
                return


# ------------------------------------------------------------ mac durumu
def faz(m):
    ab, ac = m.get("AB"), m.get("AC")
    if ab == "1":
        return "once"
    if ab == "3":
        return "bitti" if ac in fk.BITEN_DURUMLAR else "iptal"
    if ab == "2":
        if ac == "12":
            return "1y"
        if ac == "38":
            return "da"
        return "2y"
    return "?"


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def dakika(m, f, simdi):
    bas = _int(m.get("AO")) or _int(m.get("AD"))
    gecen = max(0, int(simdi) - bas) // 60 + 1
    return gecen if f == "1y" else 45 + gecen


def iy_skoru(m, f):
    ag, ah = _int(m.get("AG")), _int(m.get("AH"))
    if f in ("1y", "da"):
        return ag, ah
    if m.get("BC") is None or m.get("BD") is None:
        return None
    return ag - _int(m.get("BC")), ah - _int(m.get("BD"))


def ms_toplam(m, iy):
    # Uzatma/penalti ile biten macta 90 dk skoru: ilk yari + ikinci yari
    if m.get("AC") in ("10", "11") and iy and m.get("BC") is not None:
        return sum(iy) + _int(m.get("BC")) + _int(m.get("BD"))
    return _int(m.get("AG")) + _int(m.get("AH"))


# ------------------------------------------------------------ mesajlar
# ------------------------------------------------------------ mesajlar
# Telegram'da mesajlar iç içe görünmesin diye: başlık, boş satır, maç,
# lig, boş satır, tahmin/skor. Sonuç mesajları da maçın adını taşır.
def _mac(a, skor=None):
    ev = tg.kacir(tr_isim.takim(a["ev"]))
    dep = tg.kacir(tr_isim.takim(a["dep"]))
    if skor is None:
        return f"⚽ <b>{ev} – {dep}</b>"
    return f"⚽ {ev} <b>{skor[0]}–{skor[1]}</b> {dep}"


def _lig(a):
    bayrak, lig = tr_isim.lig(a.get("lig"))
    return f"{bayrak} <i>{tg.kacir(lig)}</i>".strip() if lig else ""


def tahmin_mesaji(a, bahis, dk, skor, iy=None):
    satirlar = ["🔴 <b>CANLI TAHMİN</b>", "", _mac(a)]
    if _lig(a):
        satirlar.append(_lig(a))
    satirlar += ["", f"🎯 <b>{tg.kacir(BAHIS[bahis][0].upper())}</b>"]
    if iy is not None:
        satirlar.append(f"⏸ İlk yarı {iy[0]}–{iy[1]}")
    else:
        satirlar.append(f"⏱ {dk}'  ·  Skor {skor[0]}–{skor[1]}")
    return "\n".join(satirlar)


def sonuc_mesaji(a, ad, durum, skor, an, liste=False):
    ikon = {"kazandi": "✅ <b>KAZANDI</b>",
            "kaybetti": "❌ <b>KAYBETTİ</b>",
            "iptal": "⚪ <b>İPTAL</b>"}[durum]
    satirlar = [f"{ikon}  ·  {tg.kacir(ad)}"]
    if liste:
        satirlar.append("<i>📋 maç öncesi listesinden</i>")
    satirlar += ["", f"{_mac(a, skor)}  ·  {an}"]
    return "\n".join(satirlar)


def _an(m, f, simdi):
    if f in ("1y", "2y"):
        return f"{dakika(m, f, simdi)}'"
    return {"da": "Devre arası", "bitti": "Maç sonu"}.get(f, "")


# ------------------------------------------------------- maç öncesi listesi
# MAÇ ÖNCESİ TERCİHLER'in arşivlediği liste (oncesi/GG.AA.YYYY.json):
#  - her başlama saatinden 5 dk önce o saatin maçları hatırlatılır,
#  - listedeki bahis tuttuğu an KAZANDI olarak hatırlatmaya yanıt düşer.
# Kaybedenler canlı gönderilmez; ertesi sabahki "dünün tercihleri" özetinde.
LISTE_BAHIS = {
    # anahtar: (başlık, kısa ad, skor türü, eşik)
    "ust25": ("MAÇ SONUCU 2.5 ÜST", "2.5 Üst", "ms", 3),
    "ust35": ("MAÇ SONUCU 3.5 ÜST", "3.5 Üst", "ms", 4),
    "iy15":  ("İLK YARI 1.5 ÜST", "İY 1.5 Üst", "iy", 2),
}
HATIRLAT = dt.timedelta(minutes=5)     # başlamadan bu kadar önce
GEC_HATIRLAT = dt.timedelta(minutes=10)  # tarama geç başlarsa bu kadar sonrasına kadar
LISTE_YENILE = 600                       # sn; liste gün içinde güncellenebilir


def liste_yukle(gun):
    k = Kayit(gun, "oncesi")
    try:
        k.oku()
    except Exception as e:
        print(f"[liste] okunamadi: {e}", flush=True)
        return {}
    v = k.veri
    if "ust25" not in v:
        return {}
    liste = {}
    for anahtar, bahisler in (("ust25", ["ust25"]), ("ust35", ["ust35", "iy15"])):
        for m in v.get(anahtar, []):
            kod = m.get("kod")
            if not kod or not m.get("saat"):
                continue
            e = liste.setdefault(kod, {"ev": m["ev"], "dep": m["dep"],
                                       "lig": m.get("lig", ""), "saat": m["saat"],
                                       "bahisler": []})
            for b in bahisler:
                if b not in e["bahisler"]:
                    e["bahisler"].append(b)
    for e in liste.values():
        h, d = (int(x) for x in e["saat"].split(":"))
        e["baslama"] = dt.datetime.combine(gun, dt.time(h, d))
    return liste


def hatirlatma_mesaji(saat, maclar):
    satirlar = [f"⏰ <b>{saat} MAÇLARI</b>", "<i>5 dakika sonra başlıyor</i>"]
    for anahtar, (baslik, _, _, _) in LISTE_BAHIS.items():
        bu = [e for _, e in maclar if anahtar in e["bahisler"]]
        if not bu:
            continue
        satirlar += ["", f"🎯 <b>{baslik}</b>"]
        satirlar += [_mac(e).replace("<b>", "").replace("</b>", "") for e in bu]
    return "\n".join(satirlar)


# ------------------------------------------------------------ tarayici
class Tarayici:
    def __init__(self, gun, token, chat, kayit, adaylar_):
        self.gun, self.token, self.chat = gun, token, chat
        self.kayit, self.adaylar = kayit, adaylar_
        self.liste = {}
        self.degisti = False

    def _st(self, kod):
        return self.kayit.veri["maclar"].setdefault(kod, {"bahis": {}})

    def _gonder(self, metin, yanit=None):
        return tg.gonder(self.token, self.chat, metin, yanit)

    # ---- canlı tahminler
    def ac(self, kod, bahis, dk, skor, iy=None):
        st = self._st(kod)
        if bahis in st["bahis"]:
            return
        mid = self._gonder(tahmin_mesaji(self.adaylar[kod], bahis, dk, skor, iy))
        st["bahis"][bahis] = {"id": mid, "durum": "acik", "dk": dk,
                              "skor": f"{skor[0]}-{skor[1]}"}
        self.degisti = True
        print(f"  -> {BAHIS[bahis][0]:11s} {self.adaylar[kod]['ev']} - "
              f"{self.adaylar[kod]['dep']} "
              f"({'DA' if dk is None else str(dk) + chr(39)}, {skor[0]}-{skor[1]})",
              flush=True)

    def kapat(self, kod, bahis, durum, skor, an):
        b = self._st(kod)["bahis"].get(bahis)
        if not b or b["durum"] != "acik":
            return
        self._gonder(sonuc_mesaji(self.adaylar[kod], BAHIS[bahis][0], durum, skor, an),
                     yanit=b.get("id"))
        b["durum"] = durum
        self.degisti = True
        print(f"  <- {BAHIS[bahis][0]:11s} {durum.upper()}  "
              f"{self.adaylar[kod]['ev']} - {self.adaylar[kod]['dep']}", flush=True)

    def isle(self, kod, m, simdi):
        f = faz(m)
        st = self._st(kod)
        if st.get("son") != f:
            st["son"] = f
            self.degisti = True
        if f in ("once", "?"):
            return

        ag, ah = _int(m.get("AG")), _int(m.get("AH"))
        toplam = ag + ah

        if f == "iptal":
            for b in list(st["bahis"]):
                self.kapat(kod, b, "iptal", (ag, ah), "Maç tamamlanmadı")
            return

        if f == "1y":
            dk = dakika(m, f, simdi)
            if toplam >= 1 and "ilk_gol_dk" not in st:
                st["ilk_gol_dk"] = dk
                self.degisti = True
            if toplam >= 2 and "iki_gol_dk" not in st:
                st["iki_gol_dk"] = dk
                self.degisti = True

            # Once sonuclandir (esik asildiysa kazandi), sonra yeni tahmin:
            # grupta KAZANDI mesaji bir sonraki tahminden once dussun.
            for b in ("iy05", "iy15", "iy25"):
                if toplam >= BAHIS[b][2]:
                    self.kapat(kod, b, "kazandi", (ag, ah), f"{dk}'")

            # Kural 1-3: yalnizca ilk yarida
            if toplam == 0 and R1_BAS <= dk <= R1_SON:
                self.ac(kod, "iy05", dk, (ag, ah))
            if toplam == 1 and st.get("ilk_gol_dk", 99) <= R2_SON:
                self.ac(kod, "iy15", dk, (ag, ah))
            if toplam == 2 and st.get("iki_gol_dk", 99) <= R3_SON:
                self.ac(kod, "iy25", dk, (ag, ah))
            return

        # devre arasi / ikinci yari / bitti
        iy = iy_skoru(m, f)
        if iy is not None and st.get("iy") != list(iy):
            st["iy"] = list(iy)
            self.degisti = True
        iy = tuple(st["iy"]) if st.get("iy") else None

        if iy is not None:
            for b in ("iy05", "iy15", "iy25"):
                durum = "kazandi" if sum(iy) >= BAHIS[b][2] else "kaybetti"
                self.kapat(kod, b, durum, iy, "İlk yarı sonu")

        ms = ms_toplam(m, iy)
        # Kural 4: ilk yari skoru listede ve 5. gol henuz gelmemis
        r4_vakit = f == "da" or (f == "2y" and dakika(m, f, simdi) <= R4_SON)
        if r4_vakit and iy in R4_SKORLAR and ms < 5:
            self.ac(kod, "ms45", None, (ag, ah), iy=iy)
        if ms >= 5:
            self.kapat(kod, "ms45", "kazandi", (ag, ah), _an(m, f, simdi))
        elif f == "bitti":
            self.kapat(kod, "ms45", "kaybetti", (ag, ah), "Maç sonu")

    # ---- maç öncesi listesi
    def hatirlat(self, simdi_dt):
        slotlar = self.kayit.veri.setdefault("liste_slot", {})
        gruplar = {}
        for kod, e in self.liste.items():
            gruplar.setdefault(e["saat"], []).append((kod, e))
        for saat, maclar in sorted(gruplar.items()):
            if saat in slotlar:
                continue
            bas = maclar[0][1]["baslama"]
            if bas - HATIRLAT <= simdi_dt <= bas + GEC_HATIRLAT:
                slotlar[saat] = self._gonder(hatirlatma_mesaji(saat, maclar))
                self.degisti = True
                print(f"  ⏰ {saat} hatirlatmasi ({len(maclar)} mac)", flush=True)

    def liste_isle(self, kod, m, simdi):
        e = self.liste[kod]
        f = faz(m)
        sonlar = self.kayit.veri.setdefault("liste_son", {})
        if sonlar.get(kod) != f:
            sonlar[kod] = f
            self.degisti = True
        if f in ("once", "?", "iptal"):
            return
        ag, ah = _int(m.get("AG")), _int(m.get("AH"))
        if f in ("1y", "da"):
            iy, ms = (ag, ah), ag + ah
        else:
            iy = iy_skoru(m, f)
            ms = ms_toplam(m, iy)
        kazanan = self.kayit.veri.setdefault("liste_kazanan", {}).setdefault(kod, [])
        for b in e["bahisler"]:
            if b in kazanan:
                continue
            _, kisa, tur, esik = LISTE_BAHIS[b]
            if tur == "iy":
                tuttu = iy is not None and sum(iy) >= esik
                skor = iy
                an = _an(m, f, simdi) if f in ("1y", "da") else "İlk yarı sonu"
            else:
                tuttu = ms >= esik
                skor, an = (ag, ah), _an(m, f, simdi)
            if not tuttu:
                continue
            yanit = self.kayit.veri.get("liste_slot", {}).get(e["saat"])
            self._gonder(sonuc_mesaji(e, kisa, "kazandi", skor, an, liste=True),
                         yanit=yanit)
            kazanan.append(b)
            self.degisti = True
            print(f"  ✅ liste {kisa:10s} {e['ev']} - {e['dep']}", flush=True)


def akis(kaynak, gun):
    fark = (gun - dt.date.today()).days
    return {m["AA"]: m for m in kaynak.gunun_maclari(fark) if m.get("AA")}


def yeniden_tetikle(gun):
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not (token and repo):
        return
    istek = urllib.request.Request(
        f"{API}/repos/{repo}/actions/workflows/tahmin.yml/dispatches",
        method="POST",
        data=json.dumps({"ref": "main", "inputs": {
            "hangisi": "canli", "gun": f"{gun:%d.%m.%Y}"}}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"})
    try:
        urllib.request.urlopen(istek, timeout=30)
        print("[tarama] sure doldu, tarama yeniden tetiklendi", flush=True)
    except Exception as e:
        print(f"[tarama] yeniden tetiklenemedi: {e}", flush=True)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID_2", "").strip()
    if not token:
        print("HATA: TELEGRAM_BOT_TOKEN tanimli degil.")
        return 1
    if not chat:
        print("TELEGRAM_CHAT_ID_2 tanimli degil. Yeni grubun id'si araniyor...")
        tg.chat_adaylari(token)
        return 1

    g = os.environ.get("TARAMA_GUN", "").strip()
    gun = dt.datetime.strptime(g, "%d.%m.%Y").date() if g else dt.date.today()

    aday = adaylar(gun)
    if aday is None:
        print(f"HATA: bet365/{gun:%d%m%Y}.json yok.")
        return 1
    print(f"[tarama] {gun:%d.%m.%Y}: {len(aday)} aday mac "
          f"(beraberlik {', '.join(f'{b:.2f}' for b in BERABERLIK)})", flush=True)

    kayit = Kayit(gun)
    kayit.oku()
    t = Tarayici(gun, token, chat, kayit, aday)
    t.liste = liste_yukle(gun)
    liste_zamani = time.time()
    print(f"[liste] mac oncesi listesinde {len(t.liste)} mac", flush=True)
    if not aday and not t.liste:
        return 0
    kaynak = fk.FlashscoreKaynak()
    basla = time.time()

    try:
        while True:
            simdi = time.time()
            if simdi - liste_zamani > LISTE_YENILE:
                yeni = liste_yukle(gun)
                if yeni:
                    t.liste = yeni
                liste_zamani = simdi
            try:
                feed = akis(kaynak, gun)
            except Exception as e:
                print(f"[tarama] akis alinamadi: {e}", flush=True)
                feed = {}

            simdi_dt = dt.datetime.now()
            try:
                t.hatirlat(simdi_dt)
            except tg.ChatBulunamadi:
                raise
            except Exception as e:
                print(f"[tarama] hatirlatma gonderilemedi: {e}", flush=True)

            for kod, m in feed.items():
                for kume, islev in ((aday, t.isle), (t.liste, t.liste_isle)):
                    if kod not in kume:
                        continue
                    try:
                        islev(kod, m, simdi)
                    except tg.ChatBulunamadi:
                        raise
                    except Exception as e:
                        print(f"[tarama] {kod} islenemedi: {e}", flush=True)

            if t.degisti:
                kayit.yaz()
                t.degisti = False

            # Bitmemis mac kaldi mi? (canli adaylar + mac oncesi listesi)
            kalan, yakin = [], False
            izlenen = [(a["baslama"], kayit.veri["maclar"].get(kod, {}).get("son"))
                       for kod, a in aday.items()]
            izlenen += [(e["baslama"], kayit.veri.get("liste_son", {}).get(kod))
                        for kod, e in t.liste.items()]
            for baslama, son in izlenen:
                if son in ("bitti", "iptal"):
                    continue
                if simdi_dt > baslama + dt.timedelta(minutes=VAZGEC_DK):
                    continue
                kalan.append(baslama)
                # 5 dk kala hatirlatma da kacmasin diye 6 dk once yakin say
                if son in ("1y", "da", "2y") or \
                        baslama - simdi_dt <= dt.timedelta(minutes=6):
                    yakin = True

            if not kalan:
                print("[tarama] butun maclar bitti.", flush=True)
                break
            if time.time() - basla > BUTCE:
                yeniden_tetikle(gun)
                break

            if yakin:
                bekle = YOKLAMA
            else:
                ilk = min(kalan)
                bekle = max(YOKLAMA, min(
                    int((ilk - simdi_dt).total_seconds()) - 360, 600))
            time.sleep(bekle)
    except tg.ChatBulunamadi as e:
        print(f"HATA: {e}\nGirilen TELEGRAM_CHAT_ID_2 calismadi. Adaylar:")
        tg.chat_adaylari(token)
        return 1
    finally:
        if t.degisti:
            kayit.yaz()

    return 0


if __name__ == "__main__":
    sys.exit(main())
