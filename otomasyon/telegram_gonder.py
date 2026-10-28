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

KOK = Path(__file__).resolve().parent.parent
KAYNAK_DOSYA = KOK / "data" / "halfTimeGoals.json"

API = "https://api.telegram.org/bot{token}/sendMessage"
SINIR = 3800          # Telegram siniri 4096; basliga ve paya yer birakiyoruz
DIGER_LIG = "Diger"


def _mesajlar(kayitlar, tarih):
    """Lig lig grupla, saate gore sirala, 4096 karakteri asmayacak parcalar uret."""
    # Lig alani merged dosyasindan gelir. PC yolunda (match_merger_bot.py) bu
    # alan hic uretilmiyor; o durumda gruplama yapmadan duz liste veriyoruz.
    ligli = any((k.get("league") or "").strip() for k in kayitlar)
    ligler = {}
    for k in kayitlar:
        ad = (k.get("league") or "").strip() or DIGER_LIG
        ligler.setdefault(ad if ligli else "", []).append(k)

    def saat_anahtari(k):
        s = (k.get("saat") or "").strip()
        return (s == "", s)          # saati bos olanlar en sona

    # Ligleri kendi ilk maclarinin saatine gore sirala
    sirali = sorted(ligler.items(), key=lambda it: saat_anahtari(min(it[1], key=saat_anahtari)))

    baslik = (
        f"<b>⚽ İlk Yarı Gol Listesi</b>\n"
        f"\U0001f4c5 {html.escape(tarih)} · {len(kayitlar)} maç"
    )

    # Tum satirlari duz bir listeye ac, sonra sinira gore parcalara bol.
    satirlar = [baslik]
    for lig, maclar in sirali:
        if lig:
            satirlar.append(f"\n<b>\U0001f3c6 {html.escape(lig)}</b>")
        for m in sorted(maclar, key=saat_anahtari):
            saat = html.escape((m.get("saat") or "--:--").strip())
            ev = html.escape((m.get("home_team") or "?").strip())
            dep = html.escape((m.get("away_team") or "?").strip())
            satirlar.append(f"<code>{saat}</code>  {ev} - {dep}")

    parcalar, simdiki = [], ""
    for satir in satirlar:
        aday = satir if not simdiki else simdiki + "\n" + satir
        if len(aday) > SINIR and simdiki:
            parcalar.append(simdiki)
            simdiki = satir.lstrip("\n")
        else:
            simdiki = aday
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
    url = f"https://api.telegram.org/bot{token}/getUpdates"
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
