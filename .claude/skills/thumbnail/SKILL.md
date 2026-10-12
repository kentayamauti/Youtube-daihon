---
name: thumbnail
description: YouTubeのサムネを高品質に作る。「サムネ作って」「サムネ案」「サムネを直して」と言われたとき、または /thumbnail のときに使う。絵はGeminiで文字なしに作り、文字はお手本型のひな形で載せ、3案を小さいサイズでも比べてからオーナーに見せる。
---

# サムネを作る（高品質の手順）

道具：`youtube-channel-kit/tools/thumbnail.py`（gen／make／check）。ひな形：`youtube-channel-kit/assets/thumb_templates/paurach_type.html`。

## 手順

1. **見本を集める**（二度調べない）
   - 企画書と、`youtube-channel-kit/library/` にあるお手本・競合の `thumbnail.jpg` を見る。足りなければ `tools/library.py add <動画ID>` で保存する
   - 伸びている動画のサムネの「型」（配置・色・文字の数）をメモする
2. **言い切る言葉を決める**（ここが一番大事）
   - 3〜6語。1行で読めるなら1行にする（スマホの小さい表示では2行は読みにくい）
   - タイトルと同じ言葉は入れない（サムネとタイトルで役割を分ける）
   - 数字を1つ入れられるなら入れる（競合の強いサムネは数字が主役）
   - 嘲笑・中身と違う煽りは入れない
3. **絵を作る**（文字は入れない）
   ```
   python3 -I youtube-channel-kit/tools/thumbnail.py gen <背景.png> "絵の説明（英語）" --ref <キャラの見本.png>
   ```
   - キャラは必ず見本画像を渡して、同じ顔・服・色にする
   - 下 1/3 は文字を載せるので、絵は上 2/3 に寄せる
   - Geminiの画像生成は課金が必要。使えないときは、オーナーが撮った写真か、手元の素材で作る
   - 他人の写真（企業の宣材・報道写真・番組の画面）は使わない
4. **文字を載せて3案作る**
   ```
   python3 -I youtube-channel-kit/tools/thumbnail.py make <案A.jpg> --band "帯の文字" --label 小見出し --bg 背景.png --char キャラ.png [--style purple|redblack]
   ```
   - 3案は「言い切る言葉」か「型（purple／redblack）」を変える
5. **小さいサイズで比べる**
   ```
   python3 -I youtube-channel-kit/tools/thumbnail.py check <一覧.png> 案A.jpg 案B.jpg 案C.jpg --compare <競合のthumbnail.jpg>
   ```
   - 一覧を自分で見て、下のチェックを全部通った案だけ残す
6. **オーナーに見せる**：一覧の画像を送り、おすすめを1つ選んだ理由を一言で添える。決めるのはオーナー

## チェック（全部 ✓ になるまで直す）

- [ ] スマホの大きさ（168×94）でも帯の文字が読める
- [ ] 文字は3〜6語、太いゴシック体、縁取りあり（明朝体は使わない）
- [ ] 何の話か（主語：企業・商品）が一目で分かる
- [ ] キャラの顔が大きく、表情で気持ちが伝わる
- [ ] 競合のサムネと並べたとき、負けていない（色・大きさ・言葉）
- [ ] タイトルと同じ言葉をくり返していない
- [ ] 1280×720、2MB以下
- [ ] 使った画像は全部、自分で作った・撮った・使ってよいもの

## 保存場所

`youtube-channel-kit/channels/<チャンネル>/plans/<企画>/` に、案の画像、一覧、使った背景・キャラを置く。
