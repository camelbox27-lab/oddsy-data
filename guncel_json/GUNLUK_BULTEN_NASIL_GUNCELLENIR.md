# 📅 GÜNLÜK BÜLTEN GÜNCELLEME REHBERİ

## Her Gün Yapılacaklar:

### 1️⃣ **Excel Dosyasını Güncelle**
- `gunlukmaclar.xlsx` dosyasını aç
- Günün maçlarını ekle/güncelle
- Kaydet ve kapat

### 2️⃣ **JSON'a Dönüştür**
Terminal'de şu komutu çalıştır:

```bash
cd public/guncel_json
python excel_to_json.py
```

### 3️⃣ **Kontrol Et**
- `gunlukmaclar.json` dosyasının güncellendiğini kontrol et
- Dosya boyutunun değiştiğini gör

### 4️⃣ **Site Otomatik Güncellenir**
- Siteyi yenile (F5)
- Yeni maçlar otomatik gelecek

---

## ⚠️ ÖNEMLİ NOTLAR:

- **Excel dosya adı değişmemeli:** `gunlukmaclar.xlsx`
- **JSON dosya adı değişmemeli:** `gunlukmaclar.json`
- **Script her zaman aynı klasörde olmalı:** `public/guncel_json/`

---

## 🔧 Script Çalışmazsa:

### Python yüklü değilse:
```bash
# Python yükle (Windows)
winget install Python.Python.3.12
```

### Pandas yüklü değilse:
```bash
pip install pandas openpyxl
```

---

## 📊 Excel Formatı:

Excel'de şu sütunlar olmalı:
- **Ev** (Ev sahibi takım)
- **Dep** (Deplasman takım)
- **MS1 A** (Açılış oran 1)
- **MS0 A** (Açılış oran 0)
- **MS2 A** (Açılış oran 2)
- **MS1 K** (Kapanış oran 1)
- **MS0 K** (Kapanış oran 0)
- **MS2 K** (Kapanış oran 2)

---

## ✅ Başarılı Güncelleme Mesajı:

```
✓ gunlukmaclar.xlsx başarıyla gunlukmaclar.json olarak kaydedildi!
```

Bu mesajı görürsen her şey tamam! 🎉
