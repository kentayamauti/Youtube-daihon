#!/usr/bin/env python3
"""オーナーOK済みのLINE配信を一斉送信する。

使い方: python3 scripts/line_broadcast.py <配信ファイル.md> [画像のURL]
- 配信ファイルに「状態：OK」がないものは送らない。
- 送ったら配信ファイルの状態を「配信済み（日時）」に書き換える。
"""
import datetime
import json
import re
import subprocess
import sys
import uuid

path = sys.argv[1]
image = sys.argv[2] if len(sys.argv) > 2 else None
src = open(path, encoding="utf-8").read()
if "状態：OK" not in src:
    sys.exit("オーナーOKが付いていないので送りません: " + path)
text = re.search(r"```\n(.*?)\n```", src, re.S).group(1)

messages = [{"type": "text", "text": text}]
if image:
    messages.append({"type": "image", "originalContentUrl": image, "previewImageUrl": image})

r = subprocess.run(
    ["curl", "-sS", "-m", "30", "-w", "\n%{http_code}", "-X", "POST",
     "https://api.line.me/v2/bot/message/broadcast",
     "-H", "Content-Type: application/json",
     "-H", "X-Line-Retry-Key: " + str(uuid.uuid4()),
     "--data-binary", json.dumps({"messages": messages}, ensure_ascii=False)],
    capture_output=True, text=True)
body, _, code = r.stdout.rpartition("\n")
print(code, body)
if code != "200":
    sys.exit(1)

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
src = re.sub(r"- 状態：.*", "- 状態：配信済み（" + now + " JST）", src, count=1)
open(path, "w", encoding="utf-8").write(src)
