import pandas as pd
import json
import os

# Excel dosyasının yolu
excel_file = "gunlukmaclar.xlsx"

# Excel dosyasını oku
df = pd.read_excel(excel_file)

# JSON dosya adını oluştur (aynı isimle .json uzantılı)
json_file = os.path.splitext(excel_file)[0] + ".json"

# DataFrame'i JSON'a çevir
json_data = df.to_json(orient='records', force_ascii=False, indent=2)

# JSON dosyasını kaydet
with open(json_file, 'w', encoding='utf-8') as f:
    f.write(json_data)

print(f"✓ {excel_file} başarıyla {json_file} olarak kaydedildi!")
