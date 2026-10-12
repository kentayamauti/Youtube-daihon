# 動画ライブラリ

調べた動画を1本1フォルダで保存する場所。**調べる前にまず `index.csv` を見る。調べ済みなら調べ直さない。**

## フォルダの中身

`<チャンネル>/<公開日>_<動画ID>/`

| ファイル | 中身 | 取り方 |
|---|---|---|
| `meta.json` | タイトル、概要欄、タグ、再生・高評価・コメント数、長さ、チャンネル登録者数、取得日 | YouTube Data API |
| `thumbnail.jpg` | サムネイル | YouTubeの画像サーバー |
| `frames/frame_25.jpg` ほか2枚 | 動画の画面（25%・50%・75%地点） | YouTubeが自動で作る画像 |
| `comments.json` | 人気順のコメント最大300件 | YouTube Data API |
| `transcript.md` | 台本の文字起こし（4分ごとに区切り） | Gemini（一字一句ではない） |
| `summary.md` | 企画・構成・主張・出典・確かめた場面・締め・サムネとの約束・画面の作り・良い点・弱い点・採点 | Gemini |

## 足す・作り直す

```
python3 -I youtube-channel-kit/tools/library.py add <動画IDかURL> [...]   # 足りないものだけ取る
python3 -I youtube-channel-kit/tools/library.py add ... --skip-gemini      # 数字・サムネ・画面・コメントだけ
python3 -I youtube-channel-kit/tools/library.py index                      # index.csv を作り直す
```

- 数字（再生数など）は取得日の時点のもの。新しくしたいときは、もう一度 `add` すると `meta.json` が上書きされる
- 文字起こしと要約は、一度できたら作り直さない。作り直したいときは、そのファイルを消してから `add`
