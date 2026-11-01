"""MAÇ ÖNCESİ TERCİHLER -> tahmin grubu.

Kaynak: bet365/GGAAYYYY.json (Flashscore'dan cekilen bet365 oranlari).
Yalnizca henuz baslamamis maclar alinir. Esitlikler TAM (aralik yok).

KURAL 1 -- "Maç sonucu 2.5 Üst"
    2.5 Ust orani  : 1.53  1.57  1.61
    beraberlik     : 4.33  4.50  4.75
    NOT: 1.61, bet365 sitesinde 8/13'un gosterimi. Flashscore ayni oran
    basamagini 1.62 olarak veriyor (8/13 = 1.6154); ikisi de kabul edilir.

KURAL 2 -- "3.5 Üst" + "İlk yarı 1.5 Üst"
    beraberlik     : 5.00  5.25  5.75  6.00  7.00  8.00

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
        u25 = oran(r, "UST25")
        if u25 in UST25_ORANLARI and ms0 in UST25_BERABERLIK:
            ust25.append({**m, "ust25": u25})
        elif ms0 in UST35_BERABERLIK:
            ust35.append({**m, "ust35": oran(r, "UST35"),
                          "iyust15": oran(r, "IYUST15")})
    anahtar = lambda m: m["saat"]
    return {"ust25": sorted(ust25, key=anahtar),
            "ust35": sorted(ust35, key=anahtar)}


def _mac_satiri(m):
    bayrak, lig = tr_isim.lig(m["lig"])
    ev = tg.kacir(tr_isim.takim(m["ev"]))
    dep = tg.kacir(tr_isim.takim(m["dep"]))
    return (f"<code>{m['saat']}</code>  <b>{ev} – {dep}</b>",
            f"{bayrak} {tg.kacir(lig)}".strip())


def _o(v):
    return f"{v:.2f}" if v else "–"


def tercih_mesaji(t, gun):
    satirlar = [
        "<b>\U0001f4cb MAÇ ÖNCESİ TERCİHLER</b>",
        f"<i>{tg.kacir(tr_isim.tarih(f'{gun:%d.%m.%Y}'))}</i>",
    ]
    if t["ust25"]:
        satirlar += ["", "<b>\U0001f3af MAÇ SONUCU 2.5 ÜST</b>"]
        for m in t["ust25"]:
            ust, alt = _mac_satiri(m)
            satirlar += [ust, f"        {alt} · 2.5 Üst <b>@{_o(m['ust25'])}</b>"]
    if t["ust35"]:
        satirlar += ["", "<b>\U0001f3af 3.5 ÜST + İLK YARI 1.5 ÜST</b>"]
        for m in t["ust35"]:
            ust, alt = _mac_satiri(m)
            satirlar += [ust, f"        {alt}",
                         f"        3.5 Üst <b>@{_o(m['ust35'])}</b> · "
                         f"İY 1.5 Üst <b>@{_o(m['iyust15'])}</b>"]
    if not (t["ust25"] or t["ust35"]):
        satirlar += ["", "<i>Bugün kriterlere uyan başlamamış maç yok.</i>"]
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
    print(f"2.5 Ust: {len(t['ust25'])} mac | 3.5 Ust + IY 1.5: {len(t['ust35'])} mac",
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
