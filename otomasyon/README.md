# Otomasyon — telefondan tek dokunusla veri guncelleme

Masaustu programlarini (IddaaPro / Bet365Pro) elle acip Excel'i buraya kopyalamak
yerine, telefondaki iki butonla ayni isi sunucuda yapar.

```
Telefon (tetikle/index.html)
      │  GitHub API: workflow_dispatch
      ▼
GitHub Actions  (.github/workflows/veri-guncelle.yml)
      │  iddaa_cek.py / bet365_cek.py   → Excel
      │  excel_to_json_ci.py            → JSON
      ▼
main dalina commit + push  →  site raw.githubusercontent'ten okur
```

## Uretilen dosyalar

| Buton | Excel | JSON |
|---|---|---|
| **İDDAA** | `iddaa/gunluk/gunlukmaclar.xlsx` | `iddaa/gunluk/gunlukmaclar.json` |
| **BET365** | `bet365/GGAAYYYY.xlsx` (orn. `13102026.xlsx`) | `bet365/GGAAYYYY.json` + `bet365/gunlukmaclar.json` |

Isimlendirme ve JSON bicimi, elle kullanilan `excel_to_json.py` scriptlerinin
uretttigi ile ayni tutulmustur; site tarafinda hicbir degisiklik gerekmez.
`bet365/gunlukmaclar.json` her zaman **en guncel tarihli** gunun kopyasidir.

## Ilk kurulum (bir kere)

**1) Bu dal main'e birlestirilmeli.**
`workflow_dispatch` ancak akis dosyasi varsayilan dalda (main) oldugunda
calisir. Birlestirmeden butonlar "Akis bulunamadi" hatasi verir.

**2) GitHub erisim anahtari (token) olustur**
[Fine-grained token olustur](https://github.com/settings/personal-access-tokens/new):

- Repository access → **Only select repositories** → `oddsy-data`
- Permissions → Repository permissions → **Actions: Read and write**
- Baska hicbir izin gerekmez.

**3) Sayfayi yayina al**
Settings → Pages → Source: `Deploy from a branch`, Branch: `main` / `(root)`.
Sayfa adresi: `https://camelbox27-lab.github.io/oddsy-data/tetikle/`

**4) Telefona ekle (Android)**
Chrome'da yukaridaki adresi ac → ⋮ menu → **Ana ekrana ekle**.
Uygulama gibi tam ekran acilir. Ilk acilista token'i bir kez gir ve kaydet —
tarayicida (localStorage) saklanir, hicbir yere gonderilmez.

## Kullanim

Butona bas, sayfa calismanin durumunu kendisi izler ve bitince sonucu gosterir.
Cekme suresi mac sayisina gore degisir, tipik olarak birkac dakika. Sayfayi
kapatsan da calisma sunucuda devam eder.

## Dosyalar

| Dosya | Isi |
|---|---|
| `iddaa_cek.py` | Mackolik'ten gunluk bulteni ceker, Excel yazar |
| `bet365_cek.py` | Flashscore'dan bugunun baslamayan maclarini ceker, Excel yazar |
| `excel_to_json_ci.py` | Excel → JSON (etkilesimsiz, git islemi yapmaz) |
| `tkinter_stub.py` | `iddaapro.py` sunucuda Tk olmadan import edilebilsin diye |
| `kaynak/` | Masaustu programlarindan **kopyalanan** cekme kodu |

## kaynak/ klasoru hakkinda

`kaynak/` icindekiler `camelbox27-lab/mac-programlar` reposundan kopyalandi:

| Dosya | Kaynak |
|---|---|
| `iddaapro.py`, `mac_uyum.py` | `iddaapro/` |
| `cekirdek.py`, `flashscore_kaynak.py`, `excel_aktar.py`, `data.db`, `hazir_ligler.json` | `bet365pro/` |

Dosyalar **hic degistirilmedi** — boylece masaustu surumu guncellendiginde
uzerine kopyalamak yeterli olur, iki ayri surum bakmak gerekmez:

```bash
cp ../mac-programlar/iddaapro/{iddaapro.py,mac_uyum.py} kaynak/
cp ../mac-programlar/bet365pro/{cekirdek.py,flashscore_kaynak.py,excel_aktar.py} kaynak/
```

`data.db` bos bir sablondur (227 kolonluk `MacBilgi` tablosu + 69 lig). Her
calisma bunun gecici bir kopyasindan baslar, yani cikti her zaman tek gunluk
temiz veridir ve sablon hic degismez.

## Notlar

- **Saat dilimi:** akis `TZ=Europe/Istanbul` ile calisir. Olmazsa runner UTC
  oldugu icin gece yarisi sonrasi dosya adi bir gun geri kayar.
- **Bos veri korumasi:** hic mac cekilemezse dosya yazilmaz ve adim hata verir;
  site bos bultenle ezilmez.
- **`ikisi` secildiginde** biri basarisiz olsa bile digerinin verisi push edilir.
- **Paket surumleri sabit** (`requirements.txt`): bet365 JSON'u pandas'in
  `to_json` bicimine bagli; mevcut JSON'larla byte duzeyinde ayni kalmasi icin.
