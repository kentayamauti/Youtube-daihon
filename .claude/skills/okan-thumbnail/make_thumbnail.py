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

# 型ごとのフォント（参考サムネに合わせる）
#   上下 → 極太ゴシック（Noto Sans JP Black）
#   縦書き → 極太明朝（Noto Serif JP Black）
FONTS = {
    "jouge": HERE / "fonts" / "NotoSansJP-Black.ttf",
    "tate": HERE / "fonts" / "NotoSerifJP-Black.ttf",
}
# 型ごとの黒フチの太さ（文字サイズ比）。縦書きの参考はフチがかなり太い
OUTLINE = {"jouge": 0.14, "tate": 0.18}

# 縦書きで90度回すもの
ROTATE = set("ー－-〜~…‥―（）()「」『』【】＝=")
# 縦書きで右上に寄せる小さい字
SMALL = set("っゃゅょぁぃぅぇぉゎッャュョァィゥェォヮヵヶ")
PUNCT = set("、。，．,.")


def pick_font(path, mode):
    p = Path(path) if path else FONTS[mode]
    if not p.exists():
        raise SystemExit(f"フォントが見つかりません: {p}")
    return p


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

    def draw(self, img, xy, text, size, anchor="la", part="both"):
        """黒フチ → 白文字（太らせ込み）の順に重ねる。part で片方だけも描ける。"""
        d = ImageDraw.Draw(img)
        f = self.font(size)
        bold, total = self.widths(size)
        if part in ("both", "outline"):
            d.text(xy, text, font=f, fill=self.outline, stroke_width=total,
                   stroke_fill=self.outline, anchor=anchor)
        if part in ("both", "fill"):
            d.text(xy, text, font=f, fill=self.fill, stroke_width=bold,
                   stroke_fill=self.fill, anchor=anchor)


def load_bg(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, (W, H), Image.LANCZOS)


# ---------- 共通：大きく描いて切り抜き、枠いっぱいに縮める ----------

BASE = 240        # 下描きの文字サイズ（大きく描いてから縮めるときれい）
MARGIN = 6        # 画面の端からのすき間（px）
MAX_STRETCH = 1.3 # 枠を埋めるために片方向へ伸ばしてよい倍率


def crop_alpha(layer):
    return layer.crop(layer.getchannel("A").getbbox())


def fit_into(layer, box_w, box_h, stretch="x"):
    """縦横比を保って枠いっぱいに縮め、足りない方向は MAX_STRETCH まで伸ばす。"""
    k = min(box_w / layer.width, box_h / layer.height)
    w, h = layer.width * k, layer.height * k
    if stretch == "x":
        w = min(box_w, w * MAX_STRETCH)
    elif stretch == "y":
        h = min(box_h, h * MAX_STRETCH)
    return layer.resize((max(1, round(w)), max(1, round(h))), Image.LANCZOS)


# ---------- 上下（横書き） ----------

def render_line(style, text):
    f = style.font(BASE)
    _, total = style.widths(BASE)
    l, t, r, b = f.getbbox(text, stroke_width=total)
    layer = Image.new("RGBA", (r - l + 20, b - t + 20), (0, 0, 0, 0))
    style.draw(layer, (10 - l, 10 - t), text, BASE)
    return crop_alpha(layer)


def jouge(args, style):
    img = load_bg(args.image).convert("RGBA")
    box_w = W - MARGIN * 2
    box_h = int(H * args.band)
    for text, where in ((args.top, "top"), (args.bottom, "bottom")):
        if not text:
            continue
        line = fit_into(render_line(style, text), box_w, box_h, stretch="x")
        x = (W - line.width) // 2
        y = MARGIN if where == "top" else H - MARGIN - line.height
        img.alpha_composite(line, (x, y))
    return img.convert("RGB")


# ---------- 左右（縦書き） ----------

def render_column(style, text, gap=0.0):
    """縦書き1列を描く。gap は文字と文字の間に足すすき間（下描きのpx）。"""
    size = BASE
    _, total = style.widths(size)
    step = size + total * 0.6 + gap
    cell = int(size + total * 2 + 20)
    height = int(step * len(text) + total * 2 + 20)
    layer = Image.new("RGBA", (cell, height), (0, 0, 0, 0))
    # フチを全部描いてから白を全部描く（隣の字のフチが白に被らないように）
    for part in ("outline", "fill"):
        for i, ch in enumerate(text):
            cx, cy = cell / 2, total + 10 + step * i + step / 2
            if ch in ROTATE:
                tile = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
                style.draw(tile, (cell / 2, cell / 2), ch, size, anchor="mm", part=part)
                tile = tile.rotate(-90, resample=Image.BICUBIC)
                layer.alpha_composite(tile, (0, int(cy - cell / 2)))
                continue
            dx = dy = 0
            if ch in SMALL:
                dx, dy = size * 0.10, -size * 0.10
            elif ch in PUNCT:
                dx, dy = size * 0.55, -size * 0.55
            style.draw(layer, (cx + dx, cy + dy), ch, size, anchor="mm", part=part)
    return crop_alpha(layer)


def fill_column(style, text, box_w, box_h):
    """列を枠（box_w × box_h）いっぱいにする。幅で決まって高さが余るときは字間を広げる。"""
    col = render_column(style, text)
    k = min(box_w / col.width, box_h / col.height)
    short = box_h / k - col.height
    if short > 1 and len(text) > 1:
        col = render_column(style, text, gap=short / (len(text) - 1))
    return fit_into(col, box_w, box_h, stretch="x")


def tate(args, style):
    img = load_bg(args.image).convert("RGBA")
    box_h = H - MARGIN * 2
    side_w = W * args.side - MARGIN

    def place(cols, side):
        if not cols:
            return
        # 高さいっぱいに描いたときの列の幅を出し、片側の幅に収まるよう配分する
        natural = []
        for t in cols:
            c = render_column(style, t)
            natural.append(c.width * box_h / c.height)
        k = side_w / sum(natural)
        widths = [w * k for w in natural]
        rendered = [fill_column(style, t, w, box_h) for t, w in zip(cols, widths)]
        # 列は右から左へ並べる（日本語の縦書きの読み順）
        x = W - MARGIN if side == "right" else MARGIN + sum(c.width for c in rendered)
        for c in rendered:
            x -= c.width
            img.alpha_composite(c, (int(x), MARGIN + (box_h - c.height) // 2))

    place(args.right, "right")
    place(args.left, "left")
    return img.convert("RGB")


def save_for_youtube(img, out):
    """YouTubeのサムネ規格：1280x720・JPEG・2MB未満。"""
    out = out.with_suffix(".jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    img = img.convert("RGB")
    if img.size != (W, H):
        img = img.resize((W, H), Image.LANCZOS)
    for q in (95, 90, 85, 80, 75, 70):
        img.save(out, "JPEG", quality=q, optimize=True)
        if out.stat().st_size < 2 * 1024 * 1024:
            break
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="mode", required=True)

    def common(sp):
        sp.add_argument("image", help="元の写真")
        sp.add_argument("-o", "--out", required=True, help="出力ファイル（YouTube用に 1280x720 の .jpg・2MB未満で書き出す）")
        sp.add_argument("--font", help="使うフォント（省略時は型ごとの既定。上下=ゴシック、縦書き=明朝）")
        sp.add_argument("--fill", default="#FFFFFF", help="文字の色")
        sp.add_argument("--outline", default="#000000", help="フチの色")
        sp.add_argument("--outline-ratio", type=float, help="フチの太さ（文字サイズ比。既定 上下0.14／縦書き0.18）")
        sp.add_argument("--bold", type=float, default=0.0, help="文字をさらに太らせる量（細いフォントを使うとき 0.03 くらい）")

    a = sub.add_parser("jouge", help="上下に横書き")
    common(a)
    a.add_argument("--top", default="", help="上の文字")
    a.add_argument("--bottom", default="", help="下の文字")
    a.add_argument("--band", type=float, default=0.30, help="1行の高さの上限（画面比）")

    b = sub.add_parser("tate", help="右と左に縦書き")
    common(b)
    b.add_argument("--right", action="append", default=[], help="右の列（右から順に、複数回指定可）")
    b.add_argument("--left", action="append", default=[], help="左の列（右から順に、複数回指定可）")
    b.add_argument("--side", type=float, default=0.30, help="片側で使う幅（画面比）")

    args = p.parse_args()
    outline_ratio = args.outline_ratio if args.outline_ratio is not None else OUTLINE[args.mode]
    style = Style(pick_font(args.font, args.mode), args.fill, args.outline, outline_ratio, args.bold)
    img = jouge(args, style) if args.mode == "jouge" else tate(args, style)
    print(save_for_youtube(img, Path(args.out)))

if __name__ == "__main__":
    main()
