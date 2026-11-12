"""MAÇ ÖNCESİ TERCİHLER -> tahmin grubu.

Kaynak: bet365/GGAAYYYY.json (Flashscore'dan cekilen bet365 oranlari).
Yalnizca henuz baslamamis maclar alinir. Esitlikler TAM (aralik yok).

KURAL 1 -- "Maç sonucu 2.5 Üst"   (iki sarttan HERHANGI BIRI yeter)
    2.5 Ust orani  : 1.53  1.57  1.61
    VEYA
    beraberlik     : 4.33  4.50  4.75
    NOT: 1.61, bet365 sitesinde 8/13'un gosterimi. Flashscore ayni oran
    basamagini 1.62 olarak veriyor (8/13 = 1.6154); ikisi de kabul edilir.

KURAL 2 -- "3.5 Üst" ve "İlk yarı 1.5 Üst" (ayri listeler, ayni maclar)
    beraberlik     : 5.00  5.25  5.75  6.00  7.00  8.00

Yalnizca otomasyon/ligler.py'deki ligler (majör ligler ve alt ligleri;
kadin, altyapi, rezerv yok). Kurallar birbirinden bagimsizdir: bir mac ikisine birden uyarsa iki
listede de gorunur. Mesajda oran yazilmaz (Wondiyo kanalindaki gibi).

En sonda gunun kuponu (otomasyon/kupon.py) ayni gruba gonderilir:
1 x 3.5 Üst, 1 x İY 1.5 Üst, 2 x 2.5 Üst, listelerden en dusuk oranlilar.

SONUCLANDIRMA: gonderilen liste (kupon dahil) 'canli-kayit' dalinda
oncesi/GG.AA.YYYY.json olarak arsivlenir. Ertesi gun butona basilinca
once dunun listesi Flashscore'un bitmis mac skorlariyla sonuclandirilir
(mac mac + yuzde), sonra gunun listesi gider. Ayni gun ikinci kez
basilirsa liste birlestirilir; sonuclandirma bir kez gonderilir.
  2.5 Üst  : macin 90 dk toplam golu >= 3
  3.5 Üst  : >= 4
  İY 1.5 Üst: ilk yari toplam golu >= 2
  Kupon    : her mac kendi bahsiyle; hepsi tutarsa kazandi
Arsivi olmayan gun (bu ozellikten onceki gunler) bet365 dosyasindan ayni
kurallarla yeniden kurulur; kupon o durumda sonuclandirilamaz.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canli_tarama                  # noqa: E402  (kayit dali + skor yardimcilari)
import kupon as kupon_modulu         # noqa: E402
from ligler import lig_uygun         # noqa: E402
import tg                            # noqa: E402
import tr_isim                       # noqa: E402

KOK = Path(__file__).resolve().parent.parent
BET365 = KOK / "bet365"

UST25_ORANLARI = [1.53, 1.57, 1.61, 1.62]
UST25_BERABERLIK = [4.33, 4.50, 4.75]
UST35_BERABERLIK = [5.00, 5.25, 5.75, 6.00, 7.00, 8.00]


def _sayi(v):
    s = str(v if v is not None else "").strip().replace(",", ".")
    if not s:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    return round(f, 2) if f > 1 else None


def oran(r, ad):
    """Once kapanis (K), yoksa acilis (A)."""
    for son in (" K", " A"):
        v = _sayi(r.get(ad + son))
        if v is not None:
            return v
    return None


def _zaman(v):
    try:
        # bet365 JSON'unda Tarih, Turkiye saatini UTC'ymis gibi yazilmis epoch'tur
        # (pandas naive datetime'i boyle serilestiriyor). UTC olarak okunmali;
        # yerel saat diliminde okumak +3 saat kaydirir.
        return dt.datetime.fromtimestamp(int(v) / 1000, dt.timezone.utc).replace(tzinfo=None)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def bet365_kayitlari(gun):
    dosya = BET365 / f"{gun:%d%m%Y}.json"
    if not dosya.exists():
        return None
    return json.loads(dosya.read_text(encoding="utf-8"))


def _maclar(gun, sadece_baslamamis=True):
    """Lig filtresine uyan, (istenirse) baslamamis, beraberlik orani olan maclar:
    [(bet365 kaydi, mac)]"""
    kayitlar = bet365_kayitlari(gun)
    if kayitlar is None:
        return None
    simdi = dt.datetime.now()
    sonuc = []
    for r in kayitlar:
        z = _zaman(r.get("Tarih"))
        if z is None or z.date() != gun:
            continue                      # baska gunun maci
        if not lig_uygun(r.get("Lig"), r.get("Ev"), r.get("Dep")):
            continue                      # kadin / altyapi / listede olmayan lig
        if sadece_baslamamis and z <= simdi:
            continue                      # baslamis mac
        ms0 = oran(r, "MS0")
        if ms0 is None:
            continue
        m = {
            "kod": str(r.get("MatchCode") or "").strip(),
            "saat": z.strftime("%H:%M"),
            "ev": r.get("Ev") or "",
            "dep": r.get("Dep") or "",
            "lig": r.get("Lig") or "",
            "beraberlik": ms0,
            "oran": {a: oran(r, a) for a in ("UST25", "UST35", "IYUST15")},
        }
        sonuc.append((r, m))
    return sonuc


def genel_maclar(gun):
    """Kupon icin yedek havuz: kurala bakmadan butun uygun maclar."""
    return [m for _, m in (_maclar(gun) or [])]


def tercihler(gun, sadece_baslamamis=True):
    maclar = _maclar(gun, sadece_baslamamis)
    if maclar is None:
        return None
    ust25, ust35 = [], []
    for r, m in maclar:
        ms0 = m["beraberlik"]
        if oran(r, "UST25") in UST25_ORANLARI or ms0 in UST25_BERABERLIK:
            ust25.append(m)
        if ms0 in UST35_BERABERLIK:
            ust35.append(m)
    anahtar = lambda m: m["saat"]
    return {"ust25": sorted(ust25, key=anahtar),
            "ust35": sorted(ust35, key=anahtar)}


def _bolum(baslik, maclar):
    """Wondiyo kanalindaki bicim: lig basligi + saat / ev - deplasman."""
    satirlar = ["", f"<b>\U0001f3af {baslik}</b>"]
    ligler = {}
    for m in maclar:
        bayrak, lig = tr_isim.lig(m["lig"])
        ligler.setdefault(f"{bayrak} {lig}".strip(), []).append(m)
    for lig, grup in sorted(ligler.items(), key=lambda it: it[1][0]["saat"]):
        satirlar.append(f"<b>{tg.kacir(lig)}</b>")
        for m in grup:
            ev = tg.kacir(tr_isim.takim(m["ev"]))
            dep = tg.kacir(tr_isim.takim(m["dep"]))
            satirlar.append(f"<code>{m['saat']}</code>  {ev} \u2013 {dep}")
    return satirlar


def tercih_mesaji(t, gun):
    satirlar = [
        "<b>\U0001f4cb MA\u00c7 \u00d6NCES\u0130 TERC\u0130HLER</b>",
        f"<i>{tg.kacir(tr_isim.tarih(f'{gun:%d.%m.%Y}'))}</i>",
    ]
    if t["ust25"]:
        satirlar += _bolum("MA\u00c7 SONUCU 2.5 \u00dcST", t["ust25"])
    if t["ust35"]:
        satirlar += _bolum("MA\u00c7 SONUCU 3.5 \u00dcST", t["ust35"])
        satirlar += _bolum("\u0130LK YARI 1.5 \u00dcST", t["ust35"])
    if not (t["ust25"] or t["ust35"]):
        satirlar += ["", "<i>Bug\u00fcn kriterlere uyan ba\u015flamam\u0131\u015f ma\u00e7 yok.</i>"]
    return tg.parcala(satirlar)


# ------------------------------------------------------------ sonuclandirma
def _skorlar(gun):
    """{kod: {"ms": (e, d), "iy": (e, d)}} -- yalnizca bitmis maclar."""
    sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
    import flashscore_kaynak as fk
    fark = (gun - dt.date.today()).days
    sonuc = {}
    for m in fk.FlashscoreKaynak().gunun_maclari(fark):
        if not fk.mac_bitti_mi(m):
            continue
        iy = canli_tarama.iy_skoru(m, "bitti")
        if iy is None:
            continue
        ag, ah = canli_tarama._int(m.get("AG")), canli_tarama._int(m.get("AH"))
        if m.get("AC") in ("10", "11") and m.get("BC") is not None:
            # uzatma/penalti: 90 dk skoru = ilk yari + ikinci yari
            ag = iy[0] + canli_tarama._int(m.get("BC"))
            ah = iy[1] + canli_tarama._int(m.get("BD"))
        sonuc[m["AA"]] = {"ms": (ag, ah), "iy": tuple(iy)}
    return sonuc


KURAL = {
    # bolum: (baslik, kisa ad, hangi skor, esik)
    "ust25": ("MA\u00c7 SONUCU 2.5 \u00dcST", "2.5 \u00dcst", "ms", 3),
    "ust35": ("MA\u00c7 SONUCU 3.5 \u00dcST", "3.5 \u00dcst", "ms", 4),
    "iy15":  ("\u0130LK YARI 1.5 \u00dcST", "\u0130Y 1.5 \u00dcst", "iy", 2),
}
TUTTU, TUTMADI = "\u2705", "\u274c"


def sonuc_mesaji(arsiv, kaynak, skor, gun, toplam=None):
    bolumler = {"ust25": arsiv.get("ust25", []), "ust35": arsiv.get("ust35", []),
                "iy15": arsiv.get("ust35", [])}
    ozet, detay = [], []
    for anahtar, maclar in bolumler.items():
        if not maclar:
            continue
        baslik, kisa, tur, esik = KURAL[anahtar]
        tutan = biten = 0
        detay += ["", f"<b>{baslik}</b>"]
        for m in sorted(maclar, key=lambda m: m.get("saat", "")):
            s = skor.get(m.get("kod"))
            ev = tg.kacir(tr_isim.takim(m["ev"]))
            dep = tg.kacir(tr_isim.takim(m["dep"]))
            if not s:
                detay.append(f"\u26aa <code>  \u2013  </code>  {ev} \u2013 {dep}")
                continue
            e, d_ = s[tur]
            tuttu = e + d_ >= esik
            biten += 1
            tutan += tuttu
            on = "\u0130Y " if tur == "iy" else ""
            im = TUTTU if tuttu else TUTMADI
            detay.append(f"{im} <code>{on}{e}-{d_}</code>  {ev} \u2013 {dep}")
        if toplam is not None:
            toplam["tutan"] += tutan
            toplam["biten"] += biten
        yuzde = f"%{round(100 * tutan / biten)}" if biten else "\u2013"
        ozet.append(f"\U0001f3af {kisa}: <b>{tutan}/{biten}</b> \u00b7 {yuzde}")

    kupon = arsiv.get("kupon")
    if kupon and kupon.get("maclar"):
        detay += ["", "<b>G\u00dcN\u00dcN KUPONU</b>"]
        durumlar = []
        for m in kupon["maclar"]:
            s = skor.get(m.get("kod"))
            ev = tg.kacir(tr_isim.takim(m["ev"]))
            dep = tg.kacir(tr_isim.takim(m["dep"]))
            # eski kuponlarda bahis alani yok: hepsi 2.5 Ust idi
            _, kisa, tur, esik = KURAL[m.get("bahis", "ust25")]
            if not s:
                durumlar.append(None)
                detay.append(f"\u26aa <code>  \u2013  </code>  {ev} \u2013 {dep} \u00b7 {kisa}")
                continue
            e, d_ = s[tur]
            durumlar.append(e + d_ >= esik)
            im = TUTTU if e + d_ >= esik else TUTMADI
            on = "\u0130Y " if tur == "iy" else ""
            detay.append(f"{im} <code>{on}{e}-{d_}</code>  {ev} \u2013 {dep} \u00b7 {kisa}")
        if False in durumlar:
            kd = "\u274c KAYBETT\u0130"
        elif None in durumlar:
            kd = "\u26aa sonu\u00e7lanmad\u0131"
        else:
            kd = "\u2705 KAZANDI"
        ozet.append(f"\U0001f3ab Kupon: <b>{kd}</b> \u00b7 {kupon.get('toplam', 0):.2f}")

    if not ozet:
        return []
    satirlar = ["<b>\U0001f4ca D\u00dcN\u00dcN TERC\u0130HLER\u0130</b>",
                f"<i>{tg.kacir(tr_isim.tarih(f'{gun:%d.%m.%Y}'))}</i>", ""] + ozet
    if kaynak != "arsiv":
        satirlar.append("<i>(liste o g\u00fcn ar\u015fivlenmemi\u015f, oranlardan yeniden kuruldu)</i>")
    return tg.parcala(satirlar + detay)


def dunu_sonuclandir(gun, toplam=None):
    """(mesaj parcalari, kayit) -- gonderildikten sonra kayit isaretlenmeli."""
    k = canli_tarama.Kayit(gun, "oncesi")
    k.oku()
    if k.veri.get("sonuclandi"):
        print(f"{gun:%d.%m.%Y} zaten sonuclandirilmis.", flush=True)
        return [], None
    if "ust25" in k.veri:
        arsiv, kaynak = k.veri, "arsiv"
    else:
        t = tercihler(gun, sadece_baslamamis=False)
        if t is None:
            print(f"{gun:%d.%m.%Y} icin arsiv de bet365 dosyasi da yok.", flush=True)
            return [], None
        arsiv, kaynak = {"ust25": t["ust25"], "ust35": t["ust35"]}, "yeniden"
    skor = _skorlar(gun)
    print(f"{gun:%d.%m.%Y}: {len(skor)} bitmis mac skoru alindi "
          f"(liste kaynagi: {kaynak})", flush=True)
    k.veri = {**arsiv, "tarih": f"{gun:%d.%m.%Y}"}
    return sonuc_mesaji(arsiv, kaynak, skor, gun, toplam), k


# ------------------------------------------------------ canlı tahmin raporu
CANLI_AD = {"iy05": "İY 0.5 Üst", "iy15": "İY 1.5 Üst",
            "iy25": "İY 2.5 Üst", "ms45": "MS 4.5 Üst"}


def canli_ozet(gun, toplam=None):
    """Dünün canlı tahminlerinin raporu: kural kural tuttu/toplam + maç maç.
    (mesaj parcalari, kayit) döner; gönderilince kayit işaretlenmeli."""
    k = canli_tarama.Kayit(gun)
    k.oku()
    if k.veri.get("ozet_gonderildi"):
        print(f"{gun:%d.%m.%Y} canli ozeti zaten gonderilmis.", flush=True)
        return [], None
    adlar = {}
    for r in bet365_kayitlari(gun) or []:
        adlar[str(r.get("MatchCode") or "").strip()] = (r.get("Ev") or "", r.get("Dep") or "")

    gruplar = {b: [] for b in CANLI_AD}
    for kod, st in k.veri.get("maclar", {}).items():
        for b, x in st.get("bahis", {}).items():
            if b in gruplar:
                gruplar[b].append((x.get("durum"), adlar.get(kod, ("?", "?"))))
    if not any(gruplar.values()):
        print(f"{gun:%d.%m.%Y}: canli tahmin yok.", flush=True)
        return [], None

    ozet, detay, ct_ = [], [], 0
    cb = 0
    for b, liste in gruplar.items():
        if not liste:
            continue
        tutan = sum(1 for d_, _ in liste if d_ == "kazandi")
        biten = sum(1 for d_, _ in liste if d_ in ("kazandi", "kaybetti"))
        acik = len(liste) - biten
        ct_ += tutan
        cb += biten
        yuzde = f"%{round(100 * tutan / biten)}" if biten else "–"
        ozet.append(f"🎯 {CANLI_AD[b]}: <b>{tutan}/{biten}</b> · {yuzde}"
                    + (f"  <i>({acik} sonuçlanmadı)</i>" if acik else ""))
        detay += ["", f"<b>{CANLI_AD[b].upper()}</b>"]
        for d_, (ev, dep) in liste:
            im = {"kazandi": "✅", "kaybetti": "❌"}.get(d_, "⚪")
            detay.append(f"{im} {tg.kacir(tr_isim.takim(ev))} – {tg.kacir(tr_isim.takim(dep))}")
    if toplam is not None:
        toplam["tutan"] += ct_
        toplam["biten"] += cb
    ozet.append(f"🔴 Canlı toplam: <b>{ct_}/{cb}</b> · "
                + (f"%{round(100 * ct_ / cb)}" if cb else "–"))
    satirlar = ["<b>🔴 DÜNÜN CANLI TAHMİNLERİ</b>",
                f"<i>{tg.kacir(tr_isim.tarih(f'{gun:%d.%m.%Y}'))}</i>", ""] + ozet
    return satirlar + detay, k


def bugunu_arsivle(gun, t, k_kupon):
    """Gonderilen listeyi arsive yazar; ayni gun tekrar basilirsa birlestirir."""
    k = canli_tarama.Kayit(gun, "oncesi")
    k.oku()
    eski = k.veri if "ust25" in k.veri else {}
    def birlestir(a, b):
        gorulen = {m.get("kod") for m in a}
        return a + [m for m in b if m.get("kod") not in gorulen]
    k.veri = {
        "tarih": f"{gun:%d.%m.%Y}",
        "ust25": birlestir(eski.get("ust25", []), t["ust25"]),
        "ust35": birlestir(eski.get("ust35", []), t["ust35"]),
        # ilk gonderilen kupon gecerli; sonradan basmak kuponu degistirmez
        "kupon": eski.get("kupon") or (
            {"maclar": k_kupon["maclar"], "toplam": k_kupon["toplam"]} if k_kupon else None),
        "sonuclandi": False,
    }
    k.yaz()


def kupon_mesaji(k):
    satirlar = [
        "<b>\U0001f3ab GÜNÜN KUPONU</b>",
        f"<i>{tg.kacir(tr_isim.tarih(k['tarih']))}</i>",
    ]
    for m in k["maclar"]:
        bayrak, lig = tr_isim.lig(m.get("lig", ""))
        ev = tg.kacir(tr_isim.takim(m["ev"]))
        dep = tg.kacir(tr_isim.takim(m["dep"]))
        satirlar += ["",
                     f"<code>{tg.kacir(m['saat'])}</code>  <b>{ev} – {dep}</b>",
                     f"{bayrak} {tg.kacir(lig)}".strip(),
                     f"\U0001f3af {tg.kacir(kupon_modulu.BAHISLER[m['bahis']][1])} · <b>{m['oran']:.2f}</b>"]
    satirlar += ["", f"\U0001f4b0 <b>TOPLAM ORAN: {k['toplam']:.2f}</b>",
                 "<i>(bet365 oranları)</i>"]
    return tg.parcala(satirlar)


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

    gun = dt.date.today()
    t = tercihler(gun)
    if t is None:
        print(f"HATA: bet365/{gun:%d%m%Y}.json yok.")
        return 1
    print(f"2.5 Ust: {len(t['ust25'])} mac | 3.5 Ust / IY 1.5 Ust: {len(t['ust35'])} mac",
          flush=True)
    # SADECE_LISTE=1: yalnizca bugunun listesi (baslamamis maclar) yeniden
    # gonderilir ve arsive eklenir; raporlar ve kupon gitmez.
    if os.environ.get("SADECE_LISTE") == "1":
        try:
            tg.hepsini_gonder(token, chat, tercih_mesaji(t, gun))
        except tg.ChatBulunamadi as e:
            print(f"HATA: {e}")
            return 1
        bugunu_arsivle(gun, t, None)
        print("OK: liste gonderildi.")
        return 0

    # SADECE_KUPON=1: yalnizca bugunun kuponu (yeniden) olusturulup gonderilir;
    # arsivdeki kupon bununla degistirilir (yarin bu sonuclandirilir).
    if os.environ.get("SADECE_KUPON") == "1":
        k = kupon_modulu.kupon(gun, t, genel_maclar(gun))
        if not k:
            print("Kupon olusturulamadi (uygun mac yok).")
            return 1
        try:
            tg.hepsini_gonder(token, chat, kupon_mesaji(k))
        except tg.ChatBulunamadi as e:
            print(f"HATA: {e}")
            return 1
        ak = canli_tarama.Kayit(gun, "oncesi")
        ak.oku()
        if "ust25" in ak.veri:
            ak.veri["kupon"] = {"maclar": k["maclar"], "toplam": k["toplam"]}
            ak.yaz()
        else:
            bugunu_arsivle(gun, t, k)
        print("OK: kupon gonderildi.")
        return 0

    # SADECE_EKSIK=1: bugunun listesi tekrar gonderilmez; yalnizca henuz
    # gitmemis olanlar gider (dunun raporlari, bugunun kuponu).
    sadece_eksik = os.environ.get("SADECE_EKSIK") == "1"
    dun = gun - dt.timedelta(days=1)
    toplam = {"tutan": 0, "biten": 0}

    # 1) Dunun raporlari: mac oncesi listesi + kupon, canli tahminler.
    #    Hata verirlerse bugunun listesini engellemesinler.
    sonuc_parcalari, dun_kayit = [], None
    try:
        sonuc_parcalari, dun_kayit = dunu_sonuclandir(dun, toplam)
    except Exception as e:
        print(f"UYARI: dun sonuclandirilamadi: {e}", flush=True)
    canli_satirlari, canli_kayit = [], None
    try:
        canli_satirlari, canli_kayit = canli_ozet(dun, toplam)
    except Exception as e:
        print(f"UYARI: canli ozeti cikarilamadi: {e}", flush=True)
    canli_parcalari = []
    if canli_satirlari:
        # Genel toplam: maç öncesi listesi + canlı tahminler (kupon hariç);
        # yalnızca iki rapor birlikte gidiyorsa anlamlı.
        if toplam["biten"] and sonuc_parcalari:
            genel = (f"📊 <b>DÜNÜN TOPLAMI</b> (maç öncesi + canlı): "
                     f"<b>{toplam['tutan']}/{toplam['biten']}</b> · "
                     f"%{round(100 * toplam['tutan'] / toplam['biten'])}")
            canli_satirlari = canli_satirlari[:3] + [genel, ""] + canli_satirlari[3:]
        canli_parcalari = tg.parcala(canli_satirlari)

    # 2) Bugunun listesi + kupon
    parcalar = [] if sadece_eksik else tercih_mesaji(t, gun)
    k = None
    kupon_gitti = False
    if sadece_eksik:
        try:
            ak = canli_tarama.Kayit(gun, "oncesi")
            ak.oku()
            kupon_gitti = bool(ak.veri.get("kupon"))
        except Exception as e:
            print(f"UYARI: bugunun arsivi okunamadi: {e}", flush=True)
    if not kupon_gitti:
        try:
            k = kupon_modulu.kupon(gun, t, genel_maclar(gun))
            if k and k["maclar"]:
                parcalar += kupon_mesaji(k)
            else:
                print("Kupon olusturulamadi (uygun mac yok).", flush=True)
        except Exception as e:
            print(f"UYARI: kupon olusturulamadi: {e}", flush=True)
    else:
        print("Bugunun kuponu zaten gonderilmis.", flush=True)

    try:
        if sonuc_parcalari:
            tg.hepsini_gonder(token, chat, sonuc_parcalari)
            dun_kayit.veri["sonuclandi"] = True
            dun_kayit.yaz()
        if canli_parcalari:
            tg.hepsini_gonder(token, chat, canli_parcalari)
            canli_kayit.veri["ozet_gonderildi"] = True
            canli_kayit.yaz()
        if parcalar:
            tg.hepsini_gonder(token, chat, parcalar)
    except tg.ChatBulunamadi as e:
        print(f"HATA: {e}\nGirilen TELEGRAM_CHAT_ID_2 calismadi. Adaylar:")
        tg.chat_adaylari(token)
        return 1

    # 3) Yarin sonuclandirilabilsin diye arsivle
    try:
        if sadece_eksik:
            ak = canli_tarama.Kayit(gun, "oncesi")
            ak.oku()
            if "ust25" in ak.veri and not ak.veri.get("kupon") and k and k.get("maclar"):
                ak.veri["kupon"] = {"maclar": k["maclar"], "toplam": k["toplam"]}
                ak.yaz()
        else:
            bugunu_arsivle(gun, t, k if (k and k.get("maclar")) else None)
    except Exception as e:
        print(f"UYARI: arsivlenemedi: {e}", flush=True)
    print("OK: tercihler gonderildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
