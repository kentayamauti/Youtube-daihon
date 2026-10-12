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
| `transcript.md` | 台本の文字起こし（30秒ごとに1段落） | **YouTubeの文字起こし（字幕・自動字幕）**。字幕がない動画だけ Gemini |
| `transcript_gemini.md` | Geminiの文字起こし（話者名つき） | 先にGeminiで起こした動画だけ |
| `summary.md` | Geminiの要約 | `--summary` を付けたときだけ（ふだんは作らない。台本は自分で読んで分析する） |

## 足す・作り直す

```
python3 -I youtube-channel-kit/tools/library.py add <動画IDかURL> [...]   # 足りないものだけ取る
python3 -I youtube-channel-kit/tools/library.py add ... --summary          # Geminiの要約も作る（ふだんは不要）
python3 -I youtube-channel-kit/tools/library.py index                      # index.csv を作り直す
```

- 数字（再生数など）は取得日の時点のもの。新しくしたいときは、もう一度 `add` すると `meta.json` が上書きされる
- 文字起こしは、一度できたら作り直さない（Geminiの文字起こしだけは、YouTubeの文字起こしが取れたら自動で差し替える）
- 自動字幕は聞き間違いがある（人名・固有名詞）。時間と流れは確か
