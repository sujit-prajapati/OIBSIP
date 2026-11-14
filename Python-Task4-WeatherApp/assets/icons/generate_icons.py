"""
Professional Weather Icon Generator.
Generates vibrant, colorful 64x64 RGBA PNG weather icons for Tkinter.
Pure Python standard library (struct + zlib) with zero external dependencies.
"""

import os
import struct
import zlib
import math


def write_png(width: int, height: int, pixels: list, filename: str):
    """Write an RGBA image matrix to a PNG file."""
    raw_data = bytearray()
    for row in pixels:
        raw_data.append(0)  # filter type 0 (None)
        for r, g, b, a in row:
            raw_data.extend((r, g, b, a))

    compressed = zlib.compress(bytes(raw_data))

    def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    png_bytes = bytearray(b"\x89PNG\r\n\x1a\n")
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png_bytes.extend(make_chunk(b"IHDR", ihdr_data))
    png_bytes.extend(make_chunk(b"IDAT", compressed))
    png_bytes.extend(make_chunk(b"IEND", b""))

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(png_bytes)


def create_empty(w=64, h=64):
    return [[(0, 0, 0, 0) for _ in range(w)] for _ in range(h)]


def draw_circle(pixels, cx, cy, r, color):
    w = len(pixels[0])
    h = len(pixels)
    for y in range(max(0, int(cy - r - 1)), min(h, int(cy + r + 2))):
        for x in range(max(0, int(cx - r - 1)), min(w, int(cx + r + 2))):
            d = math.hypot(x - cx, y - cy)
            if d <= r:
                pixels[y][x] = color
            elif d <= r + 1.0:
                alpha = int(color[3] * (r + 1.0 - d))
                if alpha > pixels[y][x][3]:
                    pixels[y][x] = (color[0], color[1], color[2], alpha)


def draw_sun(pixels, cx=32, cy=32, r=16):
    # Sun rays
    num_rays = 8
    for i in range(num_rays):
        angle = i * (2 * math.pi / num_rays)
        for dist in range(int(r + 3), int(r + 9)):
            rx = int(cx + dist * math.cos(angle))
            ry = int(cy + dist * math.sin(angle))
            if 0 <= rx < 64 and 0 <= ry < 64:
                pixels[ry][rx] = (255, 170, 0, 255)
                # thicken ray
                for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if 0 <= rx + ox < 64 and 0 <= ry + oy < 64:
                        pixels[ry + oy][rx + ox] = (255, 190, 20, 200)

    # Sun core (vibrant golden yellow/orange)
    draw_circle(pixels, cx, cy, r, (255, 185, 0, 255))
    draw_circle(pixels, cx, cy, r - 3, (255, 215, 0, 255))


def draw_moon(pixels, cx=32, cy=30, r=17):
    # Crescent moon
    for y in range(0, 64):
        for x in range(0, 64):
            d1 = math.hypot(x - cx, y - cy)
            d2 = math.hypot(x - (cx + 8), y - (cy - 6))
            if d1 <= r and d2 > r - 2:
                pixels[y][x] = (255, 215, 64, 255)
            elif d1 <= r + 0.8 and d2 > r - 2:
                pixels[y][x] = (255, 200, 40, 180)


def draw_cloud(pixels, cx=32, cy=36, color=(220, 230, 242, 255)):
    # Cloud base puffs
    draw_circle(pixels, cx - 12, cy + 4, 11, color)
    draw_circle(pixels, cx + 12, cy + 4, 11, color)
    draw_circle(pixels, cx - 2, cy - 4, 15, color)
    draw_circle(pixels, cx + 9, cy - 2, 12, color)
    # Bottom flat fill
    for y in range(int(cy + 4), int(cy + 15)):
        for x in range(int(cx - 20), int(cx + 21)):
            if 0 <= x < 64 and 0 <= y < 64:
                pixels[y][x] = color


def draw_rain_drops(pixels, cx=32, start_y=46, heavy=False):
    drop_color = (56, 149, 255, 255)
    cols = [cx - 14, cx - 7, cx, cx + 7, cx + 14] if heavy else [cx - 10, cx, cx + 10]
    for c in cols:
        for y_off in range(0, 10 if heavy else 7):
            y = start_y + y_off
            x = c - int(y_off * 0.4)
            if 0 <= x < 64 and 0 <= y < 64:
                pixels[y][x] = drop_color
                if heavy and 0 <= x + 1 < 64:
                    pixels[y][x + 1] = (30, 120, 240, 255)


def draw_lightning(pixels, cx=32, cy=42):
    bolt_color = (255, 220, 0, 255)
    pts = [
        (cx - 2, cy), (cx + 6, cy), (cx, cy + 8),
        (cx + 5, cy + 8), (cx - 4, cy + 18), (cx - 1, cy + 9),
        (cx - 5, cy + 9)
    ]
    for y in range(cy, cy + 19):
        for x in range(cx - 6, cx + 8):
            if cy <= y < cy + 8 and cx - 3 <= x <= cx + 4:
                pixels[y][x] = bolt_color
            elif cy + 8 <= y < cy + 18 and cx - 5 <= x <= cx + 3:
                pixels[y][x] = bolt_color


def draw_snow(pixels, cx=32, start_y=46):
    snow_color = (130, 205, 255, 255)
    for c in [cx - 11, cx, cx + 11]:
        for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (0, 0)]:
            x = c + ox
            y = start_y + 4 + oy
            if 0 <= x < 64 and 0 <= y < 64:
                pixels[y][x] = snow_color


def draw_mist(pixels, cx=32, cy=34):
    mist_color = (180, 200, 218, 230)
    for bar_y in [cy - 8, cy - 1, cy + 6, cy + 13]:
        for x in range(cx - 20, cx + 21):
            if 0 <= x < 64 and 0 <= bar_y < 64:
                pixels[bar_y][x] = mist_color
                if bar_y + 1 < 64:
                    pixels[bar_y + 1][x] = mist_color


def generate_all_icons(output_dir: str):
    """Generate all vibrant weather icons."""
    os.makedirs(output_dir, exist_ok=True)

    # 1. Clear Day (01d)
    img = create_empty()
    draw_sun(img, 32, 32, 17)
    write_png(64, 64, img, os.path.join(output_dir, "01d.png"))

    # 2. Clear Night (01n)
    img = create_empty()
    draw_moon(img, 32, 30, 17)
    write_png(64, 64, img, os.path.join(output_dir, "01n.png"))

    # 3. Few Clouds Day (02d)
    img = create_empty()
    draw_sun(img, 42, 22, 13)
    draw_cloud(img, 28, 38, (240, 245, 255, 255))
    write_png(64, 64, img, os.path.join(output_dir, "02d.png"))

    # 4. Few Clouds Night (02n)
    img = create_empty()
    draw_moon(img, 42, 22, 13)
    draw_cloud(img, 28, 38, (210, 225, 240, 255))
    write_png(64, 64, img, os.path.join(output_dir, "02n.png"))

    # 5. Scattered / Broken Clouds (03d, 03n, 04d, 04n)
    img = create_empty()
    draw_cloud(img, 38, 28, (180, 200, 220, 240))
    draw_cloud(img, 26, 38, (235, 245, 255, 255))
    write_png(64, 64, img, os.path.join(output_dir, "03d.png"))
    write_png(64, 64, img, os.path.join(output_dir, "04d.png"))

    # 6. Shower Rain / Drizzle (09d)
    img = create_empty()
    draw_cloud(img, 32, 28, (160, 185, 210, 255))
    draw_rain_drops(img, 32, 44, heavy=False)
    write_png(64, 64, img, os.path.join(output_dir, "09d.png"))

    # 7. Rain (10d)
    img = create_empty()
    draw_sun(img, 42, 20, 11)
    draw_cloud(img, 30, 30, (170, 195, 220, 255))
    draw_rain_drops(img, 30, 46, heavy=True)
    write_png(64, 64, img, os.path.join(output_dir, "10d.png"))

    # 8. Thunderstorm (11d)
    img = create_empty()
    draw_cloud(img, 32, 26, (90, 110, 140, 255))
    draw_lightning(img, 32, 40)
    write_png(64, 64, img, os.path.join(output_dir, "11d.png"))

    # 9. Snow (13d)
    img = create_empty()
    draw_cloud(img, 32, 28, (200, 225, 245, 255))
    draw_snow(img, 32, 44)
    write_png(64, 64, img, os.path.join(output_dir, "13d.png"))

    # 10. Mist / Fog (50d)
    img = create_empty()
    draw_mist(img, 32, 32)
    write_png(64, 64, img, os.path.join(output_dir, "50d.png"))

    print(f"Generated complete weather icon set in: {output_dir}")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
    generate_all_icons(os.path.abspath(out))

