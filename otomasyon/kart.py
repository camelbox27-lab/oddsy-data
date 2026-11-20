"""Oto-BOT surpriz kartlari (Telegram'a gorsel olarak gider).

Her surpriz mac icin 1080x1350 bir kart: mac, tahmin ve ayni acilis
oranlariyla oynanmis gecmis maclardan ornekler. Oran ve sayi yazilmaz.
HTML olarak uretilir, Chromium (Playwright) ile PNG'ye cevrilir.
"""
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tr_isim  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
LOGO = (KOK / "wondiyo" / "ikon.svg").read_text(encoding="utf-8").replace(
    '<rect width="192" height="192" rx="42" fill="#0d0f14"/>', "")

TARAF = {"1": "Ev sahibi", "0": "Beraberlik", "2": "Deplasman"}
TEMA = {  # tur -> (vurgu, ikinci, etiket)
    "iyms": ("#a78bfa", "#f472b6", "İY/MS SÜRPRİZİ"),
    "alti": ("#fb923c", "#facc15", "GOL SÜRPRİZİ"),
}

_e = lambda s: html.escape(str(s or ""))


def _skor(s):
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)", str(s or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _lig_gecmis(ad):
    """'NORWAY ELITESERIEN' / 'Ligue 1' -> okunur bicim."""
    ad = str(ad or "").strip()
    return ad.title() if ad.isupper() else ad


def _tarih(t):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(t))
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else _e(t)


def _iyms_aciklama(c):
    iy, ms = c.split("/")
    iy_y = "Ev sahibi önde" if iy == "1" else "Deplasman önde" if iy == "2" else "Beraberlik"
    ms_y = "Beraberlik" if ms == "0" else ("Ev sahibi kazanır" if ms == "1" else "Deplasman kazanır")
    return iy_y, ms_y


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;height:1350px;background:#090c11;font-family:Inter,sans-serif;color:#eef2f7;overflow:hidden;position:relative}
.g1{position:absolute;width:980px;height:980px;right:-430px;top:-470px;background:radial-gradient(circle,var(--v1a),transparent 62%)}
.g2{position:absolute;width:900px;height:900px;left:-460px;bottom:-420px;background:radial-gradient(circle,var(--v2a),transparent 62%)}
.cizgi{position:absolute;inset:0;background:repeating-linear-gradient(135deg,rgba(255,255,255,.022) 0 2px,transparent 2px 26px)}
.ic{position:relative;height:100%;padding:64px 70px 0;display:flex;flex-direction:column}
.tepe{display:flex;align-items:center;justify-content:space-between}
.marka{display:flex;align-items:center;gap:16px}
.marka svg{width:64px;height:64px;background:#0f141c;border:2px solid #1f2733;border-radius:18px;padding:5px}
.marka span{font-family:'Archivo Black',Inter,sans-serif;font-size:32px;letter-spacing:5px}
.etiket{font-size:19px;font-weight:800;letter-spacing:2.4px;padding:12px 22px;border-radius:99px;color:var(--v1);border:2px solid var(--v1);background:rgba(10,12,17,.7)}
.mac{margin-top:46px;padding:34px 38px;border-radius:34px;background:linear-gradient(160deg,rgba(26,32,44,.95),rgba(14,18,26,.95));border:2px solid #232c3a;position:relative;overflow:hidden}
.mac::before{content:"";position:absolute;left:0;top:0;bottom:0;width:8px;background:linear-gradient(180deg,var(--v1),var(--v2))}
.ust{display:flex;justify-content:space-between;align-items:center;font-size:21px;font-weight:700;color:#8792a6;letter-spacing:.4px}
.saat{font-size:24px;font-weight:800;color:#fff;background:#1c2431;border-radius:14px;padding:8px 16px;letter-spacing:.5px}
.takimlar{margin-top:20px;display:flex;flex-direction:column;gap:4px}
.takimlar b{font-size:52px;line-height:1.12;font-weight:900;letter-spacing:-1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.takimlar i{font-style:normal;font-size:20px;font-weight:800;color:#566276;letter-spacing:4px;margin:2px 0 2px 4px}
.tahmin{margin-top:26px;display:flex;align-items:center;gap:34px}
.buyuk{font-family:'Archivo Black',Inter,sans-serif;font-size:150px;line-height:.9;letter-spacing:-3px;background:linear-gradient(120deg,var(--v1),var(--v2));-webkit-background-clip:text;color:transparent;padding-bottom:6px}
.acik{display:flex;flex-direction:column;gap:14px}
.acik div{display:flex;flex-direction:column}
.acik span{font-size:18px;font-weight:800;letter-spacing:2.4px;color:#69758a}
.acik b{font-size:30px;font-weight:800}
.baslik{margin:34px 0 16px;font-size:19px;font-weight:800;letter-spacing:3px;color:#7d889c;display:flex;align-items:center;gap:14px}
.baslik::after{content:"";flex:1;height:2px;background:linear-gradient(90deg,#2a3342,transparent)}
.satir{display:flex;align-items:center;gap:18px;padding:15px 22px;border-radius:20px;background:rgba(18,23,32,.85);border:2px solid #1d2531;margin-bottom:11px}
.satir .t{width:150px;display:flex;flex-direction:column}
.satir .t b{font-size:20px;font-weight:800}
.satir .t span{font-size:15px;font-weight:700;color:#5d697d;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.satir .k{flex:1;min-width:0;font-size:24px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.satir .s{display:flex;gap:8px;align-items:center}
.sk{min-width:76px;text-align:center;font-size:22px;font-weight:800;border-radius:12px;padding:7px 10px;background:#1b2330;color:#c9d2df}
.sk small{display:block;font-size:12px;letter-spacing:1.5px;color:#5d697d;font-weight:800}
.vurgu{background:linear-gradient(120deg,var(--v1),var(--v2));color:#0b0d12}
.vurgu small{color:rgba(11,13,18,.65)}
.dip{position:absolute;left:70px;right:70px;bottom:34px;display:flex;justify-content:space-between;font-size:17px;font-weight:600;color:#4f5a6c;letter-spacing:1.2px}
"""


def _sayfa(tur, govde, gun):
    v1, v2, etiket = TEMA[tur]
    a = lambda renk, al: "rgba({},{},{},{})".format(*(int(renk[i:i + 2], 16) for i in (1, 3, 5)), al)
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&family=Archivo+Black&display=swap" rel="stylesheet">
<style>:root{{--v1:{v1};--v2:{v2};--v1a:{a(v1, .26)};--v2a:{a(v2, .16)}}}{CSS}</style></head><body>
<div class="g1"></div><div class="g2"></div><div class="cizgi"></div>
<div class="ic">
  <div class="tepe"><div class="marka">{LOGO}<span>WONDİYO</span></div><div class="etiket">💥 {etiket}</div></div>
  {govde}
</div>
<div class="dip"><span>wondiyo.com.tr · {_e(tr_isim.tarih(gun))}</span><span>18+ · Bilgi amaçlıdır</span></div>
</body></html>"""


def _mac_blogu(m):
    bayrak, lig = tr_isim.lig(m.get("lig", ""))
    return f"""<div class="mac">
    <div class="ust"><span>{_e(lig)}</span><span class="saat">{_e(m['saat'])}</span></div>
    <div class="takimlar"><b>{_e(tr_isim.takim(m['ev']))}</b><i>VS</i><b>{_e(tr_isim.takim(m['dep']))}</b></div>"""


def _ornek_satiri(o, vurgu_ms=False, vurgu_iyms=None):
    iy, ms = _skor(o["iy"]), _skor(o["ms"])
    iy_y = f"{iy[0]}-{iy[1]}" if iy else "–"
    ms_y = f"{ms[0]}-{ms[1]}" if ms else "–"
    ms_v = " vurgu" if vurgu_ms and ms and sum(ms) >= 6 else ""
    # 6+ kartinda ilk yari skoru gosterilmez (eski arsivde bazi IY skorlari hatali)
    iy_k = "" if vurgu_ms else f'<div class="sk"><small>İY</small>{iy_y}</div>'
    son = ""
    if vurgu_iyms is not None:
        son = f'<div class="sk{" vurgu" if o["iyms"] == vurgu_iyms else ""}"><small>İY/MS</small>{_e(o["iyms"])}</div>'
    return f"""<div class="satir"><div class="t"><b>{_tarih(o['tarih'])}</b><span>{_e(_lig_gecmis(o['lig']))}</span></div>
      <div class="k">{_e(o['ev'])} – {_e(o['dep'])}</div>
      <div class="s">{iy_k}<div class="sk{ms_v}"><small>MS</small>{ms_y}</div>{son}</div></div>"""


def iyms_html(m, ornekler, gun):
    iy_y, ms_y = _iyms_aciklama(m["iyms"])
    govde = _mac_blogu(m) + f"""
    <div class="tahmin"><div class="buyuk">{_e(m['iyms'])}</div>
      <div class="acik"><div><span>İLK YARI</span><b>{iy_y}</b></div><div><span>MAÇ SONU</span><b>{ms_y}</b></div></div></div>
  </div>
  <div class="baslik">BENZER AÇILIŞ ORANLI MAÇLARDAN</div>
  {''.join(_ornek_satiri(o, vurgu_iyms=m['iyms']) for o in ornekler)}"""
    return _sayfa("iyms", govde, gun)


def alti_html(m, ornekler, gun):
    govde = _mac_blogu(m) + """
    <div class="tahmin"><div class="buyuk">6+</div>
      <div class="acik"><div><span>MAÇ SONU</span><b>6 ve üzeri gol</b></div><div><span>BAHİS</span><b>5.5 Üst</b></div></div></div>
  </div>
  <div class="baslik">BENZER AÇILIŞ ORANLI MAÇLARDAN</div>
  """ + "".join(_ornek_satiri(o, vurgu_ms=True) for o in ornekler)
    return _sayfa("alti", govde, gun)


def png_yap(html_metinleri, klasor):
    """[(ad, html)] -> [png yolu]. Playwright + Chromium gerekir."""
    from playwright.sync_api import sync_playwright
    klasor = Path(klasor)
    klasor.mkdir(parents=True, exist_ok=True)
    yollar = []
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        sayfa = tarayici.new_page(viewport={"width": 1080, "height": 1350})
        for ad, metin in html_metinleri:
            h = klasor / f"{ad}.html"
            h.write_text(metin, encoding="utf-8")
            sayfa.goto(h.resolve().as_uri(), wait_until="networkidle")
            sayfa.evaluate("document.fonts.ready")
            yol = klasor / f"{ad}.png"
            sayfa.screenshot(path=str(yol))
            yollar.append(yol)
        tarayici.close()
    return yollar
