"""Headless (sunucu) ortamda tkinter taklidi.

iddaapro.py tek dosya oldugu icin modul seviyesinde `import tkinter` yapiyor.
GitHub Actions runner'inda Tk yok; bu modul iddaapro'dan ONCE import edilince
tkinter/tkcalendar yerine zararsiz sahte moduller koyar. Boylece iddaapro.py'yi
hic degistirmeden icindeki cekme/parse/Excel fonksiyonlari kullanilabilir
(tek kaynak korunur, mantik catallanmaz).

GUI siniflari (IddaaProApp vb.) tanimlanir ama ASLA ornek olusturulmaz.
"""
import sys
import types


class _Sahte:
    """Her turlu kullanimi sessizce yutan nesne."""

    def __init__(self, *a, **k):
        pass

    def __getattr__(self, ad):
        return _Sahte()

    def __call__(self, *a, **k):
        return _Sahte()


def _sahte_modul(ad):
    m = types.ModuleType(ad)

    # Erisilen her isim, alt sinif olarak tureteilebilsin diye SINIF dondurur
    # (ornegin mac_uyum.py icindeki `class RenkliButon(tk.Label)` bunu gerektirir).
    def _getattr(isim, _m=m):
        tip = type(isim, (_Sahte,), {})
        setattr(_m, isim, tip)
        return tip

    m.__getattr__ = _getattr
    return m


def kur():
    """tkinter ve tkcalendar'i sahte modullerle degistirir."""
    for ad in ("tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog",
               "tkinter.font", "tkinter.colorchooser", "tkinter.simpledialog",
               "tkcalendar"):
        if ad not in sys.modules:
            sys.modules[ad] = _sahte_modul(ad)

    tk = sys.modules["tkinter"]
    tk.ttk = sys.modules["tkinter.ttk"]
    tk.messagebox = sys.modules["tkinter.messagebox"]
    tk.filedialog = sys.modules["tkinter.filedialog"]
    tk.font = sys.modules["tkinter.font"]
    tk.TkVersion = 8.6
    tk.TclVersion = 8.6
