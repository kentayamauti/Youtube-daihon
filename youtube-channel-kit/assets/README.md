# 共通の素材

| 場所 | 中身 |
|---|---|
| `fonts/` | サムネ用の太い日本語フォント（Noto Sans JP Black、Dela Gothic One。どちらも SIL Open Font License で商用利用できる） |
| `thumb_templates/food_type.html` | 料理チャンネル型。料理の写真を画面いっぱいに1〜2枚、上と下に白い太字＋黒の太い縁取り |
| `thumb_templates/paurach_type.html` | お手本（パウラちゃんねる）型のサムネのひな形。上 2/3 に背景写真と集中線、左に大きなキャラ、右下に小見出し、下 1/3 に黄色帯の大きな文字 |

## サムネの作り方

**ふつうはスキル `/thumbnail` と `tools/thumbnail.py` を使う**（下は中で何をしているかの説明）。

1. ひな形をチャンネルの `plans/<企画>/` にコピーし、背景写真とキャラ画像（透過PNG）を同じ場所に置く
2. URLのうしろに `?band=帯の文字&label=小見出し&bg=背景.jpg&char=キャラ.png` を付けて開く（2行にするときは帯の文字を `上の行|下の行` にする）
3. Chromium でスクショする

```
chrome --headless=new --no-sandbox --hide-scrollbars --allow-file-access-from-files --virtual-time-budget=3000 \
  --window-size=1280,900 --screenshot=thumb.png "file://…/paurach_type.html?band=…&label=…&char=…"
```

4. 上から 1280×720 で切り出す（画面の下の方が描かれないことがあるので、900 の高さで撮ってから切る）

- 背景写真は、自分で撮った写真がいちばん安全（お手本も「画像はすべて独自に撮影・制作」と書いている）
