"""Oto-BOT surpriz kartlari (Telegram'a gorsel olarak gider).

Her surpriz mac icin 1080x1100 bir kart: mac, tahmin ve ayni acilis
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
# Sitenin acik tema logosu: yesil W, beyaz zemin
LOGO = """<svg viewBox="0 0 192 192" xmlns="http://www.w3.org/2000/svg"><defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2FA857"/>
<stop offset="1" stop-color="#146B34"/></linearGradient></defs>
<path d="M34 58 L62 134 L96 78 L130 134 L158 58" fill="none" stroke="url(#g)" stroke-width="16"
stroke-linecap="round" stroke-linejoin="round"/></svg>"""

TEMA = {  # tur -> etiket (renkler sitenin acik temasi: yesil + limon)
    "iyms": "İY/MS SÜRPRİZİ",
    "alti": "GOL SÜRPRİZİ",
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


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--y:#1E8A45;--ya:#2FA857;--yk:#146B34;--l:#C8D92E;--lt:#6B7D0F;--zemin:#F4F6F2;--kart:#FFFFFF;
 --gom:#EAEEE6;--yazi:#16261B;--ikinci:#4A5B4F;--soluk:#77857A;--kenar:#DCE3D6}
body{width:1080px;height:1100px;background:var(--zemin);font-family:Inter,sans-serif;color:var(--yazi);overflow:hidden;position:relative}
.bant{position:absolute;left:0;right:0;top:0;height:300px;background:linear-gradient(180deg,#D8E33F 0%,#A9CF43 55%,#8DC44A 100%)}
.bant::after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(135deg,rgba(255,255,255,.12) 0 2px,transparent 2px 24px)}
.ic{position:relative;height:100%;padding:58px 70px 0;display:flex;flex-direction:column}
.tepe{display:flex;align-items:center;justify-content:space-between}
.marka{display:flex;align-items:center;gap:16px}
.marka svg{width:66px;height:66px;background:#fff;border-radius:18px;padding:7px;box-shadow:0 4px 14px rgba(22,38,27,.12)}
.marka span{font-family:Outfit,Inter,sans-serif;font-weight:900;font-size:38px;letter-spacing:3px;color:var(--yk)}
.etiket{font-size:19px;font-weight:800;letter-spacing:2.2px;padding:12px 22px;border-radius:99px;color:#fff;background:var(--yk)}
.mac{margin-top:40px;padding:34px 38px 30px;border-radius:32px;background:var(--kart);border:2px solid var(--kenar);box-shadow:0 10px 30px rgba(22,38,27,.12)}
.ust{display:flex;justify-content:space-between;align-items:center;font-size:21px;font-weight:700;color:var(--soluk)}
.saat{font-size:24px;font-weight:800;color:#fff;background:var(--y);border-radius:14px;padding:8px 16px}
.govde{display:flex;align-items:center;gap:26px;margin-top:18px}
.takimlar{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.takimlar b{font-size:48px;line-height:1.14;font-weight:900;letter-spacing:-1px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.takimlar i{font-style:normal;font-size:18px;font-weight:800;color:var(--soluk);letter-spacing:4px;margin:2px 0 2px 3px}
.tahmin{flex:0 0 auto;min-width:250px;border-radius:28px;padding:20px 24px 18px;text-align:center;background:linear-gradient(160deg,var(--ya),var(--yk));color:#fff;box-shadow:0 10px 26px rgba(30,138,69,.35)}
.tahmin b{display:block;font-family:Outfit,Inter,sans-serif;font-weight:900;font-size:110px;line-height:1;letter-spacing:-2px}
.tahmin span{display:block;margin-top:6px;font-size:17px;font-weight:800;letter-spacing:2.4px;color:#E7F3D0}
.baslik{margin:34px 0 14px;font-size:19px;font-weight:800;letter-spacing:3px;color:var(--y);display:flex;align-items:center;gap:14px}
.baslik::after{content:"";flex:1;height:2px;background:linear-gradient(90deg,var(--kenar),transparent)}
.satir{display:flex;align-items:center;gap:18px;padding:14px 22px;border-radius:20px;background:var(--kart);border:2px solid var(--kenar);margin-bottom:11px}
.satir .t{width:150px;display:flex;flex-direction:column}
.satir .t b{font-size:20px;font-weight:800}
.satir .t span{font-size:15px;font-weight:700;color:var(--soluk);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.satir .k{flex:1;min-width:0;font-size:24px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.satir .s{display:flex;gap:8px;align-items:center}
.sk{min-width:76px;text-align:center;font-size:22px;font-weight:800;border-radius:12px;padding:7px 10px;background:var(--gom);color:var(--ikinci)}
.sk small{display:block;font-size:12px;letter-spacing:1.5px;color:var(--soluk);font-weight:800}
.vurgu{background:var(--y);color:#fff}
.vurgu small{color:#CFE8D6}
.satir.tutan{border-color:var(--yk);background:linear-gradient(110deg,var(--ya),var(--yk));color:#fff;box-shadow:0 8px 20px rgba(30,138,69,.28)}
.satir.tutan .t span{color:#D9EFD9}
.satir.tutan .sk{background:rgba(255,255,255,.18);color:#fff}
.satir.tutan .sk small{color:#D9EFD9}
.satir.tutan .vurgu{background:#fff;color:var(--yk)}
.satir.tutan .vurgu small{color:var(--y)}
.tik{flex:0 0 auto;width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;font-weight:900;background:#fff;color:var(--y)}
.bos{flex:0 0 auto;width:34px;height:34px}
.dip{position:absolute;left:70px;right:70px;bottom:34px;display:flex;justify-content:space-between;font-size:17px;font-weight:700;color:var(--soluk);letter-spacing:1.2px}
.dip b{color:var(--y)}
"""


def _sayfa(tur, govde, gun):
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&family=Outfit:wght@700;900&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<div class="bant"></div>
<div class="ic">
  <div class="tepe"><div class="marka">{LOGO}<span>WONDİYO</span></div><div class="etiket">{TEMA[tur]}</div></div>
  {govde}
</div>
<div class="dip"><span><b>wondiyo.com.tr</b> · {_e(tr_isim.tarih(gun))}</span><span>18+ · Bilgi amaçlıdır</span></div>
</body></html>"""


def _mac_blogu(m, buyuk, alt):
    bayrak, lig = tr_isim.lig(m.get("lig", ""))
    return f"""<div class="mac">
    <div class="ust"><span>{_e(lig)}</span><span class="saat">{_e(m['saat'])}</span></div>
    <div class="govde">
      <div class="takimlar"><b>{_e(tr_isim.takim(m['ev']))}</b><i>VS</i><b>{_e(tr_isim.takim(m['dep']))}</b></div>
      <div class="tahmin"><b>{_e(buyuk)}</b><span>{_e(alt)}</span></div>
    </div>
  </div>"""


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
    tutan = (vurgu_iyms is not None and o["iyms"] == vurgu_iyms) or bool(ms_v)
    isaret = '<span class="tik">✓</span>' if tutan else '<span class="bos"></span>'
    return f"""<div class="satir{' tutan' if tutan else ''}">{isaret}<div class="t"><b>{_tarih(o['tarih'])}</b><span>{_e(_lig_gecmis(o['lig']))}</span></div>
      <div class="k">{_e(o['ev'])} – {_e(o['dep'])}</div>
      <div class="s">{iy_k}<div class="sk{ms_v}"><small>MS</small>{ms_y}</div>{son}</div></div>"""


def iyms_html(m, ornekler, gun):
    govde = _mac_blogu(m, m["iyms"], "İY / MS") + f"""
  <div class="baslik">BENZER AÇILIŞ ORANLI MAÇLARDAN</div>
  {''.join(_ornek_satiri(o, vurgu_iyms=m['iyms']) for o in ornekler)}"""
    return _sayfa("iyms", govde, gun)


def alti_html(m, ornekler, gun):
    govde = _mac_blogu(m, "6+", "GOL") + """
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
        try:
            # GitHub'in ubuntu sunucularinda Google Chrome kurulu geliyor
            tarayici = p.chromium.launch(channel="chrome")
        except Exception:
            tarayici = p.chromium.launch()
        sayfa = tarayici.new_page(viewport={"width": 1080, "height": 1100})
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
