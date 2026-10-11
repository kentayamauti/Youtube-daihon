"""Gemini に YouTube の URL を渡して、台本（文字起こし）を取ってくる。

使い方:
  python3 -I tools/gemini_transcript.py <動画URLかID> [<動画URLかID> ...] --out <保存フォルダ>
  （オプション）--model gemini-2.5-flash

APIキーは環境のネットワークシークレットで generativelanguage.googleapis.com に
X-Goog-Api-Key として付ける（スクリプトはキーを扱わない）。
公開動画だけ。文字起こしはAIによるもので一字一句ではない（分析用）。
"""
import argparse
import json
import os
import re
import urllib.request

PROMPT = """この動画の音声を、話者ごとに一字一句そのまま日本語で文字起こししてください。
形式:
- 1行目に「# 動画タイトル（わかれば）」
- 以降は「[mm:ss] 話者名: セリフ」を1行ずつ（話者名が分からなければ 話者A/話者B）
- 要約・省略・感想は入れない。BGMや効果音は書かない
"""


def video_id(s):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", s)
    return m.group(1) if m else s


def transcribe(vid, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [{"parts": [
            {"file_data": {"file_uri": f"https://www.youtube.com/watch?v={vid}"}},
            {"text": PROMPT},
        ]}],
        # 文字起こしは音声が主なので、映像は低解像度にしてトークンを節約する
        "generationConfig": {"mediaResolution": "MEDIA_RESOLUTION_LOW", "temperature": 0},
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    return "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="gemini-2.5-flash")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for v in a.videos:
        vid = video_id(v)
        path = os.path.join(a.out, f"{vid}.md")
        if os.path.exists(path):
            print("済み", path)
            continue
        try:
            text = transcribe(vid, a.model)
        except Exception as e:  # 1本の失敗で全体を止めない
            print("失敗", vid, e)
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"<!-- https://www.youtube.com/watch?v={vid} / {a.model} による文字起こし -->\n{text}\n")
        print("保存", path)
