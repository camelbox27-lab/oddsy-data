"""Siteye yuklenen Ilk Yari Gol listesini Telegram grubuna gonderir.

Kaynak: data/halfTimeGoals.json  (filter_bot.py'nin urettigi dosya)
Cikti : Telegram sendMessage  -> Lig / Ev - Deplasman / Saat

Gerekli ortam degiskenleri (GitHub repo secret'i olarak tanimlanir):
  TELEGRAM_BOT_TOKEN   BotFather'dan alinan token
  TELEGRAM_CHAT_ID     Grubun chat id'si (grup icin eksi ile baslar, or. -1001234567890)

Sadece stdlib kullanir; pip kurulumu gerektirmez.
"""
import datetime as dt
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tr_isim                       # noqa: E402

KOK = Path(__file__).resolve().parent.parent
KAYNAK_DOSYA = KOK / "data" / "halfTimeGoals.json"

API = "https://api.telegram.org/bot{token}/sendMessage"
SINIR = 3800          # Telegram siniri 4096; basliga ve paya yer birakiyoruz
DIGER_LIG = "Diger"


def _kacir(metin):
    """Telegram HTML yalnizca < > & tanir; kesme/tirnak kacirilmamali."""
    return html.escape(str(metin or ""), quote=False)


def _mesajlar(kayitlar, tarih):
    """Lig lig grupla, saate gore sirala, 4096 karakteri asmayan parcalar uret.

    Lig ve takim adlari Almanca geliyor (kaynak Flashscore AT); burada
    yalnizca GOSTERIM icin Turkce'ye cevrilir, veri dosyasi degismez.
    """
    def saat_anahtari(k):
        s = (k.get("saat") or "").strip()
        return (s == "", s)          # saati bos olanlar en sona

    # Lig alani merged dosyasindan gelir. PC yolunda (match_merger_bot.py) bu
    # alan hic uretilmiyor; o durumda gruplama yapmadan duz liste veriyoruz.
    ligli = any((k.get("league") or "").strip() for k in kayitlar)
    ligler = {}
    for k in kayitlar:
        if ligli:
            bayrak, ad = tr_isim.lig(k.get("league"))
            anahtar = (f"{bayrak} {ad}".strip() if ad else DIGER_LIG)
        else:
            anahtar = ""
        ligler.setdefault(anahtar, []).append(k)

    # Ligleri kendi ilk maclarinin saatine gore sirala
    sirali = sorted(ligler.items(),
                    key=lambda it: saat_anahtari(min(it[1], key=saat_anahtari)))

    baslik = (
        f"<b>\u26bd İLK YARI GOL LİSTESİ</b>\n"
        f"<i>{_kacir(tr_isim.tarih(tarih))} · {len(kayitlar)} maç</i>"
    )

    # (lig_basligi, satir) ciftleri; lig ikiye bolunurse baslik tekrar yazilir.
    ogeler = [(None, baslik)]
    for lig_adi, maclar in sirali:
        ustbilgi = f"<b>{_kacir(lig_adi)}</b>" if lig_adi else None
        if ustbilgi:
            ogeler.append((None, "\n" + ustbilgi))
        for m in sorted(maclar, key=saat_anahtari):
            saat = _kacir((m.get("saat") or "--:--").strip())
            ev = _kacir(tr_isim.takim(m.get("home_team")) or "?")
            dep = _kacir(tr_isim.takim(m.get("away_team")) or "?")
            ogeler.append((ustbilgi, f"<code>{saat}</code>  {ev} \u2013 {dep}"))

    parcalar, simdiki, acik = [], "", None
    for ustbilgi, satir in ogeler:
        aday = satir if not simdiki else simdiki + "\n" + satir
        if len(aday) > SINIR and simdiki:
            parcalar.append(simdiki)
            # Yarida kalan ligin basligini yeni parcanin basina tasi
            if ustbilgi:
                simdiki = f"{ustbilgi} <i>(devam)</i>\n{satir}"
            else:
                simdiki = satir.lstrip("\n")
        else:
            simdiki = aday
        acik = ustbilgi
    if simdiki:
        parcalar.append(simdiki)
    return parcalar


def _gonder(token, chat_id, metin):
    veri = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    istek = urllib.request.Request(API.format(token=token), data=veri)
    with urllib.request.urlopen(istek, timeout=30) as c:
        return json.loads(c.read().decode())


def _chat_adaylari(token):
    """getUpdates ile botun gordugu sohbetleri listeler (sadece kurulum icin)."""
    # my_chat_member (bot kanala/gruba eklendi) varsayilan olarak GELMEZ,
    # allowed_updates ile acikca istemek gerekir.
    izin = urllib.parse.quote(json.dumps(
        ["message", "channel_post", "edited_channel_post", "my_chat_member"]))
    url = (f"https://api.telegram.org/bot{token}/getUpdates"
           f"?allowed_updates={izin}&limit=100")
    try:
        with urllib.request.urlopen(url, timeout=30) as c:
            d = json.loads(c.read().decode())
    except Exception as e:
        print(f"  getUpdates basarisiz: {e}", flush=True)
        return
    gorulen = {}
    for g in d.get("result", []):
        for alan in ("message", "channel_post", "my_chat_member", "edited_message"):
            sohbet = (g.get(alan) or {}).get("chat")
            if sohbet:
                gorulen[sohbet["id"]] = sohbet.get("title") or sohbet.get("username") or sohbet.get("first_name") or "?"
    if not gorulen:
        print("  Hic sohbet gorunmuyor. Botu gruba ekle ve gruba bir mesaj at,", flush=True)
        print("  sonra bu butona tekrar bas.", flush=True)
        return
    print("  Bulunan sohbetler (TELEGRAM_CHAT_ID olarak birini gir):", flush=True)
    for cid, ad in gorulen.items():
        print(f"    {cid}   {ad}", flush=True)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        print("HATA: TELEGRAM_BOT_TOKEN secret'i tanimli degil.", flush=True)
        return 1
    if not chat_id:
        # Kurulum yardimi: botu gruba ekleyip bir mesaj attiktan sonra bu
        # adim grubun chat id'sini konsola yazar; secret olarak o deger girilir.
        print("TELEGRAM_CHAT_ID tanimli degil. Aday sohbetler araniyor...", flush=True)
        _chat_adaylari(token)
        return 1

    if not KAYNAK_DOSYA.exists():
        print(f"HATA: {KAYNAK_DOSYA.name} yok. Once BULTEN YUKLE calistir.", flush=True)
        return 1

    kayitlar = json.loads(KAYNAK_DOSYA.read_text(encoding="utf-8"))
    if not kayitlar:
        print("HATA: Ilk Yari Gol listesi bos. Once BULTEN YUKLE calistir.", flush=True)
        return 1

    tarih = (kayitlar[0].get("tarih") or "").strip()
    bugun = dt.datetime.now().strftime("%d.%m.%Y")
    if tarih and tarih != bugun:
        # Engellemiyoruz; kullanici dunun listesini bilerek gonderebilir.
        print(f"UYARI: listedeki tarih {tarih}, bugun {bugun}.", flush=True)

    parcalar = _mesajlar(kayitlar, tarih or bugun)
    print(f"{len(kayitlar)} mac, {len(parcalar)} mesaj gonderilecek.", flush=True)

    for i, parca in enumerate(parcalar, 1):
        for deneme in range(3):
            try:
                _gonder(token, chat_id, parca)
                print(f"  mesaj {i}/{len(parcalar)} gonderildi", flush=True)
                break
            except urllib.error.HTTPError as e:
                govde = e.read().decode(errors="replace")[:300]
                # Token/chat_id hatasi tekrar denemekle duzelmez
                if e.code in (400, 401, 403, 404):
                    print(f"HATA {e.code}: {govde}", flush=True)
                    # "chat not found" / yetki hatasi: dogru chat id'yi kendimiz bulalim
                    if "chat not found" in govde or "chat_id" in govde or e.code in (403, 404):
                        print(f"Girilen TELEGRAM_CHAT_ID calismadi. Botun gordugu "
                              f"sohbetler araniyor...", flush=True)
                        _chat_adaylari(token)
                    return 1
                print(f"  gecici hata {e.code}, tekrar deneniyor...", flush=True)
            except Exception as e:
                print(f"  baglanti hatasi: {e}, tekrar deneniyor...", flush=True)
            time.sleep(2 * (deneme + 1))
        else:
            print(f"HATA: mesaj {i} gonderilemedi.", flush=True)
            return 1
        time.sleep(1)   # Telegram hiz siniri

    print("OK: Telegram'a gonderildi.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
