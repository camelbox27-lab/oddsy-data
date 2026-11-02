"""bet365 bulten arsivindeki bitmis maclarin yari skorlari (analiz icin).

Cikti (log): KOD IY_EV IY_DEP Y2_EV Y2_DEP  -- satir basi "YS " ile.
Siteye ve hicbir dosyaya yazmaz.
"""
import datetime as dt
import glob
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "kaynak"))
import flashscore_kaynak as fk  # noqa: E402

kok = Path(__file__).resolve().parent.parent
bugun = dt.date.today()
kodlar = []
for f in sorted(glob.glob(str(kok / "bet365" / "[0-9]*.json"))):
    ad = Path(f).stem
    gun = dt.date(int(ad[4:]), int(ad[2:4]), int(ad[:2]))
    if gun >= bugun:
        continue
    kodlar += [m["MatchCode"] for m in json.load(open(f, encoding="utf-8")) if m.get("MatchCode")]
kodlar = list(dict.fromkeys(kodlar))
print("mac:", len(kodlar), flush=True)

k = fk.FlashscoreKaynak()
tamam = 0
for i, kod in enumerate(kodlar):
    try:
        r = k._get(f"{fk.FEED}df_sui_1_{kod}")
    except Exception as e:
        print("HATA", kod, e, flush=True)
        continue
    yari = {}
    for kayit in r.text.split("¬~"):
        d = dict(a.split("÷", 1) for a in kayit.split("¬") if "÷" in a)
        ac = d.get("AC", "")
        if ac[:2] in ("1.", "2.") and "IG" in d and "IH" in d:
            yari.setdefault(ac[0], (d["IG"], d["IH"]))
    if "1" in yari and "2" in yari:
        print("YS", kod, *yari["1"], *yari["2"], flush=True)
        tamam += 1
    time.sleep(0.15)
print("bitti:", tamam, "/", len(kodlar), flush=True)
