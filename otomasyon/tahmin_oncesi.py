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

Kurallar birbirinden bagimsizdir: bir mac ikisine birden uyarsa iki
listede de gorunur. Mesajda oran yazilmaz (Wondiyo kanalindaki gibi).

En sonda gunun kuponu (otomasyon/kupon.py) ayni gruba gonderilir.

SONUCLANDIRMA: gonderilen liste (kupon dahil) 'canli-kayit' dalinda
oncesi/GG.AA.YYYY.json olarak arsivlenir. Ertesi gun butona basilinca
once dunun listesi Flashscore'un bitmis mac skorlariyla sonuclandirilir
(mac mac + yuzde), sonra gunun listesi gider. Ayni gun ikinci kez
basilirsa liste birlestirilir; sonuclandirma bir kez gonderilir.
  2.5 Üst  : macin 90 dk toplam golu >= 3
  3.5 Üst  : >= 4
  İY 1.5 Üst: ilk yari toplam golu >= 2
  Kupon    : 4 macin hepsinde 2.5 Üst tutarsa kazandi
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


def tercihler(gun, sadece_baslamamis=True):
    kayitlar = bet365_kayitlari(gun)
    if kayitlar is None:
        return None
    simdi = dt.datetime.now()
    ust25, ust35 = [], []
    for r in kayitlar:
        z = _zaman(r.get("Tarih"))
        if z is None or z.date() != gun:
            continue                      # baska gunun maci
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
        }
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


def sonuc_mesaji(arsiv, kaynak, skor, gun):
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
        yuzde = f"%{round(100 * tutan / biten)}" if biten else "\u2013"
        ozet.append(f"\U0001f3af {kisa}: <b>{tutan}/{biten}</b> \u00b7 {yuzde}")

    kupon = arsiv.get("kupon")
    if kupon and kupon.get("maclar"):
        detay += ["", "<b>G\u00dcN\u00dcN KUPONU</b>"]
        durumlar = []
        for m in kupon["maclar"]:
            s = skor.get(m.get("kod"))
            ev, dep = tg.kacir(m["ev"]), tg.kacir(m["dep"])
            if not s:
                durumlar.append(None)
                detay.append(f"\u26aa <code>  \u2013  </code>  {ev} \u2013 {dep}")
                continue
            e, d_ = s["ms"]
            durumlar.append(e + d_ >= 3)
            im = TUTTU if e + d_ >= 3 else TUTMADI
            detay.append(f"{im} <code>{e}-{d_}</code>  {ev} \u2013 {dep}")
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


def dunu_sonuclandir(gun):
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
    return sonuc_mesaji(arsiv, kaynak, skor, gun), k


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
        "",
    ]
    for m in k["maclar"]:
        satirlar.append(f"<code>{tg.kacir(m['saat'])}</code>  "
                        f"<b>{tg.kacir(m['ev'])} – {tg.kacir(m['dep'])}</b>")
        satirlar.append(f"        maç sonucu 2.5 üst &gt; "
                        f"<b>{m['ust25']:.2f}</b>")
    satirlar += ["", f"\U0001f4b0 <b>TOPLAM ORAN: {k['toplam']:.2f}</b>"]
    if not k.get("hedefte", True):
        satirlar.append("<i>(bugünkü adaylarla 4.00-10.00 aralığına "
                        "ulaşılamadı, en yakını seçildi)</i>")
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
    # 1) Dunun tercihleri: sonuclandirma (hata verirse bugunun listesini engellemesin)
    sonuc_parcalari, dun_kayit = [], None
    try:
        sonuc_parcalari, dun_kayit = dunu_sonuclandir(gun - dt.timedelta(days=1))
    except Exception as e:
        print(f"UYARI: dun sonuclandirilamadi: {e}", flush=True)

    # 2) Bugunun listesi + kupon
    parcalar = tercih_mesaji(t, gun)
    k = None
    try:
        k = kupon_modulu.kupon(gun)
        if k and k["maclar"]:
            parcalar += kupon_mesaji(k)
        else:
            print("Kupon olusturulamadi (uygun mac yok).", flush=True)
    except Exception as e:
        print(f"UYARI: kupon olusturulamadi: {e}", flush=True)

    try:
        if sonuc_parcalari:
            tg.hepsini_gonder(token, chat, sonuc_parcalari)
            dun_kayit.veri["sonuclandi"] = True
            dun_kayit.yaz()
        tg.hepsini_gonder(token, chat, parcalar)
    except tg.ChatBulunamadi as e:
        print(f"HATA: {e}\nGirilen TELEGRAM_CHAT_ID_2 calismadi. Adaylar:")
        tg.chat_adaylari(token)
        return 1

    # 3) Yarin sonuclandirilabilsin diye arsivle
    try:
        bugunu_arsivle(gun, t, k if (k and k.get("maclar")) else None)
    except Exception as e:
        print(f"UYARI: arsivlenemedi: {e}", flush=True)
    print("OK: tercihler gonderildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
