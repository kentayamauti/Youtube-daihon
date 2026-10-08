#!/usr/bin/env python3
"""YouTubeサムネイルに文字を入れる。

型は2つ:
  jouge : 上下に横書き（牛丼の型）
  tate  : 右と左に縦書き（豚バラの型）

例:
  python3 make_thumbnail.py jouge 写真.jpg --top "牛丼屋はもういかない" --bottom "この作り方覚えて" -o out.jpg
  python3 make_thumbnail.py tate 写真.jpg --right "パックの" --right "まま焼け" \
      --left "もうコンビニ" --left "行かない" -o out.jpg
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1280, 720
HERE = Path(__file__).resolve().parent

# 太いフォントを fonts/ に置けばそれを優先（例: NotoSansJP-Black.ttf）
FONT_CANDIDATES = sorted((HERE / "fonts").glob("*.[ot]t[fc]")) + [
    Path("/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"),
    Path("/usr/share/fonts/truetype/fonts-japanese-gothic.ttf"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
]

# 縦書きで90度回すもの
ROTATE = set("ー－-〜~…‥―（）()「」『』【】＝=")
# 縦書きで右上に寄せる小さい字
SMALL = set("っゃゅょぁぃぅぇぉゎッャュョァィゥェォヮヵヶ")
PUNCT = set("、。，．,.")


def pick_font(path):
    if path:
        return Path(path)
    for p in FONT_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit("日本語フォントが見つかりません。fonts/ に .ttf/.otf を置いてください。")


class Style:
    def __init__(self, font_path, fill, outline, outline_ratio, bold_ratio):
        self.font_path = font_path
        self.fill = fill
        self.outline = outline
        self.outline_ratio = outline_ratio  # 文字サイズに対する黒フチの太さ
        self.bold_ratio = bold_ratio        # 細いフォントを太らせる量

    def font(self, size):
        return ImageFont.truetype(str(self.font_path), size)

    def widths(self, size):
        bold = max(0, round(size * self.bold_ratio))
        out = max(2, round(size * self.outline_ratio))
        return bold, bold + out

    def draw(self, img, xy, text, size, anchor="la"):
        """黒フチ → 白文字（太らせ込み）の順に重ねる。"""
        d = ImageDraw.Draw(img)
        f = self.font(size)
        bold, total = self.widths(size)
        d.text(xy, text, font=f, fill=self.outline, stroke_width=total,
               stroke_fill=self.outline, anchor=anchor)
        d.text(xy, text, font=f, fill=self.fill, stroke_width=bold,
               stroke_fill=self.fill, anchor=anchor)


def load_bg(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, (W, H), Image.LANCZOS)


# ---------- 上下（横書き） ----------

def fit_horizontal(style, text, max_w, max_h):
    size = max_h
    while size > 10:
        _, total = style.widths(size)
        l, t, r, b = style.font(size).getbbox(text, stroke_width=total)
        if r - l <= max_w and b - t <= max_h:
            return size
        size -= 2
    return size


def jouge(args, style):
    img = load_bg(args.image)
    margin = int(W * 0.02)
    band_h = int(H * args.band)  # 1行ぶんの高さ
    for text, cy in ((args.top, margin + band_h / 2), (args.bottom, H - margin - band_h / 2)):
        if not text:
            continue
        size = fit_horizontal(style, text, W - margin * 2, band_h)
        style.draw(img, (W / 2, cy), text, size, anchor="mm")
    return img


# ---------- 左右（縦書き） ----------

def column_metrics(style, text, size):
    """1列の縦書きで、1文字あたりの送り幅（=size）と列幅を返す。"""
    _, total = style.widths(size)
    return size + total * 0.6, size + total * 2


def fit_vertical(style, text, max_h, max_w):
    size = max_w
    while size > 10:
        step, col_w = column_metrics(style, text, size)
        if step * len(text) <= max_h and col_w <= max_w:
            return size
        size -= 2
    return size


def draw_vertical(img, style, text, cx, top, size):
    step, _ = column_metrics(style, text, size)
    _, total = style.widths(size)
    pad = total * 2
    for i, ch in enumerate(text):
        cy = top + step * i + step / 2
        if ch in ROTATE:
            tile = Image.new("RGBA", (int(size + pad * 2),) * 2, (0, 0, 0, 0))
            style.draw(tile, (tile.width / 2, tile.height / 2), ch, size, anchor="mm")
            tile = tile.rotate(-90, resample=Image.BICUBIC)
            img.paste(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)), tile)
            continue
        dx = dy = 0
        if ch in SMALL:
            dx, dy = size * 0.10, -size * 0.10
        elif ch in PUNCT:
            dx, dy = size * 0.55, -size * 0.55
        style.draw(img, (cx + dx, cy + dy), ch, size, anchor="mm")


def tate(args, style):
    img = load_bg(args.image).convert("RGBA")
    margin = int(H * 0.025)
    max_h = H - margin * 2
    # 左右それぞれの使える幅（画面の何割か）
    side_w = W * args.side

    def place(cols, side):
        if not cols:
            return
        n = len(cols)
        slot = side_w / n
        sizes = [fit_vertical(style, t, max_h, slot) for t in cols]
        widths = [column_metrics(style, t, s)[1] for t, s in zip(cols, sizes)]
        # 列は右から左へ並べる（日本語の縦書きの読み順）
        if side == "right":
            x = W - margin
        else:
            x = margin + sum(widths)
        for t, s, w in zip(cols, sizes, widths):
            cx = x - w / 2
            step, _ = column_metrics(style, t, s)
            col_h = step * len(t)
            top = margin + (max_h - col_h) / 2 if args.center else margin
            draw_vertical(img, style, t, cx, top, s)
            x -= w

    place(args.right, "right")
    place(args.left, "left")
    return img.convert("RGB")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)

    def common(sp):
        sp.add_argument("image", help="元の写真")
        sp.add_argument("-o", "--out", required=True, help="出力ファイル（.jpg / .png）")
        sp.add_argument("--font", help="使うフォント（省略時は fonts/ → IPAゴシック）")
        sp.add_argument("--fill", default="#FFFFFF", help="文字の色")
        sp.add_argument("--outline", default="#000000", help="フチの色")
        sp.add_argument("--outline-ratio", type=float, default=0.14, help="フチの太さ（文字サイズ比）")
        sp.add_argument("--bold", type=float, default=0.035, help="文字を太らせる量（太いフォントなら0）")

    a = sub.add_parser("jouge", help="上下に横書き")
    common(a)
    a.add_argument("--top", default="", help="上の文字")
    a.add_argument("--bottom", default="", help="下の文字")
    a.add_argument("--band", type=float, default=0.22, help="1行の高さ（画面比）")

    b = sub.add_parser("tate", help="右と左に縦書き")
    common(b)
    b.add_argument("--right", action="append", default=[], help="右の列（右から順に、複数回指定可）")
    b.add_argument("--left", action="append", default=[], help="左の列（右から順に、複数回指定可）")
    b.add_argument("--side", type=float, default=0.27, help="片側で使う幅（画面比）")
    b.add_argument("--center", action="store_true", help="短い列を上下中央に寄せる（既定は上詰め）")

    args = p.parse_args()
    style = Style(pick_font(args.font), args.fill, args.outline, args.outline_ratio, args.bold)
    img = jouge(args, style) if args.mode == "jouge" else tate(args, style)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=95) if out.suffix.lower() in (".jpg", ".jpeg") else img.save(out)
    print(out)


if __name__ == "__main__":
    main()
