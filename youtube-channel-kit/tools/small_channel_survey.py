"""小規模チャンネル調査：キーワードで検索し「登録者が少ないのに伸びた動画」を拾う。

使い方:
  python3 -I tools/small_channel_survey.py キーワード一覧.txt 出力.md [--period month] [--max-subs 10000] [--ratio 3] [--min-views 5000]

キーワード一覧.txt は1行1キーワード。結果は Markdown の表（倍率の高い順）と、
同じ名前の .json（生データ）に書き出す。
"""
import argparse
import json
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import yt  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("keywords")
ap.add_argument("out")
ap.add_argument("--period", default="month", choices=list(yt.SP))
ap.add_argument("--max-subs", type=int, default=10_000)
ap.add_argument("--ratio", type=float, default=3)
ap.add_argument("--min-views", type=int, default=5_000)
a = ap.parse_args()

kws = [k.strip() for k in open(a.keywords, encoding="utf-8") if k.strip() and not k.startswith("#")]
subs = {}
rows = {}
for kw in kws:
    try:
        res = yt.search(kw, a.period)
    except Exception as e:  # 1語の失敗で全体を止めない
        print("検索失敗", kw, e, file=sys.stderr)
        continue
    for v in res:
        p = v["ch_path"]
        if p and p not in subs:
            try:
                subs[p] = yt.channel(p)["subs"]
            except Exception:
                subs[p] = None
            time.sleep(0.3)
        v["subs"] = subs.get(p)
        rows.setdefault(v["id"], {**v, "kws": []})["kws"].append(kw)
    time.sleep(0.5)

json.dump(list(rows.values()), open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

hits = [r for r in rows.values()
        if r["subs"] and r["views"] and r["subs"] <= a.max_subs
        and r["views"] >= a.ratio * r["subs"] and r["views"] >= a.min_views]
hits.sort(key=lambda r: -r["views"] / r["subs"])
per_kw = defaultdict(int)
for r in hits:
    for k in r["kws"]:
        per_kw[k] += 1

with open(a.out, "w", encoding="utf-8") as f:
    f.write(f"# 小規模チャンネル調査（期間: {a.period}／登録者{a.max_subs:,}人以下・再生が登録者の{a.ratio:g}倍以上・{a.min_views:,}回以上）\n\n")
    f.write(f"検索した動画 {len(rows)} 本のうち、条件に合ったのは {len(hits)} 本。\n\n")
    f.write("## キーワード別の当たり数\n\n| キーワード | 当たり |\n|---|---|\n")
    for k in kws:
        f.write(f"| {k} | {per_kw.get(k, 0)} |\n")
    f.write("\n## 当たった動画\n\n| 倍率 | 再生 | 登録者 | 公開 | 長さ | チャンネル | タイトル |\n|---|---|---|---|---|---|---|\n")
    for r in hits:
        t = r["title"].replace("|", "｜")
        f.write(f"| {r['views']/r['subs']:.0f}倍 | {r['views']:,} | {r['subs']:,} | {r['age']} | {r['len']} | {r['ch']} | [{t}](https://www.youtube.com/watch?v={r['id']}) |\n")
print(f"{len(rows)}本中 {len(hits)}本 → {a.out}")
