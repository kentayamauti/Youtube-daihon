"""サムネを高品質に作る道具（絵はGemini、文字はテンプレート）。

やり方（調べた結果：絵と文字を分ける、キャラは見本画像で固定、3案を比べる）
  1. gen   : Gemini の画像AIで「文字なし」の絵を作る。キャラの見本画像を渡して、毎回同じ顔にする
  2. make  : お手本型のひな形（assets/thumb_templates/paurach_type.html）に文字を載せて 1280×720 で書き出す
  3. check : 作った案と、競合のサムネを並べ、スマホで見える小さいサイズでも読めるか確かめる一覧を作る

使い方:
  python3 -I tools/thumbnail.py gen  <出力.png> "絵の説明（英語推奨）" [--ref キャラ見本.png ...]
  python3 -I tools/thumbnail.py make <出力.jpg> --band "帯の文字" [--label 小見出し] [--bg 背景] [--char キャラ透過PNG] [--style purple|redblack]
  python3 -I tools/thumbnail.py check <一覧.png> 案1.jpg 案2.jpg ... [--compare 競合のthumbnail.jpg ...]

帯の文字を2行にするときは "上の行|下の行"。
"""
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(KIT, "assets", "thumb_templates", "paurach_type.html")
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
IMAGE_MODELS = ["gemini-3-pro-image", "gemini-3.1-flash-image", "nano-banana-pro-preview", "gemini-2.5-flash-image"]

NO_TEXT = ("Do not draw any letters, words, logos, watermarks or captions anywhere in the image. "
           "Leave the bottom third of the frame simple, because large text will be placed there later.")


def gen(out, prompt, refs=()):
    parts = []
    for r in refs:  # キャラの見本（同じ顔・服・色で描かせる）
        mime = "image/png" if r.lower().endswith(".png") else "image/jpeg"
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(open(r, "rb").read()).decode()}})
    if refs:
        prompt = "Keep the character exactly consistent with the reference image(s): same face, hair, outfit and colors. " + prompt
    parts.append({"text": prompt + " " + NO_TEXT})
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}}).encode()
    last = None
    for rnd in range(3):
        for m in IMAGE_MODELS:
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                data=body, headers={"Content-Type": "application/json"})
            try:
                r = json.loads(urllib.request.urlopen(req, timeout=300).read())
            except urllib.error.HTTPError as e:
                last = f"{m}: {e.code} {e.read()[:160].decode('utf8', 'ignore')}"
                if e.code in (429, 500, 502, 503, 504):
                    continue
                raise
            for p in r["candidates"][0]["content"]["parts"]:
                if "inlineData" in p:
                    with open(out, "wb") as f:
                        f.write(base64.b64decode(p["inlineData"]["data"]))
                    print("絵を作った", out, f"({m})")
                    return out
        time.sleep(30 * (rnd + 1))
    raise RuntimeError("Geminiで絵を作れなかった（無料枠では画像生成は使えない。課金を有効にする）: " + str(last))


def make(out, band, label="", bg=None, char=None, style="purple"):
    """ひな形をいったん作業フォルダにコピーして、画像と一緒に開いて撮る"""
    work = tempfile.mkdtemp()
    shutil.copy(TEMPLATE, os.path.join(work, "t.html"))
    for f in os.listdir(os.path.dirname(TEMPLATE)):
        if f.endswith(".svg"):
            shutil.copy(os.path.join(os.path.dirname(TEMPLATE), f), work)
    q = {"band": band, "label": label, "style": style}
    for key, path in (("bg", bg), ("char", char)):
        if path:
            name = key + os.path.splitext(path)[1]
            shutil.copy(path, os.path.join(work, name))
            q[key] = name
    fonts = os.path.join(KIT, "assets", "fonts")
    os.makedirs(os.path.join(os.path.dirname(work), "fonts"), exist_ok=True)
    html = open(os.path.join(work, "t.html"), encoding="utf-8").read().replace(
        'url("../fonts/', 'url("file://' + fonts + '/')
    open(os.path.join(work, "t.html"), "w", encoding="utf-8").write(html)
    shot = os.path.join(work, "shot.png")
    url = "file://" + os.path.join(work, "t.html") + "?" + urllib.parse.urlencode(q)
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    "--allow-file-access-from-files", "--virtual-time-budget=4000", "--window-size=1280,900",
                    f"--screenshot={shot}", url], check=True, capture_output=True)
    from PIL import Image  # 画面の下が描かれないことがあるので、高めに撮って上から切る
    im = Image.open(shot).convert("RGB").crop((0, 0, 1280, 720))
    im.save(out, quality=92)
    size = os.path.getsize(out)
    print("書き出した", out, f"{size // 1024}KB", "（2MBを超えている）" if size > 2_000_000 else "")
    return out


def check(out, mine, compare=()):
    """大きいサイズ・パソコンの検索結果のサイズ・スマホのサイズで並べ、競合とも並べる"""
    from PIL import Image, ImageDraw
    sizes = [(640, 360, "大"), (360, 202, "検索結果"), (168, 94, "スマホのおすすめ")]
    rows = [(p, "案") for p in mine] + [(p, "競合") for p in compare]
    pad, lh = 16, 28
    W = sum(w for w, _, _ in sizes) + pad * (len(sizes) + 1)
    H = (360 + lh + pad) * len(rows) + pad
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    from PIL import ImageFont
    font = ImageFont.truetype(os.path.join(KIT, "assets", "fonts", "NotoSansJP-Black.ttf"), 18)
    y = pad
    for p, kind in rows:
        im = Image.open(p).convert("RGB")
        d.text((pad, y), f"{kind}: {os.path.basename(os.path.dirname(p)) if kind == '競合' else os.path.basename(p)}", fill="black", font=font)
        x = pad
        for w, h, _ in sizes:
            sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y + lh))
            x += w + pad
        y += 360 + lh + pad
    sheet.save(out)
    print("一覧を作った", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("out")
    g.add_argument("prompt")
    g.add_argument("--ref", action="append", default=[])
    m = sub.add_parser("make")
    m.add_argument("out")
    m.add_argument("--band", required=True)
    m.add_argument("--label", default="")
    m.add_argument("--bg")
    m.add_argument("--char")
    m.add_argument("--style", default="purple", choices=["purple", "redblack"])
    c = sub.add_parser("check")
    c.add_argument("out")
    c.add_argument("mine", nargs="+")
    c.add_argument("--compare", nargs="*", default=[])
    a = ap.parse_args()
    if a.cmd == "gen":
        gen(a.out, a.prompt, a.ref)
    elif a.cmd == "make":
        make(a.out, a.band, a.label, a.bg, a.char, a.style)
    else:
        check(a.out, a.mine, a.compare)
