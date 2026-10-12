"""Flashscore veri kaynağı.

Flashscore, oranları ziyaretçinin ülkesine göre veriyor; Türkiye (TR) için hiç oran
dönmüyor. Bu yüzden maç listesi Flashscore'un veri akışından, oranlar ise oran
servisinden Avusturya (AT) bölgesi olarak isteniyor.
"""
import re
import time
import json
from datetime import datetime

import requests

SITE = "https://www.flashscore.at"
FEED = "https://28.flashscore.ninja/28/x/feed/"
ODDS = "https://global.ds.lsapp.eu/odds/pq_graphql"
PROJECT_ID = 28
GEO = "AT"
GEO_SUB = "AT9"
FEED_SIGN = "SW9D1eZo"
BET365_ID = 16

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Normal biten maç (AC=3), uzatmalarda (10) ve penaltılarla (11) biten maçlar
BITEN_DURUMLAR = {"3", "10", "11"}


class FlashscoreKaynak:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": UA,
            "Referer": SITE + "/",
            "Origin": SITE,
            "x-fsign": FEED_SIGN,
        })

    # ------------------------------------------------------------------ http
    def _get(self, url, **kw):
        son_hata = None
        for deneme in range(4):
            try:
                r = self.s.get(url, timeout=25, **kw)
                if r.status_code == 200:
                    return r
                son_hata = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                son_hata = str(e)
            time.sleep(1.5 * (deneme + 1))
        raise RuntimeError(f"İstek başarısız ({son_hata}): {url}")

    # ------------------------------------------------------------ feed parse
    @staticmethod
    def feed_coz(metin):
        """Flashscore '¬~' kayıt / '÷' alan biçimini maç listesine çevirir."""
        maclar, lig = [], None
        for kayit in metin.split("¬~"):
            d = {}
            for alan in kayit.split("¬"):
                if "÷" in alan:
                    k, v = alan.split("÷", 1)
                    d[k] = v
            if "ZA" in d:
                lig = d["ZA"]
            if "AA" in d:
                d["_lig"] = lig
                maclar.append(d)
        return maclar

    # ------------------------------------------------------------- listeler
    def gunun_maclari(self, gun_farki):
        """gun_farki: 0 = bugün, -1 = dün, 1 = yarın (-7..+7)."""
        r = self._get(f"{FEED}f_1_{gun_farki}_3_de_1")
        return self.feed_coz(r.text)

    def lig_sezon_maclari(self, link, yil):
        """link: 'turkei/super-lig', yil: 2024 -> 2024-2025 sezonu sonuçları."""
        adaylar = [f"{SITE}/fussball/{link}-{yil}-{yil + 1}/ergebnisse/",
                   f"{SITE}/fussball/{link}-{yil}/ergebnisse/"]
        html = None
        for url in adaylar:
            try:
                r = self.s.get(url, timeout=25)
            except requests.RequestException:
                continue
            if r.status_code == 200 and "initialFeeds" in r.text:
                html = r.text
                break
        if html is None:
            raise RuntimeError(f"Lig sayfası bulunamadı: {link} {yil}")

        m = re.search(r'cjs\.initialFeeds\["summary-results"\]\s*=\s*\{\s*data:\s*`(.*?)`', html, re.S)
        maclar = self.feed_coz(m.group(1)) if m else []
        sezon = re.search(r"seasonId:\s*(\d+)", html)
        ulke = re.search(r"country_id\s*=\s*(\d+)", html)
        turnuva = re.search(r'tournament_id\s*=\s*"([^"]+)"', html)
        if sezon and ulke and turnuva:
            gorulen = {m_["AA"] for m_ in maclar}
            for sayfa in range(0, 30):
                r = self._get(f"{FEED}tr_1_{ulke.group(1)}_{turnuva.group(1)}_{sezon.group(1)}_{sayfa}_3_de_1")
                yeni = [x for x in self.feed_coz(r.text) if x["AA"] not in gorulen]
                if not yeni:
                    break
                for x in yeni:
                    gorulen.add(x["AA"])
                maclar.extend(yeni)
        return maclar

    # ------------------------------------------------------------ detaylar
    def ilk_yari_skoru(self, kod):
        r = self._get(f"{FEED}df_sui_1_{kod}")
        for kayit in r.text.split("¬~"):
            d = dict(a.split("÷", 1) for a in kayit.split("¬") if "÷" in a)
            if d.get("AC", "").startswith("1.") and "IG" in d and "IH" in d:
                return d["IG"], d["IH"]
        return None

    def oranlar(self, kod):
        r = self._get(ODDS, params={
            "_hash": "oce", "eventId": kod, "projectId": PROJECT_ID,
            "geoIpCode": GEO, "geoIpSubdivisionCode": GEO_SUB,
        })
        veri = (r.json().get("data") or {}).get("findOddsByEventId") or {}
        return [o for o in (veri.get("odds") or []) if o.get("bookmakerId") == BET365_ID]


# ---------------------------------------------------------------- dönüşüm
def _fmt(v):
    if v in (None, ""):
        return ""
    try:
        return f"{float(v):.2f}"
    except ValueError:
        return ""


def _ak(item):
    """(açılış, kapanış) -> eski programın biçimi: '3.00', '3.10'."""
    return _fmt(item.get("opening")), _fmt(item.get("value"))


def _koy(satir, on_ek, item):
    a, k = _ak(item)
    satir[on_ek + "_A"] = a
    satir[on_ek + "_K"] = k


def _sayi(s):
    return s.replace(".", "").replace("-", "")


def oranlari_kolonlara_cevir(bet365, ev_id, dep_id, kolonlar):
    """Oran servisindeki bet365 oranlarını MacBilgi kolonlarına dağıtır."""
    s = {}
    for grup in bet365:
        tip, kapsam, items = grup["bettingType"], grup["bettingScope"], grup["odds"]

        if tip == "HOME_DRAW_AWAY":
            on = {"FULL_TIME": "MS", "FIRST_HALF": "IY", "SECOND_HALF": "IIY"}.get(kapsam)
            if on:
                for it in items:
                    pid = it.get("eventParticipantId")
                    t = "1" if pid == ev_id else "2" if pid == dep_id else "0" if pid is None else None
                    if t:
                        _koy(s, on + t, it)

        elif tip == "DOUBLE_CHANCE":
            on = {"FULL_TIME": "CS", "FIRST_HALF": "IYCS"}.get(kapsam)
            if on:
                for it in items:
                    pid = it.get("eventParticipantId")
                    t = "10" if pid == ev_id else "02" if pid == dep_id else "12" if pid is None else None
                    if t:
                        _koy(s, on + t, it)

        elif tip == "BOTH_TEAMS_TO_SCORE":
            on = {"FULL_TIME": "", "FIRST_HALF": "IY_", "SECOND_HALF": "IIY_"}.get(kapsam)
            if on is not None:
                for it in items:
                    if it.get("bothTeamsToScore") is True:
                        _koy(s, on + "KGVAR", it)
                    elif it.get("bothTeamsToScore") is False:
                        _koy(s, on + "KGYOK", it)

        elif tip == "OVER_UNDER":
            on = {"FULL_TIME": "", "FIRST_HALF": "IY"}.get(kapsam)
            if on is not None:
                for it in items:
                    h = (it.get("handicap") or {}).get("value")
                    if not h or not h.endswith(".5"):
                        continue
                    yon = {"OVER": "UST", "UNDER": "ALT"}.get(it.get("selection"))
                    if yon:
                        _koy(s, f"{on}{yon}{_sayi(h)}", it)

        elif tip == "HALF_FULL_TIME" and kapsam == "FULL_TIME":
            for it in items:
                w = (it.get("winner") or "").replace("X", "0")
                if "/" in w:
                    a, b = w.split("/")
                    _koy(s, f"IYMS_{a}E{b}", it)

        elif tip == "CORRECT_SCORE":
            on = {"FULL_TIME": "Score", "FIRST_HALF": "IYScore"}.get(kapsam)
            if on:
                for it in items:
                    sk = it.get("score") or ""
                    if ":" in sk:
                        h, a = sk.split(":")
                        a_, k_ = _ak(it)
                        s[f"{on}_A{h}{a}"] = a_
                        s[f"{on}_K{h}{a}"] = k_

    return {k: v for k, v in s.items() if k in kolonlar}


def lig_adi(za):
    # "SCHOTTLAND: Premier League" -> "SCHOTTLAND Premier League" (eski biçim)
    return (za or "").replace(": ", " ", 1)


def tarih(ts):
    return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")


def mac_bitti_mi(m):
    return m.get("AB") == "3" and m.get("AC") in BITEN_DURUMLAR


def mac_baslamadi_mi(m):
    return m.get("AB") == "1" and m.get("AC") == "1"


def skorlar(m, ilk_yari):
    """(IYSkor, MSSkor). MS skoru 90 dakikanın skoru (uzatma hariç)."""
    if ilk_yari is None:
        return "", ""
    iy_e, iy_d = int(ilk_yari[0]), int(ilk_yari[1])
    if m.get("AC") == "3":
        ms_e, ms_d = int(m.get("AG", 0)), int(m.get("AH", 0))
    else:
        # uzatma/penaltı: ilk yarı + ikinci yarı (BC/BD) = 90 dk skoru
        ms_e, ms_d = iy_e + int(m.get("BC", 0)), iy_d + int(m.get("BD", 0))
    return f"{iy_e}-{iy_d}", f"{ms_e}-{ms_d}"


if __name__ == "__main__":
    k = FlashscoreKaynak()
    print(json.dumps(k.oranlar("4CsfniVT")[:1], indent=1)[:500])
