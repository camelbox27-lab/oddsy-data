"""@ilkyarigol ("İY 1.5 Üst") kanali: sabah raporu ve test gonderimi.

Gun icindeki 5 dk once hatirlatmalari ve KAZANDI bildirimleri canli
taramada (canli_tarama.py, Tarayici.hatirlat / liste_isle) yapilir.
Bu modul:
  rapor(gun)  -- dunun kanalda duyurulan IY 1.5 Ust maclarinin sonuclari
                 (her sabah, mac oncesi akisinda bir kez)
  test()      -- bugunun siradaki IY 1.5 Ust maclarini 'test' ibaresiyle
                 hemen gonderir (kayda yazmaz; gercek hatirlatma yine gider)
"""
import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canli_tarama            # noqa: E402
import tg                      # noqa: E402
import tr_isim                 # noqa: E402

TUTTU, TUTMADI = "✅", "❌"


def _anahtar():
    return (os.environ.get("IYGOL_BOT_TOKEN", "").strip()
            or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())


def _kanal():
    return os.environ.get("IYGOL_CHAT", "").strip() or "@ilkyarigol"


def _iy_maclari(gun):
    """Gunun mac oncesi arsivindeki IY 1.5 Ust maclari (3.5 Ust listesiyle ayni)."""
    k = canli_tarama.Kayit(gun, "oncesi")
    k.oku()
    return k.veri.get("ust35", []) if "ust25" in k.veri else []


def rapor(gun, skorlar_fn):
    """Kanalda duyurulmus maclarin sonuc raporu. Gonderildiyse True."""
    token = _anahtar()
    if not token:
        return False
    kayit = canli_tarama.Kayit(gun, "kayit")
    kayit.oku()
    if kayit.veri.get("iy_rapor_gonderildi"):
        print("[iy-kanal] rapor zaten gonderilmis", flush=True)
        return False
    duyurulan = {s for s, mid in (kayit.veri.get("iy_slot") or {}).items() if mid}
    maclar = [m for m in _iy_maclari(gun) if m.get("saat") in duyurulan]
    if not maclar:
        print("[iy-kanal] dun kanalda duyurulan mac yok, rapor yok", flush=True)
        return False
    skor = skorlar_fn(gun)
    satirlar, tutan, biten = [], 0, 0
    for m in sorted(maclar, key=lambda m: m["saat"]):
        ev, dep = tg.kacir(tr_isim.takim(m["ev"])), tg.kacir(tr_isim.takim(m["dep"]))
        s = skor.get(m.get("kod"))
        if not s:
            satirlar.append(f"⚪ <code>  –  </code>  {ev} – {dep}")
            continue
        e, d = s["iy"]
        ok = e + d >= 2
        biten += 1
        tutan += ok
        satirlar.append(f"{TUTTU if ok else TUTMADI} <code>İY {e}-{d}</code>  {ev} – {dep}")
    yuzde = f"%{round(100 * tutan / biten)}" if biten else "–"
    metin = "\n".join([
        "<b>\U0001f4ca DÜNÜN SONUÇLARI</b>",
        f"<i>{tg.kacir(tr_isim.tarih(f'{gun:%d.%m.%Y}'))}</i>",
        "",
        f"\U0001f3af İlk Yarı 1.5 Üst: <b>{tutan}/{biten}</b> · {yuzde}",
        "",
    ] + satirlar)
    for parca in tg.parcala(metin.split("\n")):
        tg.gonder(token, _kanal(), parca)
    kayit.veri["iy_rapor_gonderildi"] = True
    kayit.yaz()
    print(f"[iy-kanal] rapor gonderildi: {tutan}/{biten}", flush=True)
    return True


def test():
    token = _anahtar()
    if not token:
        print("HATA: bot anahtari yok")
        return 1
    gun = dt.date.today()
    simdi = dt.datetime.now()
    gruplar = {}
    for m in _iy_maclari(gun):
        h, d = (int(x) for x in m["saat"].split(":"))
        if dt.datetime.combine(gun, dt.time(h, d)) > simdi:
            gruplar.setdefault(m["saat"], []).append(
                (m.get("kod"), {**m, "bahisler": ["iy15"]}))
    if not gruplar:
        print("Bugun baslamamis IY 1.5 Ust maci yok.")
        return 0
    saat = sorted(gruplar)[0]
    metin = canli_tarama.iy_kanal_mesaji(saat, gruplar[saat]) + \
        "\n\n<i>\U0001f9ea Test mesajı — gerçek bildirim maçtan 5 dk önce gelecek.</i>"
    mid = tg.gonder(token, _kanal(), metin)
    print(f"OK: test gonderildi ({saat}, mesaj {mid})")
    return 0


if __name__ == "__main__":
    sys.exit(test() if sys.argv[1:] == ["test"] else 0)
