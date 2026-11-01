"""Telegram gonderim yardimcilari (tahmin grubu icin).

Yalnizca stdlib. telegram_gonder.py'nin Wondiyo kanalina gonderim yolu
bundan bagimsizdir; bu modul yeni tahmin grubunun (maç öncesi + canlı)
ortak altyapisidir.
"""
import html
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{metod}"
SINIR = 3800          # Telegram siniri 4096; paya yer birak


class ChatBulunamadi(Exception):
    pass


def kacir(metin):
    """Telegram HTML yalnizca < > & tanir; kesme/tirnak kacirilmamali."""
    return html.escape(str(metin or ""), quote=False)


def parcala(satirlar):
    """Satir listesini Telegram sinirina gore mesajlara boler."""
    parcalar, simdiki = [], ""
    for satir in satirlar:
        aday = satir if not simdiki else simdiki + "\n" + satir
        if len(aday) > SINIR and simdiki:
            parcalar.append(simdiki)
            simdiki = satir
        else:
            simdiki = aday
    if simdiki:
        parcalar.append(simdiki)
    return parcalar


def _istek(token, metod, veri, timeout=30):
    istek = urllib.request.Request(
        API.format(token=token, metod=metod),
        data=urllib.parse.urlencode(veri).encode())
    with urllib.request.urlopen(istek, timeout=timeout) as c:
        return json.loads(c.read().decode())


def gonder(token, chat_id, metin, yanit=None):
    """Mesaji gonderir, message_id doner. 3 deneme; chat hatasinda istisna."""
    veri = {
        "chat_id": chat_id,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    if yanit:
        # Sonuclandirma mesajlari asil tahminin altina yanit olarak duser
        veri["reply_to_message_id"] = str(yanit)
        veri["allow_sending_without_reply"] = "true"
    for deneme in range(3):
        try:
            c = _istek(token, "sendMessage", veri)
            return (c.get("result") or {}).get("message_id")
        except urllib.error.HTTPError as e:
            govde = e.read().decode(errors="replace")[:300]
            if e.code == 429:            # hiz siniri: soylenen kadar bekle
                try:
                    bekle = json.loads(govde)["parameters"]["retry_after"]
                except Exception:
                    bekle = 5
                time.sleep(int(bekle) + 1)
                continue
            if e.code in (400, 403, 404) and ("chat" in govde.lower()):
                raise ChatBulunamadi(govde)
            if e.code in (400, 401, 403, 404):
                raise RuntimeError(f"Telegram {e.code}: {govde}")
        except Exception as e:
            print(f"  [tg] baglanti hatasi: {e}", flush=True)
        time.sleep(2 * (deneme + 1))
    raise RuntimeError("Telegram'a 3 denemede gonderilemedi")


def hepsini_gonder(token, chat_id, parcalar):
    for i, p in enumerate(parcalar, 1):
        gonder(token, chat_id, p)
        print(f"  mesaj {i}/{len(parcalar)} gonderildi", flush=True)
        time.sleep(1)


def chat_adaylari(token):
    """Botun gordugu sohbetleri yazar (yeni grubun chat id'sini bulmak icin)."""
    izin = urllib.parse.quote(json.dumps(
        ["message", "channel_post", "my_chat_member"]))
    url = (API.format(token=token, metod="getUpdates")
           + f"?allowed_updates={izin}&limit=100")
    try:
        with urllib.request.urlopen(url, timeout=30) as c:
            d = json.loads(c.read().decode())
    except Exception as e:
        print(f"  getUpdates basarisiz: {e}", flush=True)
        return
    gorulen = {}
    for g in d.get("result", []):
        for alan in ("message", "channel_post", "my_chat_member"):
            s = (g.get(alan) or {}).get("chat")
            if s:
                gorulen[s["id"]] = s.get("title") or s.get("username") or "?"
    if not gorulen:
        print("  Hic sohbet gorunmuyor. Botu gruba ekle, gruba bir mesaj at,"
              " sonra butona tekrar bas.", flush=True)
        return
    print("  Botun gordugu sohbetler (TELEGRAM_CHAT_ID_2 olarak birini gir):",
          flush=True)
    for cid, ad in gorulen.items():
        print(f"    {cid}   {ad}", flush=True)
