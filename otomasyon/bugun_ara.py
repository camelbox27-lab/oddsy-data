"""Bugunun bultenlerinde (iddaa + bet365) aranan tam oranlara uyan maclar.
Yalnizca loga yazar."""
import datetime as dt
import json
from pathlib import Path

kok = Path(__file__).resolve().parent.parent
bugun = dt.date.today()


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


print("=== IDDAA (IY 1.5 Ust = 1.90 / 1.95, 2.5 Ust = 1.44)")
L = json.load(open(kok / "iddaa/gunluk/gunlukmaclar.json", encoding="utf-8"))
L = [m for m in L if m.get("Tarih") == bugun.strftime("%d.%m.%Y")]
print(f"bulten: {len(L)} mac, IY 1.5 Ust olan: {sum(1 for m in L if f(m.get('IY AU 1.5 Ust')))}")
for m in sorted(L, key=lambda m: m.get("Saat", "")):
    iy, u = f(m.get("IY AU 1.5 Ust")), f(m.get("AU 2.5 Ust"))
    if iy in (1.90, 1.95) or u == 1.44:
        print(f"  {m['Saat']} {m['Ev Sahibi']} - {m['Konuk Ekip']} ({m['Lig']})  IY1.5U {iy}  2.5U {u}  3.5U {m.get('AU 3.5 Ust')}  KG {m.get('KG Var')}")

print("\n=== BET365 (2.5 Ust = 1.44; + 3.5 Ust = 2.10)")
B = json.load(open(kok / f"bet365/{bugun.strftime('%d%m%Y')}.json", encoding="utf-8"))
print(f"bulten: {len(B)} mac")
for m in sorted(B, key=lambda m: m["Tarih"]):
    if m.get("UST25 K") == 1.44:
        s = dt.datetime.fromtimestamp(m["Tarih"] / 1000, dt.timezone.utc).strftime("%H:%M")
        ek = "  <<< 3.5U 2.10" if m.get("UST35 K") == 2.1 else ""
        print(f"  {s} {m['Ev']} - {m['Dep']} ({m['Lig']})  2.5U {m.get('UST25 K')}  3.5U {m.get('UST35 K')}  KG {m.get('KGVAR K')}{ek}")
