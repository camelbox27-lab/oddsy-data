"""Wondiyo Tahmin (Oto-BOT) icin lig filtresi.

Canli tarama ve mac oncesi tercihler (kupon dahil) yalnizca bu liglerdeki
maclari kullanir: majör ligler ve alt ligleri. Kadin, altyapi (U17-U23)
ve rezerv (B / II) takimlari hic alinmaz.
"""

# Yalnizca bu ligler alinir. Anahtar Flashscore'un (Almanca)
# ulke adi, deger lig adinin basi. Buyuk 5 + Turkiye: ilk 3 kademe (Ingiltere
# 4); diger Avrupa: ilk 2 kademe; Avrupa kupalari; birkac buyuk Amerika ligi.
LIGLER = {
    "ENGLAND":      ["Premier League", "Championship", "League One", "League Two",
                     "FA Cup", "EFL Cup"],
    "SPANIEN":      ["La Liga", "Primera RFEF", "Copa del Rey"],
    "ITALIEN":      ["Serie A", "Serie B", "Serie C", "Coppa Italia -"],
    "DEUTSCHLAND":  ["Bundesliga", "2. Bundesliga", "3. Liga", "DFB Pokal"],
    "FRANKREICH":   ["Ligue 1", "Ligue 2", "National", "Coupe de France"],
    "TÜRKEI":       ["Süper Lig", "1. Lig", "2. Lig", "Pokal"],
    "NIEDERLANDE":  ["Eredivisie", "Eerste Divisie", "KNVB Beker"],
    "PORTUGAL":     ["Liga Portugal", "Taça de Portugal"],
    "BELGIEN":      ["Jupiler League", "Challenger Pro League", "Beker"],
    "SCHOTTLAND":   ["Premier League", "Championship", "League Cup", "FA Cup"],
    "ÖSTERREICH":   ["Bundesliga", "2. Liga", "ÖFB Cup"],
    "SCHWEIZ":      ["Super League", "Challenge League"],
    "DÄNEMARK":     ["Superliga", "1. Division"],
    "SCHWEDEN":     ["Allsvenskan", "Superettan"],
    "NORWEGEN":     ["Eliteserien", "OBOS-ligaen"],
    "GRIECHENLAND": ["Super League"],
    "TSCHECHIEN":   ["1. Liga", "Division 2"],
    "POLEN":        ["Ekstraklasa", "I liga"],
    "KROATIEN":     ["HNL", "Prva NL"],
    "EUROPA":       ["Champions League", "Europa League", "Conference League"],
    "BRASILIEN":    ["Série A", "Série B", "Copa do Brasil"],
    "ARGENTINIEN":  ["Liga Profesional"],
    "USA":          ["MLS"],
}
_DISLA_LIG = ("frauen", "women", "wsl", "damen", "femen", "u17", "u18", "u19",
              "u20", "u21", "u23", "jugend", "youth", "primavera", "reserve",
              "freundschaft", "friendly")
_DISLA_TAKIM_SON = (" F", " B", " II", " U19", " U20", " U21", " U23")


def lig_uygun(lig, ev="", dep=""):
    """Mac alinir mi? (majör lig / alt lig, yetiskin erkek takimlari)"""
    lig = (lig or "").strip()
    kucuk = lig.lower()
    if any(k in kucuk for k in _DISLA_LIG):
        return False
    for takim in (ev or "", dep or ""):
        if takim.strip().endswith(_DISLA_TAKIM_SON):
            return False
    for ulke, ligler in LIGLER.items():
        if lig.startswith(ulke + " "):
            yarisma = lig[len(ulke) + 1:]
            return any(yarisma.startswith(l) for l in ligler)
    return False
