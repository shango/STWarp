"""Generate the STWarp app icon.

Produces assets/stwarp.ico (multi-size Windows icon) and
assets/stwarp.png (1024x1024 reference master) from a procedural
STMap-style gradient: R = x, G = (1 - y), B = 0, with rounded corners
and a soft border. The result looks like a miniature STMap tile and
is used both as the Windows executable icon and as the in-app window
icon.

Run:
    python scripts/make_icon.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
ICO_PATH = ASSETS_DIR / "stwarp.ico"
PNG_PATH = ASSETS_DIR / "stwarp.png"

# Sizes bundled into the .ico so Windows picks the right one for each surface.
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
MASTER = 1024
CORNER_RATIO = 0.20     # rounded corner radius as fraction of side
INSET_RATIO = 0.06      # padding so the tile doesn't touch the icon edges
BORDER_PX_AT_MASTER = 6


def _stmap_tile(size: int) -> Image.Image:
    """Render the classic STMap gradient as an RGBA image at `size` px.

    Convention: R = x / (W-1), G = (H-1-y) / (H-1). So the tile reads:
      top-left   -> green   (R=0, G=1)
      top-right  -> yellow  (R=1, G=1)
      bottom-left  -> black (R=0, G=0)
      bottom-right -> red   (R=1, G=0)
    """
    xs = np.linspace(0.0, 1.0, size, dtype=np.float32)
    ys = np.linspace(1.0, 0.0, size, dtype=np.float32)
    r = np.broadcast_to(xs[None, :], (size, size))
    g = np.broadcast_to(ys[:, None], (size, size))
    b = np.zeros_like(r)
    a = np.ones_like(r)
    rgba = np.stack([r, g, b, a], axis=-1)
    rgba = (rgba * 255.0 + 0.5).clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def _rounded_mask(size: int, radius: int) -> Image.Image:
    """Return a single-channel L-mode mask with a rounded square."""
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return m


def _render_master() -> Image.Image:
    """Render the 1024x1024 master icon with shadow + border."""
    size = MASTER
    inset = int(size * INSET_RATIO)
    tile_size = size - 2 * inset
    radius = int(tile_size * CORNER_RATIO)

    tile = _stmap_tile(tile_size)
    mask = _rounded_mask(tile_size, radius)
    tile.putalpha(mask)

    # Thin light border for crisp edges on dark/light backgrounds alike.
    border = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
    bd = ImageDraw.Draw(border)
    bd.rounded_rectangle(
        (0, 0, tile_size - 1, tile_size - 1),
        radius=radius,
        outline=(255, 255, 255, 55),
        width=BORDER_PX_AT_MASTER,
    )

    # Soft drop shadow behind the tile.
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        (inset + 4, inset + 16, size - inset - 1 + 4, size - inset - 1 + 16),
        radius=radius,
        fill=(0, 0, 0, 140),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=18))

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(tile, dest=(inset, inset))
    canvas.alpha_composite(border, dest=(inset, inset))
    return canvas


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    master = _render_master()
    master.save(PNG_PATH, format="PNG")
    print(f"Wrote {PNG_PATH}")

    master.save(
        ICO_PATH,
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
    )
    print(f"Wrote {ICO_PATH} with sizes {ICO_SIZES}")


if __name__ == "__main__":
    main()
