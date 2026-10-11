"""YouTubeの公開ページ（チャンネル・検索結果）から数字を取り出す小道具。

APIキーなしで動く。動画ページとコメントは、クラウド環境からだと
YouTube側に止められるので扱わない（コメントはブラウザ経由で集める）。
"""
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "ja"}

# 検索の絞り込み（アップロード日）
SP = {"today": "EgIIAg%3D%3D", "week": "EgIIAw%3D%3D", "month": "EgIIBA%3D%3D", "year": "EgIIBQ%3D%3D"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode()


def initial(html):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html)
    return json.loads(m.group(1))


def walk(o, key):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == key:
                yield v
            yield from walk(v, key)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v, key)


def jp_num(s):
    """「12万」「7.8万」「1,234」→ 整数"""
    if not s:
        return None
    m = re.search(r"([\d.]+)\s*(万|億)?", s.replace(",", ""))
    if not m:
        return None
    unit = {"万": 10_000, "億": 100_000_000}.get(m.group(2), 1)
    return int(float(m.group(1)) * unit)


def channel(handle_or_path):
    """'@paurach' か '/@paurach' → 登録者数と最新30本（再生数・公開からの日数）"""
    path = handle_or_path if handle_or_path.startswith("/") else "/" + handle_or_path
    d = initial(get(f"https://www.youtube.com{path}/videos"))
    head = json.dumps(list(walk(d, "pageHeaderViewModel")), ensure_ascii=False)
    subs = re.search(r"チャンネル登録者数 ([\d.万億,]+)", head)
    videos = []
    for L in walk(d, "lockupViewModel"):
        md = L.get("metadata", {}).get("lockupMetadataViewModel", {})
        parts = [p.get("text", {}).get("content", "") for p in walk(md, "metadataParts") for p in p]
        videos.append({
            "id": L.get("contentId"),
            "title": md.get("title", {}).get("content"),
            "views": jp_num(parts[0]) if parts else None,
            "age": parts[1] if len(parts) > 1 else None,
        })
    return {"path": path, "subs": jp_num(subs.group(1)) if subs else None, "videos": videos}


def search(query, period="month"):
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    if period:
        url += "&sp=" + SP[period]
    d = initial(get(url))
    out = []
    for v in walk(d, "videoRenderer"):
        owner = v.get("ownerText", {}).get("runs", [{}])[0]
        out.append({
            "id": v["videoId"],
            "title": "".join(r["text"] for r in v["title"]["runs"]),
            "views": jp_num(v.get("viewCountText", {}).get("simpleText", "")),
            "age": v.get("publishedTimeText", {}).get("simpleText"),
            "len": v.get("lengthText", {}).get("simpleText"),
            "ch": owner.get("text"),
            "ch_path": owner.get("navigationEndpoint", {}).get("browseEndpoint", {}).get("canonicalBaseUrl"),
        })
    return out
