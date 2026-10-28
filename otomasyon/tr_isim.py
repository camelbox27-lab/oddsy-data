# -*- coding: utf-8 -*-
"""Almanca gelen lig/takim isimlerini Turkce gosterime cevirir.

NEDEN: Veri kaynagi Flashscore'un Almanca (AT) surumu. Oranlar ve mac
kodlari bu surume bagli oldugu icin kaynak DEGISTIRILMIYOR; isimler
yalnizca gosterim asamasinda cevriliyor. Bu modul veriyi degistirmez,
sadece Telegram mesaji uretilirken cagrilir -> site ve PC etkilenmez.

Lig adi bicimi: "<ULKE> <Turnuva>"  (or. "TSCHECHIEN MOL Cup")
"""
import re

# ---- Ulke: Almanca -> (Turkce, bayrak) ------------------------------------
ULKELER = {
    "ÄGYPTEN": ("Mısır", "🇪🇬"), "ALBANIEN": ("Arnavutluk", "🇦🇱"),
    "ALGERIEN": ("Cezayir", "🇩🇿"), "ANDORRA": ("Andorra", "🇦🇩"),
    "ANGOLA": ("Angola", "🇦🇴"), "ARGENTINIEN": ("Arjantin", "🇦🇷"),
    "ARMENIEN": ("Ermenistan", "🇦🇲"), "ASERBAIDSCHAN": ("Azerbaycan", "🇦🇿"),
    "ÄTHIOPIEN": ("Etiyopya", "🇪🇹"), "AUSTRALIEN": ("Avustralya", "🇦🇺"),
    "BAHRAIN": ("Bahreyn", "🇧🇭"), "BANGLADESCH": ("Bangladeş", "🇧🇩"),
    "BELARUS": ("Belarus", "🇧🇾"), "BELGIEN": ("Belçika", "🇧🇪"),
    "BOLIVIEN": ("Bolivya", "🇧🇴"), "BOSNIEN UND HERZEGOWINA": ("Bosna-Hersek", "🇧🇦"),
    "BOTSWANA": ("Botsvana", "🇧🇼"), "BRASILIEN": ("Brezilya", "🇧🇷"),
    "BULGARIEN": ("Bulgaristan", "🇧🇬"), "BURKINA FASO": ("Burkina Faso", "🇧🇫"),
    "BURUNDI": ("Burundi", "🇧🇮"), "CHILE": ("Şili", "🇨🇱"),
    "CHINA": ("Çin", "🇨🇳"), "COSTA RICA": ("Kosta Rika", "🇨🇷"),
    "DÄNEMARK": ("Danimarka", "🇩🇰"), "DEUTSCHLAND": ("Almanya", "🇩🇪"),
    "DOMINIKANISCHE REPUBLIK": ("Dominik Cumhuriyeti", "🇩🇴"),
    "ECUADOR": ("Ekvador", "🇪🇨"), "EL SALVADOR": ("El Salvador", "🇸🇻"),
    "ELFENBEINKÜSTE": ("Fildişi Sahili", "🇨🇮"), "ENGLAND": ("İngiltere", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    "ESTLAND": ("Estonya", "🇪🇪"), "FÄRÖER": ("Faroe Adaları", "🇫🇴"),
    "FINNLAND": ("Finlandiya", "🇫🇮"), "FRANKREICH": ("Fransa", "🇫🇷"),
    "GABUN": ("Gabon", "🇬🇦"), "GAMBIA": ("Gambiya", "🇬🇲"),
    "GEORGIEN": ("Gürcistan", "🇬🇪"), "GHANA": ("Gana", "🇬🇭"),
    "GIBRALTAR": ("Cebelitarık", "🇬🇮"), "GRIECHENLAND": ("Yunanistan", "🇬🇷"),
    "GUATEMALA": ("Guatemala", "🇬🇹"), "HONDURAS": ("Honduras", "🇭🇳"),
    "HONGKONG": ("Hong Kong", "🇭🇰"), "INDIEN": ("Hindistan", "🇮🇳"),
    "INDONESIEN": ("Endonezya", "🇮🇩"), "IRAK": ("Irak", "🇮🇶"),
    "IRAN": ("İran", "🇮🇷"), "IRLAND": ("İrlanda", "🇮🇪"),
    "ISLAND": ("İzlanda", "🇮🇸"), "ISRAEL": ("İsrail", "🇮🇱"),
    "ITALIEN": ("İtalya", "🇮🇹"), "JAMAIKA": ("Jamaika", "🇯🇲"),
    "JAPAN": ("Japonya", "🇯🇵"), "JEMEN": ("Yemen", "🇾🇪"),
    "JORDANIEN": ("Ürdün", "🇯🇴"), "KAMBODSCHA": ("Kamboçya", "🇰🇭"),
    "KAMERUN": ("Kamerun", "🇨🇲"), "KANADA": ("Kanada", "🇨🇦"),
    "KASACHSTAN": ("Kazakistan", "🇰🇿"), "KATAR": ("Katar", "🇶🇦"),
    "KENIA": ("Kenya", "🇰🇪"), "KIRGISISTAN": ("Kırgızistan", "🇰🇬"),
    "KOLUMBIEN": ("Kolombiya", "🇨🇴"), "KONGO": ("Kongo", "🇨🇬"),
    "KOSOVO": ("Kosova", "🇽🇰"), "KROATIEN": ("Hırvatistan", "🇭🇷"),
    "KUWAIT": ("Kuveyt", "🇰🇼"), "LETTLAND": ("Letonya", "🇱🇻"),
    "LIBANON": ("Lübnan", "🇱🇧"), "LIBYEN": ("Libya", "🇱🇾"),
    "LIECHTENSTEIN": ("Lihtenştayn", "🇱🇮"), "LITAUEN": ("Litvanya", "🇱🇹"),
    "LUXEMBURG": ("Lüksemburg", "🇱🇺"), "MALAYSIA": ("Malezya", "🇲🇾"),
    "MALTA": ("Malta", "🇲🇹"), "MAROKKO": ("Fas", "🇲🇦"),
    "MAZEDONIEN": ("Makedonya", "🇲🇰"), "NORDMAZEDONIEN": ("Kuzey Makedonya", "🇲🇰"),
    "MEXIKO": ("Meksika", "🇲🇽"), "MOLDAWIEN": ("Moldova", "🇲🇩"),
    "MONGOLEI": ("Moğolistan", "🇲🇳"), "MONTENEGRO": ("Karadağ", "🇲🇪"),
    "MYANMAR": ("Myanmar", "🇲🇲"), "NEUSEELAND": ("Yeni Zelanda", "🇳🇿"),
    "NICARAGUA": ("Nikaragua", "🇳🇮"), "NIEDERLANDE": ("Hollanda", "🇳🇱"),
    "NIGERIA": ("Nijerya", "🇳🇬"), "NORDIRLAND": ("Kuzey İrlanda", "🏴"),
    "NORWEGEN": ("Norveç", "🇳🇴"), "OMAN": ("Umman", "🇴🇲"),
    "ÖSTERREICH": ("Avusturya", "🇦🇹"), "PAKISTAN": ("Pakistan", "🇵🇰"),
    "PALÄSTINA": ("Filistin", "🇵🇸"), "PANAMA": ("Panama", "🇵🇦"),
    "PARAGUAY": ("Paraguay", "🇵🇾"), "PERU": ("Peru", "🇵🇪"),
    "PHILIPPINEN": ("Filipinler", "🇵🇭"), "POLEN": ("Polonya", "🇵🇱"),
    "PORTUGAL": ("Portekiz", "🇵🇹"), "PUERTO RICO": ("Porto Riko", "🇵🇷"),
    "RUMÄNIEN": ("Romanya", "🇷🇴"), "RUSSLAND": ("Rusya", "🇷🇺"),
    "SAUDI-ARABIEN": ("Suudi Arabistan", "🇸🇦"), "SCHOTTLAND": ("İskoçya", "🏴󠁧󠁢󠁳󠁣󠁴󠁿"),
    "SCHWEDEN": ("İsveç", "🇸🇪"), "SCHWEIZ": ("İsviçre", "🇨🇭"),
    "SENEGAL": ("Senegal", "🇸🇳"), "SERBIEN": ("Sırbistan", "🇷🇸"),
    "SIMBABWE": ("Zimbabve", "🇿🇼"), "SINGAPUR": ("Singapur", "🇸🇬"),
    "SLOWAKEI": ("Slovakya", "🇸🇰"), "SLOWENIEN": ("Slovenya", "🇸🇮"),
    "SPANIEN": ("İspanya", "🇪🇸"), "SRI LANKA": ("Sri Lanka", "🇱🇰"),
    "SÜDAFRIKA": ("Güney Afrika", "🇿🇦"), "SÜDKOREA": ("Güney Kore", "🇰🇷"),
    "SUDAN": ("Sudan", "🇸🇩"), "SYRIEN": ("Suriye", "🇸🇾"),
    "TADSCHIKISTAN": ("Tacikistan", "🇹🇯"), "TAIWAN": ("Tayvan", "🇹🇼"),
    "TANSANIA": ("Tanzanya", "🇹🇿"), "THAILAND": ("Tayland", "🇹🇭"),
    "TSCHECHIEN": ("Çekya", "🇨🇿"), "TUNESIEN": ("Tunus", "🇹🇳"),
    "TÜRKEI": ("Türkiye", "🇹🇷"), "TURKMENISTAN": ("Türkmenistan", "🇹🇲"),
    "UGANDA": ("Uganda", "🇺🇬"), "UKRAINE": ("Ukrayna", "🇺🇦"),
    "UNGARN": ("Macaristan", "🇭🇺"), "URUGUAY": ("Uruguay", "🇺🇾"),
    "USA": ("ABD", "🇺🇸"), "USBEKISTAN": ("Özbekistan", "🇺🇿"),
    "VENEZUELA": ("Venezuela", "🇻🇪"),
    "VEREINIGTE ARABISCHE EMIRATE": ("BAE", "🇦🇪"),
    "VIETNAM": ("Vietnam", "🇻🇳"), "WALES": ("Galler", "🏴󠁧󠁢󠁷󠁬󠁳󠁿"),
    "ZYPERN": ("Kıbrıs", "🇨🇾"),
    # Kita / genel
    "EUROPA": ("Avrupa", "🇪🇺"), "SÜDAMERIKA": ("Güney Amerika", "🌎"),
    "NORD- & MITTELAMERIKA": ("Kuzey ve Orta Amerika", "🌎"),
    "AFRIKA": ("Afrika", "🌍"), "ASIEN": ("Asya", "🌏"),
    "OZEANIEN": ("Okyanusya", "🌏"), "WELT": ("Dünya", "🌐"),
}

# Uzun adlar once denensin (or. "BOSNIEN UND HERZEGOWINA")
_ULKE_SIRALI = sorted(ULKELER, key=len, reverse=True)

# ---- Turnuva adindaki Almanca kelimeler ------------------------------------
TURNUVA_KELIME = [
    ("Qualifikation", "Eleme"),
    ("Ligaphase", "Lig Aşaması"),
    ("Gruppenphase", "Grup Aşaması"),
    ("Meisterschaft", "Şampiyonası"),
    ("Meisterrunde", "Şampiyonluk Grubu"),
    ("Abstiegsrunde", "Küme Düşme Grubu"),
    ("Aufstiegsrunde", "Yükselme Grubu"),
    ("Playoffs", "Play-off"),
    ("Play-offs", "Play-off"),
    ("Frauen", "Kadınlar"),
    ("Herren", "Erkekler"),
    ("Jugend", "Gençler"),
    ("Achtelfinale", "Son 16"),
    ("Viertelfinale", "Çeyrek Final"),
    ("Halbfinale", "Yarı Final"),
    ("Finale", "Final"),
    ("Vorrunde", "Ön Eleme"),
    ("Relegation", "Baraj"),
    ("Super Liga", "Süper Lig"),
    ("Superliga", "Süper Lig"),
]

# ---- Almanca takim adi kaliplari (sadece net olanlar) ----------------------
TAKIM_KELIME = {
    "Mailand": "Milano", "Rom": "Roma", "Neapel": "Napoli", "Turin": "Torino",
    "Genua": "Cenova", "Florenz": "Floransa", "Venedig": "Venedik",
    "Lissabon": "Lizbon", "Kopenhagen": "Kopenhag", "Moskau": "Moskova",
    "Bukarest": "Bükreş", "Athen": "Atina", "Warschau": "Varşova",
    "Wien": "Viyana", "München": "Münih", "Nizza": "Nice",
    "Teneriffa": "Tenerife", "Saragossa": "Zaragoza", "Mailands": "Milano",
    "Belgrad": "Belgrad", "Brüssel": "Brüksel", "Lüttich": "Liege",
    "Antwerpen": "Antwerp", "Göteborg": "Göteborg", "Kiew": "Kiev",
    "Krakau": "Krakov", "Breslau": "Wroclaw", "Danzig": "Gdansk",
    "Mailand.": "Milano",
}
_TAKIM_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, TAKIM_KELIME), key=len, reverse=True)) + r")\b"
)

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]


def lig(ad):
    """'TSCHECHIEN MOL Cup' -> ('🇨🇿', 'Çekya · MOL Cup')"""
    ad = (ad or "").strip()
    if not ad:
        return "", ""

    ulke_tr, bayrak, turnuva = "", "", ad
    for alm in _ULKE_SIRALI:
        if ad == alm:
            ulke_tr, bayrak = ULKELER[alm]
            turnuva = ""
            break
        if ad.startswith(alm + " "):
            ulke_tr, bayrak = ULKELER[alm]
            turnuva = ad[len(alm) + 1:].strip()
            break

    # "Pokal Türkei" -> "Türkiye Kupası"  (ulke adi tasiyan kupalar)
    m = re.match(r"^Pokal\s+(.+)$", turnuva)
    if m:
        kalan = m.group(1).strip()
        for alm in _ULKE_SIRALI:
            if kalan == alm.title() or kalan.upper() == alm:
                turnuva = ULKELER[alm][0] + " Kupası"
                break
            if kalan.upper().startswith(alm + " - "):
                turnuva = ULKELER[alm][0] + " Kupası" + kalan[len(alm):]
                break
        else:
            turnuva = kalan + " Kupası"

    for alm, tr in TURNUVA_KELIME:
        turnuva = re.sub(r"\b" + re.escape(alm) + r"\b", tr, turnuva)

    turnuva = re.sub(r"\s*-\s*", " – ", turnuva).strip(" –")

    if not turnuva:
        return bayrak, ulke_tr
    if not ulke_tr:
        return "", turnuva
    # Turnuva adi zaten ulkeyi soyluyorsa tekrar etme
    if ulke_tr.lower() in turnuva.lower():
        return bayrak, turnuva
    return bayrak, f"{ulke_tr} · {turnuva}"


def takim(ad):
    """Almanca sehir adlarini duzeltir; taninmayan adi oldugu gibi birakir."""
    ad = (ad or "").strip()
    if not ad:
        return ad
    return _TAKIM_RE.sub(lambda m: TAKIM_KELIME[m.group(1)], ad)


def tarih(gg_aa_yyyy):
    """'28.10.2026' -> '28 Ekim 2026 Çarşamba'"""
    try:
        import datetime as dt
        g = dt.datetime.strptime(gg_aa_yyyy, "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return gg_aa_yyyy
    return f"{g.day} {AYLAR[g.month - 1]} {g.year} {GUNLER[g.weekday()]}"
