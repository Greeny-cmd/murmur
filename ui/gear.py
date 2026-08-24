"""
Material Design gear icon — rendered from the official Material "settings" SVG.

The Unicode gear (\u2699) renders as a thin strip in some Windows fonts, and a
hand-drawn QPainter gear looked off. This uses the Google Material Design
"settings" glyph for a crisp, modern icon at any size.
"""

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QPixmap, QIcon, QImage, QPainter
from PyQt6.QtSvg import QSvgRenderer

# Official Material Design "settings" icon path (Apache 2.0 / CC BY 4.0).
_MATERIAL_GEAR_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24">
  <path fill="{color}" d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58
    c0.18-0.14,0.23-0.41,0.12-0.61l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96
    c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41h-3.84
    c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33
    c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58
    C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58c-0.18,0.14-0.23,0.41-0.12,0.61
    l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54
    c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54
    c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32
    c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94zM12,15.6c-1.98,0-3.6-1.62-3.6-3.6
    s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
</svg>
"""


def make_gear_pixmap(size: int = 36, color=(95, 99, 104)) -> QPixmap:
    """Render the Material gear at the requested size and color."""
    hex_color = "#%02X%02X%02X" % tuple(color)
    svg_str = _MATERIAL_GEAR_SVG.format(size=int(size * 4), color=hex_color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    renderer.render(p)
    p.end()

    pix = QPixmap.fromImage(img)
    return pix


def make_gear_icon(size: int = 36, color=(95, 99, 104)) -> QIcon:
    return QIcon(make_gear_pixmap(size, color))