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
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def tercihler(gun):
    kayitlar = bet365_kayitlari(gun)
    if kayitlar is None:
        return None
    simdi = dt.datetime.now()
    ust25, ust35 = [], []
    for r in kayitlar:
        z = _zaman(r.get("Tarih"))
        if z is None or z.date() != gun or z <= simdi:
            continue                      # baska gun ya da baslamis mac
        ms0 = oran(r, "MS0")
        if ms0 is None:
            continue
        m = {
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
    parcalar = tercih_mesaji(t, gun)

    try:
        k = kupon_modulu.kupon(gun)
        if k and k["maclar"]:
            parcalar += kupon_mesaji(k)
        else:
            print("Kupon olusturulamadi (uygun mac yok).", flush=True)
    except Exception as e:
        print(f"UYARI: kupon olusturulamadi: {e}", flush=True)

    try:
        tg.hepsini_gonder(token, chat, parcalar)
    except tg.ChatBulunamadi as e:
        print(f"HATA: {e}\nGirilen TELEGRAM_CHAT_ID_2 calismadi. Adaylar:")
        tg.chat_adaylari(token)
        return 1
    print("OK: tercihler gonderildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
