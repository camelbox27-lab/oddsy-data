"""macOS uyumu. Windows'ta hiçbir şey yapmaz.

- macOS'ta tk.Button arka plan rengini göstermez (beyaz zemin üstüne beyaz yazı olur);
  renkli butonlar Label tabanlı bir butonla değiştirilir.
- Windows yazı tipi (Segoe UI) Mac'te yok ve Mac'te punto küçük görünür;
  yazı tipleri Mac karşılığına çevrilip büyütülür.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk

MAC = sys.platform == "darwin"
MAC_FONT = "Helvetica Neue"
OLCEK = 4 / 3  # Windows 96 dpi / Mac 72 dpi


def dosya_ac(yol):
    if MAC:
        subprocess.Popen(["open", str(yol)])
    elif sys.platform.startswith("win"):
        os.startfile(yol)
    else:
        subprocess.Popen(["xdg-open", str(yol)])


def _font_cevir(f):
    if isinstance(f, (tuple, list)) and f and isinstance(f[0], str) and f[0].startswith("Segoe"):
        f = list(f)
        f[0] = MAC_FONT
        if len(f) > 1 and isinstance(f[1], int) and f[1] > 0:
            f[1] = round(f[1] * OLCEK)
        return tuple(f)
    return f


class RenkliButon(tk.Label):
    """Mac'te rengini koruyan buton (tk.Button ile aynı şekilde kullanılır)."""

    _HAZIR = False

    def __init__(self, master=None, cnf=None, **kw):
        kw = {**(cnf or {}), **kw}
        self._komut = kw.pop("command", None)
        for k in ("overrelief", "default", "repeatdelay", "repeatinterval"):
            kw.pop(k, None)
        kw.setdefault("padx", 6)
        kw.setdefault("pady", 3)
        self._basili = False
        super().__init__(master, **kw)
        if not RenkliButon._HAZIR:
            self.bind_class("RenkliButon", "<ButtonPress-1>", RenkliButon._bas)
            self.bind_class("RenkliButon", "<ButtonRelease-1>", RenkliButon._birak)
            RenkliButon._HAZIR = True
        self.bindtags(("RenkliButon",) + self.bindtags())

    @staticmethod
    def _bas(e):
        b = e.widget
        if str(b.cget("state")) != "disabled":
            b._basili = True
            b._eski_relief = b.cget("relief")
            b.configure(relief="sunken")

    @staticmethod
    def _birak(e):
        b = e.widget
        if not b._basili:
            return
        b._basili = False
        b.configure(relief=b._eski_relief)
        x, y = e.x, e.y
        if 0 <= x < b.winfo_width() and 0 <= y < b.winfo_height():
            b.invoke()

    def invoke(self):
        if self._komut and str(self.cget("state")) != "disabled":
            return self._komut()

    def configure(self, cnf=None, **kw):
        kw = {**(cnf or {}), **kw}
        if "command" in kw:
            self._komut = kw.pop("command")
        for k in ("overrelief", "default"):
            kw.pop(k, None)
        return super().configure(**kw) if kw else super().configure()

    config = configure

    def __setitem__(self, k, v):
        self.configure(**{k: v})

    def cget(self, k):
        return self._komut if k == "command" else super().cget(k)

    __getitem__ = cget


def uygula():
    """Mac'te tkinter'ı yamalar; widget'lar oluşturulmadan önce çağrılmalı."""
    if not MAC:
        return
    eski_options = tk.Misc._options

    def _options(self, cnf, kw=None):
        if isinstance(cnf, dict) and "font" in cnf:
            cnf = {**cnf, "font": _font_cevir(cnf["font"])}
        if isinstance(kw, dict) and "font" in kw:
            kw = {**kw, "font": _font_cevir(kw["font"])}
        return eski_options(self, cnf, kw)

    tk.Misc._options = _options

    eski_style = ttk.Style.configure

    def _style_configure(self, style, query_opt=None, **kw):
        if "font" in kw:
            kw["font"] = _font_cevir(kw["font"])
        return eski_style(self, style, query_opt, **kw)

    ttk.Style.configure = _style_configure
    tk.Button = RenkliButon
