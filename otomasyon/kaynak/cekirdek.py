"""Veritabanı (data.db) erişimi ve maç çekme işlemleri."""
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import flashscore_kaynak as fk

PARALEL = 4
GUN_SINIRI = 7  # Flashscore gün akışı bugünden en fazla ±7 gün verir


class Veritabani:
    def __init__(self, yol):
        self.yol = yol
        self.kilit = threading.Lock()
        with self._baglan() as c:
            self.kolonlar = [r[1] for r in c.execute("PRAGMA table_info(MacBilgi)")]
        if not self.kolonlar:
            raise RuntimeError("MacBilgi tablosu bulunamadı.")

    def _baglan(self):
        return sqlite3.connect(self.yol, timeout=60)

    # ------------------------------------------------------------- maçlar
    def mac_sayisi(self):
        with self._baglan() as c:
            return c.execute("SELECT COUNT(*) FROM MacBilgi").fetchone()[0]

    def tarih_sinirlari(self):
        """(en eski, en yeni) maç günü; tablo boşsa (None, None)."""
        with self._baglan() as c:
            a, b = c.execute("SELECT min(date(Tarih)), max(date(Tarih)) FROM MacBilgi").fetchone()
        return (date.fromisoformat(a), date.fromisoformat(b)) if a else (None, None)

    def son_maclar(self, adet=300):
        with self._baglan() as c:
            return c.execute(f"SELECT * FROM MacBilgi ORDER BY Tarih DESC, Id DESC LIMIT {int(adet)}").fetchall()

    def tarih_araligi(self, bas, bit):
        """bas/bit: date. İki gün dahil."""
        with self._baglan() as c:
            return c.execute(
                "SELECT * FROM MacBilgi WHERE date(Tarih) BETWEEN ? AND ? ORDER BY Tarih, Id",
                (bas.isoformat(), bit.isoformat())).fetchall()

    def tarih_araligini_sil(self, bas, bit):
        with self.kilit, self._baglan() as c:
            return c.execute("DELETE FROM MacBilgi WHERE date(Tarih) BETWEEN ? AND ?",
                             (bas.isoformat(), bit.isoformat())).rowcount

    def baslamayanlari_sil(self):
        with self.kilit, self._baglan() as c:
            return c.execute("DELETE FROM MacBilgi WHERE BitmisMac = 0").rowcount

    def var_mi(self, kod, bitmis):
        with self._baglan() as c:
            r = c.execute("SELECT BitmisMac FROM MacBilgi WHERE MatchCode=?", (kod,)).fetchall()
        # Biten maç zaten kayıtlıysa tekrar çekme; başlamayan kayıt varsa güncellenir
        return any(b == 1 for (b,) in r) or (not bitmis and bool(r))

    def kaydet(self, satir):
        kol = [k for k in self.kolonlar if k != "Id" and k in satir]
        sql = f"INSERT INTO MacBilgi ({','.join(kol)}) VALUES ({','.join('?' * len(kol))})"
        with self.kilit, self._baglan() as c:
            c.execute("DELETE FROM MacBilgi WHERE MatchCode=?", (satir["MatchCode"],))
            c.execute(sql, [satir[k] for k in kol])

    # -------------------------------------------------------------- ligler
    def ligler(self):
        with self._baglan() as c:
            return c.execute("SELECT Id, Name, Link FROM League ORDER BY Name").fetchall()

    def lig_kaydet(self, ad, link, lig_id=None):
        with self.kilit, self._baglan() as c:
            if lig_id:
                c.execute("UPDATE League SET Name=?, Link=? WHERE Id=?", (ad, link, lig_id))
            else:
                c.execute("INSERT INTO League (Name, Link) VALUES (?, ?)", (ad, link))

    def lig_sil(self, idler):
        with self.kilit, self._baglan() as c:
            c.executemany("DELETE FROM League WHERE Id=?", [(i,) for i in idler])

    def tum_ligleri_sil(self):
        with self.kilit, self._baglan() as c:
            c.execute("DELETE FROM League")


class Cekici:
    """Maçları çeker. log(metin) ve ilerleme(bitti, toplam) geri çağırımları alır."""

    def __init__(self, db, log, ilerleme):
        self.db = db
        self.log = log
        self.ilerleme = ilerleme
        self.durdur = threading.Event()
        self.kaynak = fk.FlashscoreKaynak()
        self.kaydedilen = 0

    def _tek_mac(self, m, bitmis):
        if self.durdur.is_set():
            return "iptal"
        kod = m["AA"]
        if self.db.var_mi(kod, bitmis):
            return "zaten"
        bet365 = self.kaynak.oranlar(kod)
        satir = fk.oranlari_kolonlara_cevir(bet365, m.get("JA"), m.get("JB"), set(self.db.kolonlar))
        if not (satir.get("MS1_K") or satir.get("MS1_A")):
            return "oransiz"
        iy, ms = "", ""
        if bitmis:
            iy, ms = fk.skorlar(m, self.kaynak.ilk_yari_skoru(kod))
            if not ms:
                return "skorsuz"
        satir.update({
            "BitmisMac": 1 if bitmis else 0,
            "MatchCode": kod,
            "Lig": fk.lig_adi(m.get("_lig")),
            "Tarih": fk.tarih(m["AD"]),
            "Ev": m.get("AE", ""),
            "Dep": m.get("AF", ""),
            "IYSkor": iy,
            "MSSkor": ms,
        })
        self.db.kaydet(satir)
        return "kaydedildi"

    def maclari_isle(self, maclar, bitmis, baslik):
        sayac = {"kaydedildi": 0, "zaten": 0, "oransiz": 0, "skorsuz": 0, "hata": 0, "iptal": 0}
        toplam = len(maclar)
        self.log(f"{baslik}: {toplam} maç bulundu, oranlar çekiliyor...")
        bitti = 0
        with ThreadPoolExecutor(PARALEL) as ex:
            isler = [ex.submit(self._tek_mac, m, bitmis) for m in maclar]
            for f in isler:
                try:
                    sonuc = f.result()
                except Exception:  # tek maç hatası tüm işlemi durdurmasın
                    sonuc = "hata"
                sayac[sonuc] += 1
                bitti += 1
                self.ilerleme(bitti, toplam)
        self.kaydedilen += sayac["kaydedildi"]
        self.log(f"{baslik}: {sayac['kaydedildi']} maç kaydedildi"
                 + (f", {sayac['zaten']} zaten kayıtlı" if sayac["zaten"] else "")
                 + (f", {sayac['oransiz']} maçta bet365 oranı yok" if sayac["oransiz"] else "")
                 + (f", {sayac['hata']} hata" if sayac["hata"] else ""))
        return sayac

    def gunluk(self, bas, bit, bitmis):
        """bas..bit (dahil) günlerindeki maçlar. Gün, bilgisayarın saatine göre belirlenir."""
        sec = fk.mac_bitti_mi if bitmis else fk.mac_baslamadi_mi
        bugun = date.today()
        # Flashscore'un gün akışı Türkiye saatine göre bölünmüyor; bir gün öncesi/sonrası da
        # alınıp maçlar başlama saatine göre ayıklanır.
        ilk = max(-GUN_SINIRI, (bas - bugun).days - 1)
        son = min(GUN_SINIRI, (bit - bugun).days + 1)
        maclar = {}
        for fark in range(ilk, son + 1):
            if self.durdur.is_set():
                return
            self.log(f"{bugun + timedelta(days=fark):%d.%m.%Y} maç listesi alınıyor...")
            for m in self.kaynak.gunun_maclari(fark):
                if sec(m) and bas <= date.fromtimestamp(int(m["AD"])) <= bit:
                    maclar[m["AA"]] = m
        tur = "biten" if bitmis else "başlamayan"
        gunler = f"{bas:%d.%m.%Y}" if bas == bit else f"{bas:%d.%m.%Y} - {bit:%d.%m.%Y}"
        self.maclari_isle(list(maclar.values()), bitmis, f"{gunler} {tur} maçlar")

    def ligler(self, yil):
        ligler = self.db.ligler()
        if not ligler:
            self.log("Kayıtlı lig yok. AYARLAR'dan lig ekleyin.")
            return
        for sira, (_, ad, link) in enumerate(ligler, 1):
            if self.durdur.is_set():
                break
            self.log(f"[{sira}/{len(ligler)}] {ad} ({yil}-{yil + 1}) maç listesi alınıyor...")
            try:
                maclar = [m for m in self.kaynak.lig_sezon_maclari(link, yil) if fk.mac_bitti_mi(m)]
            except Exception as e:
                self.log(f"{ad}: {e}")
                continue
            self.maclari_isle(maclar, True, ad)
