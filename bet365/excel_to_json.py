"""
=================================================
  ODDSY - Haftalık Toplu Dönüşüm Scripti
  TÜM DDMMYYYY.xlsx -> DDMMYYYY.json + GitHub Push
=================================================

KULLANIM:
  1. Bu klasöre TÜM haftanın Excel'lerini koy:
       20022026.xlsx
       21022026.xlsx
       22022026.xlsx  ... vb.
  2. CALISTIR.bat'a çift tıkla  VEYA  cmd'de: python excel_to_json.py
  3. Site her gün otomatik o günün verisini gösterir

GITHUB REPO: camelbox27-lab/oddsy-data
Site URL   : https://raw.githubusercontent.com/camelbox27-lab/oddsy-data/main/bet365/gunlukmaclar.json
"""

import os
import sys
import json
import subprocess
import shutil
from datetime import datetime

# ── Pandas kontrolü ve otomatik kurulum ───────────────────────────────────────
try:
    import pandas as pd
except ImportError:
    print("[!] Pandas bulunamadi, kuruluyor...")
    subprocess.run([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"], check=True)
    import pandas as pd

# ── Renk sabitleri ────────────────────────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def baris(char="=", n=58):
    print(char * n)

# ── Script dizinine geç ───────────────────────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

baris()
print(f"{BOLD}{CYAN}  ODDSY - HAFTALIK TOPLU GÜNCELLEME{RESET}")
print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}")
baris()

# ── DDMMYYYY.xlsx dosyalarını bul ve sırala ───────────────────────────────────
excel_dosyalari = []
for f in os.listdir(script_dir):
    if f.endswith(".xlsx") and len(f) == 13:   # DDMMYYYY.xlsx = 13 karakter
        try:
            tarih = datetime.strptime(f[:8], "%d%m%Y")
            excel_dosyalari.append((tarih, f))
        except ValueError:
            continue

excel_dosyalari.sort()   # Tarihe göre eskiden yeniye

if not excel_dosyalari:
    print(f"\n{RED}  [HATA] Hiç DDMMYYYY.xlsx dosyası bulunamadı!{RESET}")
    print(f"  Örnek dosya adları: 20022026.xlsx  21022026.xlsx")
    print(f"  Koy: {script_dir}")
    input("\n  Çıkış için Enter...\n")
    sys.exit(1)

print(f"\n  {len(excel_dosyalari)} Excel dosyası bulundu:\n")
for tarih, dosya in excel_dosyalari:
    print(f"    {CYAN}{dosya}{RESET}  ({tarih.strftime('%d.%m.%Y')})")

# ── Her Excel'i JSON'a dönüştür ───────────────────────────────────────────────
print()
baris("-")
print(f"  DÖNÜŞTÜRME BAŞLIYOR...")
baris("-")

donusturulan = []
en_guncel_tarih = None
en_guncel_json  = None

for tarih, excel_file in excel_dosyalari:
    json_file = tarih.strftime("%d%m%Y") + ".json"
    tarih_str = tarih.strftime("%d.%m.%Y")

    try:
        df = pd.read_excel(excel_file)
        mac_sayisi = len(df)
        df["_gunTarihi"] = tarih_str
        json_data = df.to_json(orient='records', force_ascii=False, indent=2)

        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(json_data)

        print(f"  {GREEN}✓{RESET} {excel_file} -> {BOLD}{json_file}{RESET}  ({mac_sayisi} maç)")
        donusturulan.append((tarih, json_file, excel_file, mac_sayisi))

        if en_guncel_tarih is None or tarih > en_guncel_tarih:
            en_guncel_tarih = tarih
            en_guncel_json  = json_file

    except Exception as e:
        print(f"  {RED}✗ {excel_file} HATA: {e}{RESET}")

if not donusturulan:
    print(f"\n{RED}  [HATA] Hiçbir dosya dönüştürülemedi!{RESET}")
    input("\n  Çıkış için Enter...\n")
    sys.exit(1)

# ── gunlukmaclar.json = en güncel günün kopyası ──────────────────────────────
if en_guncel_json:
    shutil.copy2(en_guncel_json, "gunlukmaclar.json")
    print(f"\n  {YELLOW}► gunlukmaclar.json{RESET} = {en_guncel_json} kopyası (fallback)")


# ── GitHub'a push ──────────────────────────────────────────────────────────────
baris("-")
print(f"  GITHUB'A YÜKLENİYOR...")
baris("-")

try:
    repo_dir = os.path.dirname(script_dir)  # oddsy-data koku

    tarih_aralik = (
        f"{donusturulan[0][0].strftime('%d.%m')}"
        + (f"-{donusturulan[-1][0].strftime('%d.%m.%Y')}" if len(donusturulan) > 1 else f".{donusturulan[0][0].strftime('%Y')}")
    )

    # ── git add (sadece bet365 klasörü)
    r = subprocess.run(["git", "add", "-A", "bet365/"], cwd=repo_dir, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {RED}[git add HATA]{RESET} {r.stderr.strip()}")
        raise Exception("stop")
    print(f"  git add {GREEN}OK{RESET}")

    # ── git commit (nothing to commit = normal) ──────────────────────────
    commit_msg = f"Haftalik bulten {tarih_aralik} ({len(donusturulan)} gun, toplam {sum(m for _,_,_,m in donusturulan)} mac)"
    r = subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo_dir, capture_output=True, text=True)
    if r.returncode != 0:
        combined = (r.stderr + " " + r.stdout).strip()
        if "nothing to commit" in combined.lower() or "nothing added" in combined.lower():
            print(f"  {YELLOW}[BİLGİ] Değişiklik yok, dosyalar zaten güncel. Push gerekmiyor.{RESET}")
            input(f"\n  Çıkış için Enter...\n")
            sys.exit(0)
        print(f"  {RED}[git commit HATA]{RESET} {combined}")
        raise Exception("stop")
    print(f"  git commit {GREEN}OK{RESET}")

    # ── git push (gerçek hatayı göster) ───────────────────────────────────
    print(f"  git push ediliyor...")
    r = subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, capture_output=True, text=True)
    if r.returncode != 0:
        err = r.stderr.strip()
        print(f"\n  {RED}[git push HATA]{RESET}")
        print(f"  {RED}{err}{RESET}")
        print()

        # Yardımcı ipucu
        if "rejected" in err.lower() or "non-fast-forward" in err.lower():
            print(f"  {YELLOW}Çözüm: Remote'da farklı şey var. Şunu dene:{RESET}")
            print(f"    cd {repo_dir}")
            print(f"    git pull --rebase origin main")
            print(f"    git push origin main")
        elif "authentication" in err.lower() or "403" in err or "could not read" in err.lower():
            print(f"  {YELLOW}Çözüm: GitHub kimlik doğrulama sorunu.{RESET}")
            print(f"    GitHub Desktop kullanıyorsan orada login ol.")
            print(f"    Veya: git credential-manager unconfigure && git push origin main")

        raise Exception("stop")

    # ── Başarılı! ─────────────────────────────────────────────────────────
    baris()
    print(f"{GREEN}{BOLD}  BAŞARILI! GITHUB'A PUSH EDİLDİ!{RESET}")
    print(f"\n  Yüklenen günler:")
    for tarih, json_file, _, mac_sayisi in donusturulan:
        print(f"    {GREEN}✓{RESET}  {tarih.strftime('%d.%m.%Y')}  →  {json_file}  ({mac_sayisi} maç)")
    print(f"\n  Site her gün otomatik olarak o günün verisini gösterir.")
    print(f"  (YapayZeka menüsü bugün: {datetime.now().strftime('%d%m%Y')}.json)")
    baris()

except FileNotFoundError:
    baris("-")
    print(f"{YELLOW}  [UYARI] Git bulunamadı - JSON'lar oluşturuldu, push yapılmadı.{RESET}")
    print(f"  Git: https://git-scm.com/download/win")
    baris("-")

except Exception as e:
    if "stop" not in str(e):
        print(f"  {RED}[BEKLENMEYEN HATA] {e}{RESET}")
    baris("-")
    print(f"  {YELLOW}JSON dosyaları oluşturuldu ama push yapılamadı.{RESET}")
    print(f"  {YELLOW}Yukarıdaki hata mesajına bak.{RESET}")
    baris("-")

input(f"\n  Çıkış için Enter...\n")
