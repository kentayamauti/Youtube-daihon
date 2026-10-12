"""YouTube Data API v3 で数字とコメントを取る（キーは環境のネットワークシークレットで付く）。

使い方:
  python3 -I tools/ytapi.py videos @ハンドル 出力.csv [--max 50]
  python3 -I tools/ytapi.py comments <動画ID> 出力.json [--max 300]
"""
import argparse
import csv
import json
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://www.googleapis.com/youtube/v3/"


def api(path, **params):
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(url, timeout=60).read())


def channel(handle):
    it = api("channels", part="snippet,statistics,contentDetails", forHandle=handle)["items"][0]
    return {"id": it["id"], "title": it["snippet"]["title"],
            "subs": int(it["statistics"].get("subscriberCount", 0)),
            "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"]}


def seconds(iso):
    h, m, s = (int(x) if x else 0 for x in re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso).groups())
    return h * 3600 + m * 60 + s


def videos(handle, limit=50):
    ch = channel(handle)
    ids, token = [], None
    while len(ids) < limit:
        p = {"part": "contentDetails", "playlistId": ch["uploads"], "maxResults": 50}
        if token:
            p["pageToken"] = token
        r = api("playlistItems", **p)
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            break
    out = []
    for i in range(0, len(ids[:limit]), 50):
        r = api("videos", part="snippet,statistics,contentDetails", id=",".join(ids[i:i + 50]))
        for v in r["items"]:
            st = v["statistics"]
            out.append({"id": v["id"], "published": v["snippet"]["publishedAt"],
                        "title": v["snippet"]["title"], "sec": seconds(v["contentDetails"]["duration"]),
                        "views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                        "comments": int(st.get("commentCount", 0))})
    return ch, out


def comments(video_id, limit=300, order="relevance"):
    out, token = [], None
    while len(out) < limit:
        p = {"part": "snippet", "videoId": video_id, "maxResults": 100, "order": order, "textFormat": "plainText"}
        if token:
            p["pageToken"] = token
        r = api("commentThreads", **p)
        for t in r["items"]:
            s = t["snippet"]["topLevelComment"]["snippet"]
            out.append({"text": s["textDisplay"], "likes": s["likeCount"], "replies": t["snippet"]["totalReplyCount"]})
        token = r.get("nextPageToken")
        if not token:
            break
    return out[:limit]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["videos", "comments"])
    ap.add_argument("target")
    ap.add_argument("out")
    ap.add_argument("--max", type=int, default=50)
    a = ap.parse_args()
    if a.cmd == "videos":
        ch, vs = videos(a.target, a.max)
        with open(a.out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(vs[0]))
            w.writeheader()
            w.writerows(vs)
        print(ch["title"], "登録者", ch["subs"], len(vs), "本 →", a.out)
    else:
        cs = comments(a.target, a.max)
        json.dump(cs, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(len(cs), "件 →", a.out)


def search(query, days=31, limit=50, order="viewCount"):
    """期間内の動画を検索し、再生数・チャンネル登録者数をつけて返す（1回100ユニット）"""
    from datetime import datetime, timedelta, timezone
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = api("search", part="snippet", q=query, type="video", order=order, publishedAfter=after,
            maxResults=min(limit, 50), regionCode="JP", relevanceLanguage="ja")
    ids = [i["id"]["videoId"] for i in r["items"]]
    if not ids:
        return []
    vs = api("videos", part="snippet,statistics,contentDetails", id=",".join(ids))["items"]
    chs = {c["id"]: c for c in api("channels", part="snippet,statistics",
                                   id=",".join({v["snippet"]["channelId"] for v in vs}))["items"]}
    out = []
    for v in vs:
        c = chs.get(v["snippet"]["channelId"], {})
        out.append({"id": v["id"], "title": v["snippet"]["title"], "published": v["snippet"]["publishedAt"],
                    "sec": seconds(v["contentDetails"]["duration"]),
                    "views": int(v["statistics"].get("viewCount", 0)),
                    "likes": int(v["statistics"].get("likeCount", 0)),
                    "comments": int(v["statistics"].get("commentCount", 0)),
                    "ch_id": v["snippet"]["channelId"], "ch": v["snippet"]["channelTitle"],
                    "ch_handle": c.get("snippet", {}).get("customUrl"),
                    "subs": int(c.get("statistics", {}).get("subscriberCount", 0) or 0)})
    return out


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def is_short(video_id):
    """ショート（縦長）なら True。/shorts/ のURLがそのまま開けばショート、普通の動画ページに飛ばされれば横長"""
    op = urllib.request.build_opener(_NoRedirect)
    try:
        return op.open(f"https://www.youtube.com/shorts/{video_id}", timeout=20).status == 200
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return False
        raise
