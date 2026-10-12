"""
Chroma Kit — UI theme presets for Krita.
Created by SubToSidb.

Uses the direct addExtension pattern (same as plugin_importer which is Kila's
built-in working plugin). The __init__.py runs at module import time,
creates the Extension, and registers it with krita.Krita.instance().addExtension().
No helloWorld() function — Kila's loader doesn't call it.

Supports saving/loading color presets so you can experiment with gradients
and different color schemes. Presets are saved as JSON files next to the plugin.
"""
import os
import sys
import json
import traceback

_LOG = os.path.join(os.path.dirname(__file__), "chroma-kit-debug.log")
_PRESETS_DIR = os.path.join(os.path.dirname(__file__), "presets")
_STATE_FILE = os.path.join(os.path.dirname(__file__), "chroma-kit-state.json")
# Sentinel name for "no preset" — clears the stylesheet so Krita uses its own
# default theme UI. Persisted like any other selection; restoring it re-clears.
NO_PRESET = "__none__"


def _log(msg):
    try:
        with open(_LOG, "a") as f:
            f.write(msg + "\n")
            f.flush()
    except Exception:
        pass


_log("=" * 50)
_log("[chroma_kit] MODULE IMPORT STARTING")
print("[chroma_kit] MODULE IMPORT STARTING", flush=True)

# Import krita APIs
from krita import Extension, Krita  # noqa: E402
_log("[chroma_kit] krita imports OK")

from PyQt5.QtCore import QEvent, QPointF, QTimer, Qt, QSize  # noqa: E402
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF  # noqa: E402
from PyQt5.QtWidgets import (QApplication, QMessageBox, QInputDialog,  # noqa: E402
                             QWidget, QDockWidget, QToolBar, QMenuBar, QStatusBar,
                             QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                             QListWidgetItem, QLabel, QPushButton, QTextEdit,
                             QTabWidget, QTabBar, QSlider, QProgressBar, QGroupBox,
                             QCheckBox, QRadioButton, QLineEdit, QComboBox,
                             QSpinBox, QMainWindow, QToolButton)
import math  # noqa: E402
import colorsys  # noqa: E402
_log("[chroma_kit] PyQt5 imports OK")
print("[chroma_kit] PyQt5 imports OK", flush=True)


# --- Color preset system ---

# Default color scheme — dark wine red
DEFAULT_COLORS = {
    "name": "Dark Wine Red",
    "border": "#4d0000",
    "border_hover": "#cc6666",
    "bg": "#000000",
    "bg_hover": "#1a0000",
    "bg_selected": "#1a0000",
    "bg_pressed": "#4d0000",
    "text": "#cc6666",
    "text_disabled": "#993333",
    "accent": "#cc6666",
    "accent_bright": "#ff9999",
}


def build_qss_for(colors):
    """Build the full QSS string for a preset dict, using the exact same
    dispatch order as ChromaKitExtension._apply_qss. Shared by the live
    apply path and the preview dialog so preview is never out of sync."""
    if colors.get("custom_qss"):
        strip_keys = ("custom_qss", "gradient", "gradient_start", "gradient_end",
                      "gradient_mid1", "gradient_mid2", "glow_color", "glow_size")
        base_colors = {k: v for k, v in colors.items() if k not in strip_keys}
        qss = build_qss(base_colors)
        custom = colors["custom_qss"]
        if isinstance(custom, list):
            custom = "\n".join(custom)
        return qss + "\n" + custom
    elif colors.get("glow_color"):
        return build_qss_multigradient(colors)
    elif colors.get("gradient"):
        return build_qss_gradient(colors)
    return build_qss(colors)


def build_qss(c):
    """Build QSS string from a color dict."""
    return f"""
* {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']} !important;
}}
QMainWindow {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
}}
QDockWidget {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    font-size: 11px;
}}
QDockWidget::title {{
    background-color: {c['bg']} !important;
    border: 1px solid {c['border']};
    border-bottom: 1px solid {c['border']};
    padding: 1px;
    color: {c['text']};
    font-weight: bold;
}}
QDockWidget::close-button, QDockWidget::float-button {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
}}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    border: 1px solid {c['accent']};
    background-color: {c['bg_hover']} !important;
}}
QGroupBox {{
    border: 1px solid {c['border']};
    border-radius: 0px;
    margin-top: 1px;
    font-weight: bold;
    color: {c['text']};
    background-color: {c['bg']} !important;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 1px;
    color: {c['text']};
}}
QPushButton {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
    padding: 1px 2px;
    font-weight: bold;
}}
QPushButton:hover {{
    border: 1px solid {c['accent']};
    background-color: {c['bg_hover']} !important;
}}
QPushButton:pressed {{
    border: 1px solid {c['accent_bright']};
    background-color: {c['bg_pressed']} !important;
}}
QTabBar::tab {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
    padding: 1px 2px;
}}
QTabBar::tab:selected {{
    background-color: {c['bg_selected']} !important;
    color: {c['text']};
    border: 1px solid {c['accent']};
}}
QTabBar::tab:!selected:hover {{
    background-color: {c['bg_hover']} !important;
    border: 1px solid {c['accent']};
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
    padding: 1px 2px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {c['accent']};
}}
QComboBox::drop-down {{
    border: 1px solid {c['accent']};
    background-color: {c['bg']} !important;
}}
QCheckBox, QRadioButton {{
    color: {c['text']};
}}
QCheckBox::indicator, QRadioButton::indicator {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c['bg_pressed']} !important;
    border: 1px solid {c['accent']};
}}
QMenuBar {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
}}
QMenuBar::item:selected {{
    background-color: {c['bg_selected']} !important;
    color: {c['text']};
}}

QToolBar {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
}}
QToolBar::separator {{
    background-color: {c['border']};
    width: 1px;
    height: 8px;
}}
QToolBar QToolButton {{
    border: 1px solid transparent;
    background-color: transparent;
    color: {c['text']};
    padding: 1px 2px;
}}
QToolBar QToolButton:hover {{
    border: 1px solid {c['accent']};
    background-color: {c['bg_hover']} !important;
}}
QToolBar QToolButton:pressed, QToolBar QToolButton:checked {{
    border: 1px solid {c['accent']};
    background-color: {c['bg_pressed']} !important;
    color: {c['accent_bright']};
}}
QToolBar QToolButton:checked {{
    border: 2px solid {c['accent']};
    background-color: {c['bg_pressed']} !important;
}}
QToolButton {{
    border: 1px solid transparent;
    background-color: transparent;
    color: {c['text']};
    padding: 1px 2px;
}}
QToolButton:hover {{
    border: 1px solid {c['accent']};
    background-color: {c['bg_hover']} !important;
}}
QToolButton:pressed, QToolButton:checked {{
    border: 2px solid {c['accent']};
    background-color: {c['bg_pressed']} !important;
    color: {c['accent_bright']};
}}

QStatusBar {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
}}
QSplitter::handle {{
    background-color: {c['border']};
}}
QProgressBar {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
}}
QProgressBar::chunk {{
    background-color: {c['accent']} !important;
    border: 1px solid {c['accent']};
}}
QHeaderView::section {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
}}
QDialog {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
}}
QToolTip {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
}}
QAbstractItemView {{
    border: 1px solid {c['border']};
    background-color: {c['bg']} !important;
    color: {c['text']};
}}
QAbstractItemView::item:selected, QAbstractItemView::item:selected:focus {{
    background-color: {c['bg_selected']} !important;
    color: {c['text']};
    border: 1px solid {c['accent']};
}}
QAbstractItemView::item:selected:!active {{
    background-color: {c['bg_selected']} !important;
    color: {c['text']};
}}
QAbstractItemView::item:hover {{
    background-color: {c['bg_hover']} !important;
    color: {c['text']};
}}
QTreeView::item, QTreeWidget::item, QTreeWidgetItem {{
    background-color: {c['bg']} !important;
}}
QTreeWidget {{
    background-color: {c['bg']} !important;
}}
QListWidget {{
    background-color: {c['bg']} !important;
}}
QListView {{
    background-color: {c['bg']} !important;
}}
QTableWidget {{
    background-color: {c['bg']} !important;
}}
QTableCornerButton {{
    background-color: {c['bg']} !important;
}}
QSplitter {{
    background-color: {c['bg']} !important;
}}
QFrame {{
    background-color: {c['bg']} !important;
}}
QStackedWidget {{
    background-color: {c['bg']} !important;
}}
QScrollArea {{
    background-color: {c['bg']} !important;
}}
QTabWidget {{
    background-color: {c['bg']} !important;
}}
QTabWidget::pane {{
    background-color: {c['bg']} !important;
}}
QWidget {{
    background-color: {c['bg']} !important;
}}
"""


# --- Gradient example preset ---

GRADIENT_PRESET = {
    "name": "Gradient Dark",
    "border": "#330000",
    "border_hover": "#cc6666",
    "bg": "#000000",
    "bg_hover": "#1a0000",
    "bg_selected": "#1a0000",
    "bg_pressed": "#4d0000",
    "text": "#cc6666",
    "text_disabled": "#993333",
    "accent": "#cc6666",
    "accent_bright": "#ff9999",
    "gradient": True,
    "gradient_start": "#000000",
    "gradient_end": "#1a1a1a",
    "gradient_mid1": "#0a0a0a",
    "gradient_mid2": "#1a0000",
    "glow_color": "#4d0000",
    "glow_size": 2,
}


def build_qss_gradient(c):
    """Build QSS with gradient backgrounds — shows how far you can push QSS."""
    base_colors = {k: v for k, v in c.items() if k not in ("gradient", "gradient_start", "gradient_end")}
    base = build_qss(base_colors)

    # Gradient rules come AFTER base so they override the !important
    gradient_qss = f"""
QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {c['gradient_start']}, stop:1 {c['gradient_end']}) !important;
    color: {c['text']};
    border: 1px solid {c['accent']};
}}
QPushButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c['gradient_start']}, stop:1 {c['gradient_end']}) !important;
    border: 2px solid {c['accent']};
    color: {c['accent_bright']};
}}
QToolBar QToolButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c['gradient_start']}, stop:1 {c['gradient_end']}) !important;
    border: 2px solid {c['accent']};
}}
"""
    return base + gradient_qss


def build_qss_multigradient(c):
    """Build QSS with multi-stop gradients and glow effects."""
    # Strip gradient-only keys so build_qss doesn't choke on them
    base_colors = {k: v for k, v in c.items() if k not in (
        "gradient", "gradient_start", "gradient_end",
        "gradient_mid1", "gradient_mid2", "glow_color", "glow_size"
    )}
    # build_qss sets !important everywhere — so we need to override
    # the specific selectors AFTER it with gradient versions
    base = build_qss(base_colors)

    g_start = c.get("gradient_start", c["bg"])
    g_mid1 = c.get("gradient_mid1", c["bg_hover"])
    g_mid2 = c.get("gradient_mid2", c["bg_selected"])
    g_end = c.get("gradient_end", c["bg"])
    glow = c.get("glow_color", c["accent"])
    glow_size = c.get("glow_size", 2)

    # This gradient QSS comes AFTER base, so it overrides the !important
    # background-color on :selected/:checked states
    multi_qss = f"""
QTabBar::tab:selected, QToolBar QToolButton:checked, QPushButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {g_start},
        stop:0.3 {g_mid1},
        stop:0.7 {g_mid2},
        stop:1 {g_end}
    ) !important;
    color: {c['text']};
    border: 1px solid {glow};
}}
QToolBar QToolButton:checked {{
    border: {glow_size}px solid {glow};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {g_mid2},
        stop:1 {g_start}
    ) !important;
    color: {c['accent_bright']};
    border: 1px solid {glow};
}}
QMenuBar::item:selected, QAbstractItemView::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {g_mid1},
        stop:0.5 {g_mid2},
        stop:1 {g_end}
    ) !important;
    color: {c['text']};
    border: 1px solid {glow};
}}
"""
    # gradient QSS first (gets overridden by base), then base
    return base + multi_qss


def load_presets():
    """Load all preset color schemes from the presets directory.
    Only seed built-in fallbacks for presets that still rely on them; every
    JSON-authored theme overrides by name. 'Darker Wine Red' is the current
    name of the former 'Gradient Dark' preset."""
    presets = {"Dark Wine Red": DEFAULT_COLORS, "Darker Wine Red": GRADIENT_PRESET}
    if os.path.isdir(_PRESETS_DIR):
        for fname in os.listdir(_PRESETS_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(_PRESETS_DIR, fname), "r") as f:
                        json_preset = json.load(f)
                    name = json_preset.get("name", fname)
                    if name in presets:
                        # Merge: JSON values override built-in, but keep custom_qss from built-in
                        merged = dict(presets[name])
                        merged.update(json_preset)
                        if "custom_qss" not in json_preset and "custom_qss" in presets[name]:
                            merged["custom_qss"] = presets[name]["custom_qss"]
                        presets[name] = merged
                    else:
                        presets[name] = json_preset
                except Exception as e:
                    _log(f"[chroma_kit] Failed to load preset {fname}: {e}")
    return presets


# Current active colors — restored from the saved state file if present,
# so the theme you picked last survives Krita restarts.
def _load_state():
    """Read the persisted active-theme name, or None."""
    try:
        if os.path.isfile(_STATE_FILE):
            with open(_STATE_FILE, "r") as f:
                return json.load(f).get("active")
    except Exception as e:
        _log(f"[chroma_kit] state load failed: {e}")
    return None


def _save_state(name):
    """Persist the active-theme name so it survives Krita restarts."""
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({"active": name}, f)
        _log(f"[chroma_kit] state saved: {name}")
    except Exception as e:
        _log(f"[chroma_kit] state save failed: {e}")


_presets = load_presets()
_active_name = _load_state()
if _active_name == NO_PRESET:
    # No preset selected — leave Krita's own theme in place.
    _colors = {"name": "No Preset"}
    _log("[chroma_kit] restored: no preset (Krita default theme)")
elif _active_name and _active_name in _presets:
    _colors = dict(_presets[_active_name])
    _log(f"[chroma_kit] restored active theme: {_active_name}")
elif "Redline" in _presets:
    _colors = dict(_presets["Redline"])
else:
    _colors = dict(DEFAULT_COLORS)


# --- Texture overlay system -------------------------------------------------
# Krita's QSS engine does not paint background-image (verified: no URL form
# works). Textures are instead painted by a child widget that sits at the
# bottom of the main window's child stack, so every sibling above it that has
# a translucent QSS fill lets the pattern show through — same visibility as
# the QSS window gradient itself. A preset activates a texture with a dict:
#   "texture": {"pattern": "honeycomb", "alpha": 55, "scale": 90,
#               "width": 2.0, "color": "#fde68a"}
# Patterns: honeycomb, dots, hatch.


class TextureOverlay(QWidget):
    """Child widget painting a repeating pattern under all sibling widgets."""

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._params = None
        self._tile = None
        self._bg = None
        self._mask_hash = None
        self.setGeometry(parent_window.rect())
        parent_window.installEventFilter(self)
        self.lower()
        self.hide()
        # NO polling, NO constant repaint: paint once per preset-load and on
        # window resize only. Docker moves are picked up next time a preset
        # is loaded/applied. Zero idle cost by design.
        _log("[chroma_kit] TextureOverlay created")

    def set_params(self, params):
        self._params = params
        self._tile = None  # force rebuild on next paint
        self._bg = None
        self._mask_hash = None
        if params:
            self.show()
            self.lower()  # show() re-raises; order matters
        else:
            self.hide()

    def eventFilter(self, obj, ev):
        try:
            if obj is self.parentWidget() and ev.type() == QEvent.Resize:
                self.setGeometry(self.parentWidget().rect())
                self._bg = None      # force one rebuild at the new size
                self.update()        # single repaint for the resize
        except Exception:
            pass
        return False


    def _masked_rects(self, parent):
        """Geometry of every content panel the texture must stay out of.
        Uses findChildren so nested/wrapped dockers are caught too."""
        rects = []
        try:
            for c in parent.findChildren(QDockWidget):
                if c.isVisible() and not c.isWindow():
                    rects.append((c.objectName() or "dock", c.geometry()))
            for cls in (QToolBar, QMenuBar, QStatusBar):
                for c in parent.findChildren(cls):
                    if c.isVisible() and not c.isWindow():
                        rects.append((c.objectName() or cls.__name__, c.geometry()))
            cw = parent.centralWidget()
            if cw is not None and cw.isVisible():
                rects.append(("central", cw.geometry()))
        except Exception as e:
            _log(f"[chroma_kit] _masked_rects FAILED: {e}")
        return rects

    def paintEvent(self, ev):
        try:
            if not self._params:
                return
            self._paint_count = getattr(self, "_paint_count", 0) + 1
            if self._paint_count % 20 == 1:
                _log(f"[chroma_kit] overlay paints: {self._paint_count}")
            if self._tile is None:
                self._build_tile()
            if self._tile is None or self._tile.isNull():
                return
            parent = self.parentWidget()
            avoid = bool(self._params.get("avoid_panels", True))
            mask = self._masked_rects(parent) if avoid else []
            fp = (self.size(), tuple(mask))
            if self._bg is None or self._bg.isNull() or fp != self._mask_hash:
                # rebuild: tiled pattern, then erase under panels -> clean edges
                bg = QPixmap(self.size())
                if bg.isNull():
                    return
                bg.fill(Qt.transparent)
                p = QPainter(bg)
                p.drawTiledPixmap(bg.rect(), self._tile)
                if mask:
                    p.setCompositionMode(QPainter.CompositionMode_Clear)
                    for _name, r in mask:
                        p.drawRect(r)
                p.end()
                self._bg = bg
                self._mask_hash = fp
                _log(f"[chroma_kit] texture bg rebuilt: {len(mask)} panels masked "
                     f"({', '.join(sorted(set(n for n, _ in mask))) or 'NONE'})")
            if self._bg is None or self._bg.isNull():
                return
            p = QPainter(self)
            p.drawPixmap(0, 0, self._bg)
        except Exception as e:
            _log(f"[chroma_kit] paintEvent FAILED (texture disabled): {e}")
            try:
                self.hide()   # never take Krita down with us
            except Exception:
                pass

    def _draw_honeycomb_layers(self, painter, color, width, tw, th):
        """Three descending hex lattices in one tile = depth illusion.
        Near: 2 hex rows per tile, full alpha. Mid: 4 rows, 55% alpha.
        Far: 8 rows, 30% alpha. All pitches are exact fractions of the tile
        so every layer is perfectly tile-periodic (no seams at any scale)."""
        layers = [
            (4, 0.75, 0.33),   # (rows_per_tile, alpha_mult, row_offset_frac)
            (8, 0.50, 0.66),
        ]
        for rows_per, amult, off in layers:
            lrow = th / float(rows_per)            # exact period divisor
            lscale = tw / (1.0 if rows_per == 2 else float(rows_per // 2))
            lR = lscale / math.sqrt(3)
            c = QColor(color)
            c.setAlpha(max(1, int(round(color.alpha() * amult))))
            thin = 0.9 if rows_per == 4 else 0.8
            painter.setPen(QPen(c, max(1.0, width * thin)))
            margin = lR + width + 2
            r0 = -int(margin // lrow) - 1
            r1 = int((th + margin) // lrow) + 2
            y_off = lrow * off
            for r in range(r0, r1):
                y = (lrow * r + y_off) % th
                xoff = lscale / 2.0 if (r % 2) else 0.0
                c0 = -int((margin + xoff) // lscale) - 1
                c1 = int((tw + margin) // lscale) + 2
                for cc in range(c0, c1):
                    cx = lscale * cc + xoff
                    pts = QPolygonF([QPointF(
                        cx + lR * math.cos(math.radians(90 + 60 * k)),
                        y + lR * math.sin(math.radians(90 + 60 * k)))
                        for k in range(6)])
                    painter.drawPolygon(pts)


    def _shade_tile_rows(self, pm, params):
        """Modulate tile rows by the window's vertical light position so
        texture brightness follows the golden-hour gradient: brighter near
        the top of the window, nearly gone at the dark band, lifted slightly
        at the floor. Runs once at tile build (cached), not per-frame."""
        try:
            grad = params.get("shade")
            if not grad:
                return pm
            top = float(grad.get("top", 1.0))     # brightness at window top
            mid = float(grad.get("mid", 0.25))    # at dark band
            bot = float(grad.get("bot", 0.45))    # at window floor
            if top <= 0 and mid <= 0 and bot <= 0:
                return pm
            img = pm.toImage()
            h = img.height()
            w_ = img.width()
            for y in range(h):
                t = y / max(1, h - 1)
                if t < 0.55:
                    f = top + (mid - top) * (t / 0.55)
                else:
                    f = mid + (bot - mid) * ((t - 0.55) / 0.45)
                f = max(0.0, min(2.0, f))
                if abs(f - 1.0) < 0.02:
                    continue
                for x in range(w_):
                    px = img.pixel(x, y)
                    a = (px >> 24) & 0xFF
                    if a:
                        na = max(0, min(255, int(a * f)))
                        # keep rgb, change alpha only
                        img.setPixel(x, y, (px & 0x00FFFFFF) | (na << 24))
            out = QPixmap.fromImage(img)
            _log("[chroma_kit] tile shaded by gradient profile")
            return out
        except Exception as e:
            _log(f"[chroma_kit] _shade_tile_rows FAILED: {e}")
            return pm

    def _build_tile(self):
        try:
            p = self._params
            pattern = p.get("pattern", "honeycomb")
            scale = max(8, int(p.get("scale", 90)))
            alpha = max(1, min(255, int(p.get("alpha", 55))))
            width = max(1.0, float(p.get("width", 2.0)))
            color = QColor(p.get("color", "#fde68a"))
            color.setAlpha(alpha)

            if pattern == "honeycomb":
                tw = scale
                th = int(round(scale * math.sqrt(3)))
            elif pattern == "honeycomb1":
                tw = scale
                th = int(round(scale * math.sqrt(3)))
            elif pattern == "dots":
                step = max(4, scale // 3)
                tw = th = step * 3
            else:  # hatch (also the fallback pattern)
                step = max(6, scale // 4)
                tw = th = step * 4

            pm = QPixmap(tw, th)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.Antialiasing, True)

            if pattern == "honeycomb":
                self._draw_honeycomb_layers(painter, color, width, tw, th)
            elif pattern == "honeycomb1":
                R = tw / math.sqrt(3)
                row_pitch = th / 2.0  # exact periodicity; hexes stay regular to 0.08%
                painter.setPen(QPen(color, width))
                margin = R + width + 2
                r0 = -int(margin // row_pitch) - 1
                r1 = int((th + margin) // row_pitch) + 2
                for r in range(r0, r1):
                    y = row_pitch * r
                    xoff = tw / 2.0 if (r % 2) else 0.0
                    c0 = -int((margin + xoff) // tw) - 1
                    c1 = int((tw + margin) // tw) + 2
                    for c in range(c0, c1):
                        cx = tw * c + xoff
                        pts = QPolygonF([QPointF(
                            cx + R * math.cos(math.radians(90 + 60 * k)),
                            y + R * math.sin(math.radians(90 + 60 * k)))
                            for k in range(6)])
                        painter.drawPolygon(pts)
            elif pattern == "dots":
                step = tw // 3
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                for gy in range(4):
                    for gx in range(4):
                        painter.drawEllipse(QPointF(gx * step, gy * step), width, width)
            else:  # hatch
                painter.setPen(QPen(color, width))
                for k in range(-2, (tw + th) // step + 2):
                    x0 = k * step
                    painter.drawLine(QPointF(x0, 0), QPointF(x0 + th, th))

            painter.end()
            if pattern == "honeycomb":
                pm = self._shade_tile_rows(pm, self._params)
            self._tile = pm
            _log(f"[chroma_kit] texture tile built: {pattern} {tw}x{th} alpha={alpha}")
        except Exception as e:
            _log(f"[chroma_kit] texture tile build FAILED: {e}")
            self._tile = None


# --- Theme descriptions (shown in the Load Theme picker) -------------------
# One-line plain-language descriptions keyed by preset name. Presets not
# listed here simply show "No description." — never block loading.
DESCRIPTIONS = {
    "Redline": "Deep red on near-black. Aggressive, high-contrast, the default house look.",
    "Static": "Ink/teal base with coral and chartreuse. Deliberately clashing, messy energy.",
    "Cerulean": "Bright sky-blue on deep ocean. Clean, cool, calm.",
    "Ember": "Soft red on dark. Gentle, muted, easy on the eyes.",
    "Emberline": "Red-copper and deep rose on black espresso. Hot metal, engraved serif headers.",
    "Sienna": "Warm copper and rose on dark espresso. Softer, more golden than Emberline.",
    "Zaffre": "Steel-cyan and pale ice on blue-charcoal. Cold instrument-panel look.",
    "Honey": "Amber and gold on dark brown. Warm, honeyed, low-key.",
    "Lumen": "Soft violet on dark. Gentle, muted, easy on the eyes.",
    "Mono": "Pure grayscale. No color at all — flat and neutral.",
    "Phosphor": "Terminal green on black. Retro CRT vibes.",
    "Verdant": "Bright green on dark. Fresh, lively, nature-toned.",
    "Vivid": "Saturated violet. Punchy and loud.",
    "Gold Glow": "Bright gold with glow accents. Loud, celebratory.",
    "Blue Glow": "Soft blue with glow accents. Calm, cool, glowing edges.",
    "Purple Glow": "Light purple with glow. Dreamy, soft.",
    "Rainbow Glow": "Multi-hue glow. Everything at once.",
    "Glow Black": "Black with a red glow. Minimal, single-accent neon.",
    "Dark Wine Red": "Deep wine red on pure black. The original house default.",
    "Gradient Dark": "Dark red with a subtle gradient. The earliest preset.",
    "Darker Wine Red": "Deeper wine red with a subtle gradient. The renamed 'Gradient Dark'.",
    "Magenta": "Hot magenta and soft rose on dark plum. Rounded, borderless, two-hue sweeps.",
    "Azure": "Electric blue on deep navy. Cool single hue, lit-from-above gradients.",
    "Acid": "Acid lime on near-black. High-saturation neon with a lime sheen.",
    "Capsule": "Abstract by shape: absurd radii everywhere — pill buttons, circular tabs, round inputs.",
    "Branded Bronze": "Tiled bronze banding, double-border frames, letter-spacing, inverted selection.",
    "Cobalt Weave": "Blue companion to Branded Bronze: tiled cobalt banding, double borders, inverted selection.",
    "Interference": "Static's clashing gradient axes in new colors — violet base, amber and mint accents.",
    "Moire": "Reflect-mode interference banding — a vibrating op-art moire pattern. Cyan-teal and violet.",
    "Neon Halo": "Fake neon glow via stacked borders and outlines. Hot magenta and electric cyan.",
    "Terminal": "Shell / ASCII look. Heavy monospace, bright green on black, TTY vibes.",
    "Jumbo": "Oversized 18px type so labels overflow and feel cramped and aggressive.",
}


def _krita_preview_button(act, checked=None):
    """Build a QToolButton that LOOKS like a real Krita toolbar button (same
    icon, same tooltip, same styling) but NEVER triggers the action — it takes
    only the icon and text, never setDefaultAction, so a click in the preview
    can't mutate the live Krita session (mirror the canvas, open a docker,
    etc.). checked: None = plain, True/False = force checkable state."""
    b = QToolButton()
    try:
        b.setIcon(act.icon())
    except Exception:
        pass
    try:
        b.setToolTip(act.toolTip())
    except Exception:
        pass
    if checked is not None:
        b.setCheckable(True)
        b.setChecked(checked)
    return b


def build_preview_panel(parent):
    """A mock of Krita's real UI built from the actual widget classes, so a
    dialog-scoped stylesheet applied to it renders every selector your themes
    use. Returns the outer QMainWindow; callers do panel.setStyleSheet(qss).
    The Krita-buttons row uses REAL Krita toolbar actions (icon only, never
    triggered), so those buttons carry the exact icons you see in Krita."""
    win = QMainWindow(parent)
    win.setWindowFlags(Qt.Widget)
    central = QWidget(win)
    win.setCentralWidget(central)
    v = QVBoxLayout(central)
    v.setContentsMargins(8, 8, 8, 8)
    v.setSpacing(8)

    # menu bar
    mb = QMenuBar(win)
    mb.addAction("File")
    mb.addAction("Edit")
    mb.addAction("View")
    v.addWidget(mb)

    # toolbar with a checked + unchecked button
    tb = QToolBar(win)
    tb.addAction("Brush")
    tb.addAction("Move")
    tb.addAction("Crop")
    v.addWidget(tb)

    # real Krita toolbar buttons — icon-only, look them up from Krita's own
    # action map so they are the genuine icons. Visual only: _krita_preview_button
    # takes just the icon, never setDefaultAction, so clicks never trigger.
    # Missing IDs are skipped silently.
    real_tb = QToolBar(win)
    real_tb.setObjectName("realKritaButtons")
    for act_id in ("mirror_canvas", "reset_canvas_rotation",
                   "rotate_canvas_left", "rotate_canvas_right",
                   "toggle_brush_outline"):
        try:
            act = Krita.instance().action(act_id)
            if act is not None and not act.icon().isNull():
                real_tb.addWidget(_krita_preview_button(act))
        except Exception as e:
            _log(f"[chroma_kit] real action {act_id} skipped: {e}")
    v.addWidget(real_tb)

    # dock widget with title + buttons, standing in for a docker.
    # Narrow (fixed width) so it reads like Krita's side dockers, not a wide pane.
    dock = QDockWidget("Layers", win)
    dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
    dock.setFixedWidth(190)
    dw_inner = QWidget()
    dl = QVBoxLayout(dw_inner)
    dl.setContentsMargins(4, 4, 4, 4)
    dock.setWidget(dw_inner)
    v.addWidget(dock)

    # a list inside the dock so item-view selectors show
    lst = QListWidget(dock)
    for i in range(5):
        lst.addItem(QListWidgetItem(f"Layer {i + 1}"))
    lst.setCurrentRow(1)
    dl.addWidget(lst)

    # buttons in every state the themes style
    btn_row = QHBoxLayout()
    b_normal = QPushButton("Normal")
    b_checked = QPushButton("Checked")
    b_checked.setCheckable(True)
    b_checked.setChecked(True)
    b_default = QPushButton("Default")
    b_default.setDefault(True)
    b_disabled = QPushButton("Disabled")
    b_disabled.setEnabled(False)
    for b in (b_normal, b_checked, b_default, b_disabled):
        btn_row.addWidget(b)
    v.addLayout(btn_row)

    # inputs
    in_row = QHBoxLayout()
    le = QLineEdit()
    le.setText("1024")
    le.setPlaceholderText("value")
    sb = QSpinBox()
    sb.setValue(42)
    cb = QComboBox()
    cb.addItems(["Normal", "Multiply", "Screen"])
    in_row.addWidget(le)
    in_row.addWidget(sb)
    in_row.addWidget(cb)
    v.addLayout(in_row)

    # checkboxes / radio -> replaced with REAL Krita checkable toolbar actions.
    # The generic "Enabled / Checked / Radio" row looked off because Krita
    # never shows plain standalone checkboxes in toolbars; these are the actual
    # toggles you see (layer visibility, wrap-around, brush outline), rendered
    # as checkable QToolButtons so their checked/hover styling shows for real.
    # Visual only — never triggers the underlying action.
    real_toggles = QToolBar(win)
    real_toggles.setObjectName("realKritaToggles")
    for act_id in ("toggle_layer_visibility", "wrap_around_mode",
                   "toggle_brush_outline"):
        try:
            act = Krita.instance().action(act_id)
            if act is not None:
                real_toggles.addWidget(_krita_preview_button(act, checked=True))
        except Exception as e:
            _log(f"[chroma_kit] toggle action {act_id} skipped: {e}")
    # one unchecked so the unchecked state shows too
    try:
        act = Krita.instance().action("mirror_canvas")
        if act is not None:
            real_toggles.addWidget(_krita_preview_button(act, checked=False))
    except Exception as e:
        _log(f"[chroma_kit] toggle action mirror_canvas skipped: {e}")
    v.addWidget(real_toggles)

    # tabs with a selected tab
    tabs = QTabWidget()
    t1 = QWidget()
    t2 = QWidget()
    tabs.addTab(t1, "Brush")
    tabs.addTab(t2, "Color")
    tabs.setCurrentIndex(0)
    v.addWidget(tabs)

    # group box
    gb = QGroupBox("Settings")
    gbl = QVBoxLayout(gb)
    gbl.addWidget(QSlider(Qt.Horizontal))
    v.addWidget(gb)

    # slider + progress
    v.addWidget(QSlider(Qt.Horizontal))
    pb = QProgressBar()
    pb.setValue(60)
    v.addWidget(pb)

    # status bar
    win.statusBar().showMessage("Ready  •  1920 x 1080")

    v.addStretch(1)
    return win


def _preset_group(name, colors):
    """Group label for a preset by its accent hue, so the picker can space
    themes into color families. Falls back to 'Neutral' for near-grey."""
    import colorsys
    a = colors.get("accent", "#888888")
    try:
        h = a.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
        hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    except Exception:
        return "Neutral"
    if sat < 0.12:
        return "Neutral"
    deg = hue * 360
    if deg < 15 or deg >= 345:
        return "Red"
    if deg < 45:
        return "Orange"
    if deg < 70:
        return "Yellow"
    if deg < 160:
        return "Green"
    if deg < 255:
        return "Blue"          # cyan + azure + true blue together
    if deg < 290:
        return "Violet"        # violet + magenta together
    return "Magenta"


def _grouped_names(presets):
    """Return presets as an ordered list of (group_label, [names]) families,
    ordered by hue so the picker reads red -> ... -> neutral -> abstract.
    Names inside a family stay alphabetical. A few presets are pinned to a
    family by hand where the hue alone would split them oddly."""
    import colorsys
    # Hand-pinned families (override the hue guess). Everything else is
    # auto-grouped by accent hue.
    PINNED = {
        "Magenta": "Violet",       # keep with Lumen + Vivid, tidier
        "Neon Halo": "Violet",     # hot magenta — same family as Magenta/Vivid
        "Rainbow Glow": "Abstract",  # meme theme, banished to the bottom
        "Capsule": "Abstract",      # abstract by shape, not color
        "Branded Bronze": "Abstract",  # tiled bronze banding + double borders + inverted selection
        "Static": "Abstract",       # deliberately clashing axes, messy energy
        "Interference": "Abstract",  # Static's clashing axes in new colors
        "Moire": "Abstract",         # reflect-mode interference banding, op-art
    }
    # Terminal (green) and Jumbo (orange) are kept but NOT pinned — they sort
    # into their natural color families by hue.
    order = ["Red", "Orange", "Yellow", "Green", "Blue", "Violet",
             "Magenta", "Neutral", "Abstract"]
    buckets = {}
    for n in presets:
        group = PINNED.get(n) or _preset_group(n, presets[n])
        buckets.setdefault(group, []).append(n)
    families = []
    for g in order:
        if g in buckets:
            families.append((g, sorted(buckets[g])))
    # any unexpected group lands at the end rather than vanishing
    for g in sorted(buckets):
        if g not in order:
            families.append((g, sorted(buckets[g])))
    return families


class ChromaKitExtension(Extension):
    """Extension that applies wine red QSS to the Krita UI."""

    def __init__(self, parent):
        super().__init__(parent)
        self._texture_overlays = {}
        _log("[chroma_kit] DarkRedOutlineExtension.__init__ done")

    def setup(self):
        _log("[chroma_kit] setup() CALLED")
        print("[chroma_kit] setup() CALLED", flush=True)
        self._apply_qss()

    def createActions(self, window):
        """Create menu actions for the plugin."""
        # Load a preset — its label shows the active theme so you can see what
        # you're running without opening the picker.
        self._load_action = window.createAction(
            "dark_red_load_preset",
            "Chroma Kit: Load Theme",
            "tools/settings",
        )
        self._load_action.triggered.connect(self._load_preset)

        # Re-apply QSS
        action = window.createAction(
            "dark_red_reapply",
            "Chroma Kit: Re-apply Theme",
            "tools/settings",
        )
        action.triggered.connect(self._apply_qss)

        self._refresh_menu_label()

    def _refresh_menu_label(self):
        """Update the Load Theme menu item to show the active theme."""
        try:
            if getattr(self, "_load_action", None) is not None:
                self._load_action.setText(
                    f"Chroma Kit: {_colors.get('name', 'Unknown')} (change theme)")
        except Exception as e:
            _log(f"[chroma_kit] menu label refresh failed: {e}")

    def _current_label(self):
        """The active theme name, for the menu status line."""
        return _colors.get("name", "Unknown")

    def _apply_qss(self):
        global _colors
        try:
            app = QApplication.instance()
            if app is None:
                _log("[chroma_kit] QApplication.instance() is None — skip")
                return

            if _colors.get("name") == "No Preset":
                # Clear our stylesheet entirely so Krita uses its own theme.
                app.setStyleSheet("")
                self._update_texture()
                _log("[chroma_kit] QSS CLEARED — Krita default theme")
                print("[chroma_kit] QSS CLEARED — Krita default theme", flush=True)
                return

            qss = build_qss_for(_colors)
            app.setStyleSheet(qss)
            self._enlarge_toolbar_icons()
            self._update_texture()
            _log(f"[chroma_kit] QSS APPLIED — {_colors.get('name', 'default')}")
            print(f"[chroma_kit] QSS APPLIED — {_colors.get('name', 'default')}", flush=True)
        except Exception as e:
            _log(f"[chroma_kit] QSS apply FAILED: {e}")
            traceback.print_exc(file=sys.stderr)

    def _enlarge_toolbar_icons(self):
        """QSS cannot resize Krita's toolbar action icons (undo/redo/etc.) —
        icon-size and qproperty-iconSize only affect icons the stylesheet
        itself provides. The real lever is QToolBar.setIconSize(), so we walk
        the main window's toolbars and bump them. This is why the newer presets
        had tiny undo/redo icons: no preset-level QSS can fix it."""
        try:
            win = Krita.instance().activeWindow()
            if win is None:
                return
            qmw = win.qwindow()
            if qmw is None:
                return
            target = QSize(22, 22)
            for tb in qmw.findChildren(QToolBar):
                # only bump if currently smaller, so we never shrink a toolbar
                # the user (or Krita) deliberately made large
                try:
                    if tb.iconSize().width() < target.width():
                        tb.setIconSize(target)
                except Exception:
                    pass
        except Exception as e:
            _log(f"[chroma_kit] toolbar icon resize failed: {e}")

    def _update_texture(self):
        """Texture overlay support removed. The window-sized overlay caused real
        canvas lag and no preset ships a texture block. Now a no-op that also
        tears down any overlay left over from an older build, so nothing stale
        survives. Zero idle cost by design."""
        try:
            for key in list(self._texture_overlays.keys()):
                ov = self._texture_overlays.pop(key)
                try:
                    ov.hide()
                    ov.setParent(None)
                    ov.deleteLater()
                except Exception:
                    pass
        except Exception as e:
            _log(f"[chroma_kit] texture teardown FAILED: {e}")
            traceback.print_exc(file=sys.stderr)


    def _load_preset(self):
        """Rich theme picker: name + one-line description + color swatches,
        marks the currently active theme, and persists the choice."""
        global _colors, _presets
        _presets = load_presets()
        if not _presets:
            QMessageBox.warning(None, "Chroma Kit", "No themes found.")
            return

        current = _colors.get("name", "")
        dlg = QDialog(None)
        dlg.setWindowTitle("Chroma Kit — Load Theme")
        dlg.resize(820, 560)
        root = QVBoxLayout(dlg)

        # current-theme banner
        banner = QLabel(f"Active theme:  <b>{current}</b>")
        root.addWidget(banner)

        # two columns: picker (left) + live preview (right)
        cols = QHBoxLayout()
        left = QVBoxLayout()

        lst = QListWidget()
        # "No Preset" first — disables our styling, restores Krita's own theme.
        none_item = QListWidgetItem("No Preset" + ("   (active)" if current == "No Preset" else ""))
        none_item.setToolTip("Turn off Chroma Kit and use Krita's default theme.")
        lst.addItem(none_item)

        # Grouped by color family (hue), spaced with a separator row between
        # families. We remember the row of every real preset so selection and
        # _bare_name() still work despite the separator rows in between.
        families = _grouped_names(_presets)
        row_of = {}          # preset name -> list row
        first_preset_row = None
        for fam_index, (group, members) in enumerate(families):
            if fam_index > 0:
                sep = QListWidgetItem("")           # blank spacer between families
                sep.setFlags(Qt.NoItemFlags)          # not selectable / not hoverable
                lst.addItem(sep)
            for n in members:
                p = _presets[n]
                desc = DESCRIPTIONS.get(n, "")
                suffix = "   (active)" if n == current else ""
                item = QListWidgetItem(f"{n}{suffix}")
                if desc:
                    item.setToolTip(desc)
                sw = []
                for key in ("bg", "accent", "accent_bright", "text"):
                    v = p.get(key)
                    if v:
                        sw.append(v)
                if sw:
                    item.setText(f"{n}{suffix}   " + "  ".join("▮" for _ in sw))
                    item.setForeground(QColor(p.get("accent", "#ffffff")))
                lst.addItem(item)
                row_of[n] = lst.count() - 1
                if first_preset_row is None:
                    first_preset_row = lst.count() - 1

        # select the active row
        if current == "No Preset":
            lst.setCurrentRow(0)
        elif current in row_of:
            lst.setCurrentRow(row_of[current])
        elif first_preset_row is not None:
            lst.setCurrentRow(first_preset_row)
        else:
            lst.setCurrentRow(0)
        left.addWidget(lst)

        # description readout for the highlighted theme
        desc_lbl = QTextEdit()
        desc_lbl.setReadOnly(True)
        desc_lbl.setMaximumHeight(90)

        def _bare_name():
            it = lst.currentItem()
            if it is None:
                return None
            n = it.text().split("   ")[0].strip()
            if n.endswith("(active)"):
                n = n.replace("(active)", "").strip()
            return n

        def _show_desc():
            n = _bare_name()
            if n == "No Preset":
                desc_lbl.setPlainText("Turn off Chroma Kit and use Krita's default theme.")
            else:
                desc_lbl.setPlainText(DESCRIPTIONS.get(n, "No description.") if n else "")
        lst.currentItemChanged.connect(lambda *_: (_show_desc(), _show_preview()))
        _show_desc()
        left.addWidget(desc_lbl)

        # buttons
        btns = QHBoxLayout()
        btns.addStretch(1)
        ok_btn = QPushButton("Load")
        cancel_btn = QPushButton("Cancel")
        ok_btn.setDefault(True)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        left.addLayout(btns)
        cols.addLayout(left, 1)

        # live preview panel on the right, with a "Preview Preset" header that
        # shows which theme is currently being previewed.
        right = QVBoxLayout()
        preview_hdr = QHBoxLayout()
        preview_title = QLabel("Preview Preset")
        preview_title.setStyleSheet("font-weight: bold;")
        preview_name = QLabel("")
        preview_hdr.addWidget(preview_title)
        preview_hdr.addStretch(1)
        preview_hdr.addWidget(preview_name)
        right.addLayout(preview_hdr)
        preview = build_preview_panel(dlg)
        right.addWidget(preview, 1)
        cols.addLayout(right, 2)
        root.addLayout(cols)

        def _show_preview():
            n = _bare_name()
            if n == "No Preset":
                preview_name.setText("No Preset")
                preview.setStyleSheet("")  # preview shows Krita default look
            elif n and n in _presets:
                preview_name.setText(n)
                try:
                    preview.setStyleSheet(build_qss_for(_presets[n]))
                except Exception as e:
                    _log(f"[chroma_kit] preview build failed for {n}: {e}")

        _show_preview()

        ok_btn.clicked.connect(dlg.accept)
        cancel_btn.clicked.connect(dlg.reject)

        if dlg.exec_() != QDialog.Accepted:
            return
        n = _bare_name()
        if not n:
            return
        if n == "No Preset":
            _colors = {"name": "No Preset"}
            _save_state(NO_PRESET)
            _log("[chroma_kit] no preset selected")
            self._apply_qss()
            self._update_texture()
            self._refresh_menu_label()
        elif n in _presets:
            _colors = dict(_presets[n])
            _save_state(n)
            _log(f"[chroma_kit] loaded '{n}'")
            self._apply_qss()
            self._update_texture()
            self._refresh_menu_label()


# Register extension with Kila
_log("[chroma_kit] Registering extension via addExtension...")
try:
    ext = ChromaKitExtension(parent=Krita.instance())
    Krita.instance().addExtension(ext)
    _log("[chroma_kit] addExtension() called OK — module END")
    print("[chroma_kit] addExtension() called OK", flush=True)
except Exception as e:
    _log(f"[chroma_kit] addExtension FAILED: {e}")
    traceback.print_exc(file=sys.stderr)
    raise

_log("[chroma_kit] MODULE IMPORT COMPLETE")
print("[chroma_kit] MODULE IMPORT COMPLETE", flush=True)
