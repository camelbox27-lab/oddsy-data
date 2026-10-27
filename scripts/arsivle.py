#!/usr/bin/env python3
"""Günlük bülteni tarih damgalı bir kopya olarak arşivler.

Bülten dosyaları her gün üzerine yazılıyor; maç sayfalarının kalıcı olması için
her çalıştırmada o günün anlık görüntüsü ayrı bir dosyaya kopyalanır.
Aynı gün tekrar çalışırsa dosya güncellenir (kapanış oranları gün içinde değişir).
"""
import json
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Türkiye saatine göre gün belirlenir, UTC'ye göre değil
TR = timezone(timedelta(hours=3))

ROOT = Path(__file__).resolve().parent.parent

KAYNAKLAR = [
    (ROOT / 'bet365' / 'gunlukmaclar.json', ROOT / 'bet365' / 'arsiv'),
    (ROOT / 'iddaa' / 'gunluk' / 'gunlukmaclar.json', ROOT / 'iddaa' / 'arsiv'),
]


def gecerli_json(yol: Path) -> bool:
    """Bozuk ya da boş bir dosyayı arşive almayalım."""
    try:
        with yol.open(encoding='utf-8') as f:
            veri = json.load(f)
    except (OSError, ValueError) as hata:
        print(f'  ATLANDI {yol.name}: okunamadı ({hata})')
        return False
    if not isinstance(veri, list) or not veri:
        print(f'  ATLANDI {yol.name}: liste değil veya boş')
        return False
    print(f'  {yol.name}: {len(veri)} kayıt')
    return True


def main() -> None:
    bugun = datetime.now(TR).strftime('%Y-%m-%d')
    print(f'[arsivle] Tarih (TR): {bugun}')

    for kaynak, hedef_dizin in KAYNAKLAR:
        if not kaynak.exists():
            print(f'  ATLANDI {kaynak}: dosya yok')
            continue
        if not gecerli_json(kaynak):
            continue
        hedef_dizin.mkdir(parents=True, exist_ok=True)
        hedef = hedef_dizin / f'{bugun}.json'
        shutil.copy2(kaynak, hedef)
        print(f'  -> {hedef.relative_to(ROOT)}')
        indeks_yaz(hedef_dizin)


def indeks_yaz(dizin: Path) -> None:
    """Arşivdeki günleri listeler.

    Siteyi derleyen taraf hangi günlerin mevcut olduğunu GitHub API'sine
    sormadan buradan öğrenir.
    """
    gunler = sorted(p.stem for p in dizin.glob('*.json') if p.name != 'index.json')
    indeks = dizin / 'index.json'
    with indeks.open('w', encoding='utf-8') as f:
        json.dump({'gunler': gunler, 'guncellendi': datetime.now(TR).isoformat()}, f,
                  ensure_ascii=False, indent=2)
    print(f'  -> {indeks.relative_to(ROOT)} ({len(gunler)} gün)')


if __name__ == '__main__':
    main()
