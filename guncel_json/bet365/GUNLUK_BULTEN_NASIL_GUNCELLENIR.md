# 📅 GÜNLÜK MAÇ GÜNCELLEME REHBERİ

## 🚀 Hızlı Kullanım

1. Excel dosyasını **GGGAAAYYYY.xlsx** formatında koy (örn: `20022026.xlsx`)
2. `GÜNLÜK_GÜNCELLE.bat` dosyasına **çift tıkla**
3. ✅ Site 1-2 dakikada güncellenir

---

## 📁 Excel Dosyası Adlandırma

| Tarih | Dosya Adı |
|-------|-----------|
| 20 Şubat 2026 | `20022026.xlsx` |
| 21 Şubat 2026 | `21022026.xlsx` |
| 22 Şubat 2026 | `22022026.xlsx` |

**Format: GGGAAAYYYY** → Gün(2)+Ay(2)+Yıl(4) = 8 rakam + .xlsx

---

## 🔄 Otomatik Dosya Seçim Mantığı

Script her çalıştığında:

```
1. Bugünün tarihli dosyayı ara  →  20022026.xlsx
2. Bulamazsa dünün dosyasını ara (gece geç çalıştırıldıysa)
3. Bulamazsa en güncel tarihli dosyayı kullan
```

---

## 🔄 Akış

```
20022026.xlsx  (bugünün tarihi)
      │
      ▼ excel_to_json.py
gunlukmaclar.json
      │
      ▼ git push
GitHub (camelbox27-lab/oddsy-data)
      │
      ▼ fetch
YapayZeka menüsü (raw.githubusercontent.com)
```

---

## 📊 Excel Sütun Formatı

| Sütun | Açıklama |
|-------|----------|
| **Id** | Maç ID (benzersiz) |
| **Ev** | Ev sahibi takım |
| **Dep** | Deplasman takım |
| **MS1 A** | Açılış oran - 1 |
| **MS0 A** | Açılış oran - 0 |
| **MS2 A** | Açılış oran - 2 |
| **MS1 K** | Kapanış oran - 1 |
| **MS0 K** | Kapanış oran - 0 |
| **MS2 K** | Kapanış oran - 2 |
| **Maç Sonucu Skor** | Örn: `2-1` |
| **İlk Yarı Skor** | Örn: `1-0` |

---

## 🔧 Sorun Giderme

```bash
# Python yoksa
winget install Python.Python.3.12

# Pandas yoksa
pip install pandas openpyxl

# Git push çalışmıyorsa
cd C:\Users\AyberkEylülKemal\Desktop\TahminApp\oddsy-data
git add . && git commit -m "guncelleme" && git push origin main
```
