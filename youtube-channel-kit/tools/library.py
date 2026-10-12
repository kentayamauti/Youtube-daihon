"""動画ライブラリ：1本の動画を調べたら、全部フォルダに保存して二度と調べ直さない。

保存先: library/<チャンネル>/<公開日>_<動画ID>/
  meta.json        タイトル・概要欄・タグ・再生/高評価/コメント数・長さ・取得日（YouTube Data API）
  thumbnail.jpg    サムネイル
  frames/          動画の画面（25%・50%・75%地点。YouTubeが自動で作る画像）
  comments.json    人気順コメント（最大300件）
  transcript.md    台本の文字起こし（Gemini。YouTubeの文字起こしが取れるようになったら差し替え）
  summary.md       企画・構成・主張・サムネとの約束・画面の作り・良い点/弱い点（Gemini）
library/index.csv  全動画の一覧（調べる前にまずここを見る）

使い方:
  python3 -I tools/library.py add <動画IDかURL> [...]        # 足りないものだけ取る（取得済みは飛ばす）
  python3 -I tools/library.py add ... --skip-gemini           # 数字・サムネ・画面・コメントだけ
  python3 -I tools/library.py index                           # index.csv を作り直す
"""
import argparse
import base64
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_transcript as gt  # noqa: E402
import ytapi  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "library")

SUMMARY_PROMPT = """あなたはYouTubeチャンネルの分析担当です。下の動画（メタ情報・台本の文字起こし・サムネイル・画面3枚）を読み、
次の見出しで日本語のMarkdownにまとめてください。推測は「（推測）」と書く。台本にないことは書かない。

## 企画（一行）
## 誰に向けた動画か
## 構成（時間つき）
- [mm:ss] パートの名前：何を言っているか（1行）
## 冒頭30秒で言っていること
## 主張（一言で）
## 根拠・出典（台本で触れた媒体・データ）
## 自分で試した・確かめた場面（あれば時間と内容、全体に占めるおおよその割合）
## 締め（最後に何を言って終わるか）
## サムネ・タイトルの約束と、本編での回収
## 画面の作り（サムネと画面3枚から：キャラ・背景・テロップ・図表・素材の使い方）
## 言い回し・キャラの特徴（よく出る言葉、口調）
## 良い点（3つ）
## 弱い点・批判されそうな点（3つ）
## 採点（各1〜5）
- サムネとタイトルの約束を果たす：
- 見る前になかったもの（事実・体験・見方）がある：
- 事実と意見を分けている（出典あり）：
- その回にしかない「確かめた」中身：
- 人に話したくなる結論で終わる：
"""


def slug(s, n=24):
    s = re.sub(r"[\\/:*?\"<>|\s#【】「」『』（）()!！?？、。・…ｗw]+", "_", s).strip("_")
    return s[:n]


def fetch(url):
    return urllib.request.urlopen(url, timeout=60).read()


def folder_for(meta):
    ch = slug(meta["channel_handle"] or meta["channel"], 40)
    return os.path.join(ROOT, ch, f"{meta['published'][:10]}_{meta['id']}")


def get_meta(vid):
    v = ytapi.api("videos", part="snippet,statistics,contentDetails", id=vid)["items"][0]
    c = ytapi.api("channels", part="snippet,statistics", id=v["snippet"]["channelId"])["items"][0]
    st = v["statistics"]
    return {
        "id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
        "title": v["snippet"]["title"], "published": v["snippet"]["publishedAt"],
        "channel": v["snippet"]["channelTitle"], "channel_id": v["snippet"]["channelId"],
        "channel_handle": c["snippet"].get("customUrl", ""),
        "channel_subs": int(c["statistics"].get("subscriberCount", 0) or 0),
        "sec": ytapi.seconds(v["contentDetails"]["duration"]),
        "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
        "comments": int(st.get("commentCount", 0)),
        "tags": v["snippet"].get("tags", []), "description": v["snippet"]["description"],
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def save_image(vid, names, path):
    for n in names:
        try:
            data = fetch(f"https://i.ytimg.com/vi/{vid}/{n}.jpg")
        except urllib.error.HTTPError:
            continue
        with open(path, "wb") as f:
            f.write(data)
        return n
    return None


def gemini_summary(meta, d):
    parts = [{"text": SUMMARY_PROMPT},
             {"text": "# メタ情報\n" + json.dumps({k: meta[k] for k in
              ("title", "channel", "channel_subs", "published", "sec", "views", "likes", "comments", "description")},
              ensure_ascii=False)},
             {"text": "# 台本の文字起こし\n" + open(os.path.join(d, "transcript.md"), encoding="utf-8").read()}]
    for img in ["thumbnail.jpg", "frames/frame_25.jpg", "frames/frame_50.jpg", "frames/frame_75.jpg"]:
        p = os.path.join(d, img)
        if os.path.exists(p):
            parts.append({"text": f"[画像: {img}]"})
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": base64.b64encode(open(p, "rb").read()).decode()}})
    body = json.dumps({"contents": [{"parts": parts}], "generationConfig": {"temperature": 0.2}}).encode()
    for rnd in range(4):
        for m in gt.FALLBACK:
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                data=body, headers={"Content-Type": "application/json"})
            try:
                r = json.loads(urllib.request.urlopen(req, timeout=600).read())
                text = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
                return f"<!-- {m} による要約 / {meta['fetched_at']} -->\n# {meta['title']}\n\n{text}\n"
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504):
                    raise
        time.sleep(60 * (rnd + 1))
    raise RuntimeError("Gemini が混雑していて要約できなかった")


def add(vid, skip_gemini=False, import_dirs=()):
    vid = gt.video_id(vid)
    meta = get_meta(vid)
    d = folder_for(meta)
    os.makedirs(os.path.join(d, "frames"), exist_ok=True)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if not os.path.exists(os.path.join(d, "thumbnail.jpg")):
        save_image(vid, ["maxresdefault", "sddefault", "hqdefault"], os.path.join(d, "thumbnail.jpg"))
    for pct, k in ((25, 1), (50, 2), (75, 3)):
        p = os.path.join(d, "frames", f"frame_{pct}.jpg")
        if not os.path.exists(p):
            save_image(vid, [f"maxres{k}", f"sd{k}", f"hq{k}"], p)
    if not os.path.exists(os.path.join(d, "comments.json")) and meta["comments"]:
        try:
            cs = ytapi.comments(vid, 300)
            json.dump(cs, open(os.path.join(d, "comments.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except urllib.error.HTTPError as e:  # コメント欄が閉じている動画など
            print("  コメント取得できず", vid, e.code)
    tp = os.path.join(d, "transcript.md")
    if not os.path.exists(tp):
        for src in import_dirs:  # 以前に別の場所で起こした文字起こしを引き継ぐ
            old = os.path.join(src, f"{vid}.md")
            if os.path.exists(old):
                os.replace(old, tp)
                break
    if skip_gemini:
        print("保存（Geminiなし）", d)
        return d
    if not os.path.exists(tp):
        text = gt.transcribe(vid, gt.FALLBACK[0])
        with open(tp, "w", encoding="utf-8") as f:
            f.write(f"<!-- {meta['url']} / Gemini による文字起こし（一字一句ではない） -->\n{text}\n")
    sp = os.path.join(d, "summary.md")
    if not os.path.exists(sp):
        with open(sp, "w", encoding="utf-8") as f:
            f.write(gemini_summary(meta, d))
    print("保存", d)
    return d


def index():
    rows = []
    for dirpath, _, files in os.walk(ROOT):
        if "meta.json" not in files:
            continue
        m = json.load(open(os.path.join(dirpath, "meta.json"), encoding="utf-8"))
        rows.append({
            "公開日": m["published"][:10], "チャンネル": m["channel"], "登録者": m["channel_subs"],
            "再生": m["views"], "再生/登録者": round(m["views"] / max(m["channel_subs"], 1), 2),
            "長さ(分)": round(m["sec"] / 60, 1), "タイトル": m["title"], "動画ID": m["id"],
            "文字起こし": "◯" if os.path.exists(os.path.join(dirpath, "transcript.md")) else "",
            "要約": "◯" if os.path.exists(os.path.join(dirpath, "summary.md")) else "",
            "取得日": m["fetched_at"][:10], "フォルダ": os.path.relpath(dirpath, ROOT),
        })
    rows.sort(key=lambda r: (r["チャンネル"], r["公開日"]))
    with open(os.path.join(ROOT, "index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["動画ID"])
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "本 → library/index.csv")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "index"])
    ap.add_argument("videos", nargs="*")
    ap.add_argument("--skip-gemini", action="store_true")
    ap.add_argument("--import-dir", action="append", default=[])
    a = ap.parse_args()
    if a.cmd == "add":
        for v in a.videos:
            try:
                add(v, a.skip_gemini, a.import_dir)
            except Exception as e:  # 1本の失敗で全体を止めない
                print("失敗", v, e)
    index()
