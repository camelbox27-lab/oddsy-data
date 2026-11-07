"""Flashscore mac ozeti (df_sui) ham ciktisi: gol dakikasi alanlarini gormek icin."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
import flashscore_kaynak as fk  # noqa: E402

k = fk.FlashscoreKaynak()
for kod in sys.argv[1:]:
    r = k._get(f"{fk.FEED}df_sui_1_{kod}")
    print(f"===== {kod} ({len(r.text)} bayt)")
    for kayit in r.text.split("¬~")[:40]:
        print("  ", kayit[:300])
