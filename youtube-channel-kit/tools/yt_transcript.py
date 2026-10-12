"""YouTube の「文字起こし」（字幕・自動字幕）を取る。

動画ページはロボット確認で止められるので、YouTubeアプリ（iOS）と同じ窓口から字幕の場所を聞いて取る。
日本語の字幕があればそれを、なければ自動字幕（asr）を使う。字幕がない動画は None を返す。

使い方:
  python3 -I tools/yt_transcript.py <動画ID>
"""
import html
import http.cookiejar
import json
import re
import sys
import urllib.request

WEB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
IOS_UA = "com.google.ios.youtube/20.10.4 (iPhone16,2; U; CPU iOS 18_3 like Mac OS X;)"

_session = {}


def _opener():
    if not _session:
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        page = op.open(urllib.request.Request("https://www.youtube.com/?hl=ja", headers={"User-Agent": WEB_UA}),
                       timeout=30).read().decode()
        _session.update(op=op,
                        ver=re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"', page).group(1),
                        vd=re.search(r'"VISITOR_DATA":"([^"]+)"', page).group(1))
    return _session


def tracks(vid):
    s = _opener()
    body = {"context": {"client": {"clientName": "IOS", "clientVersion": "20.10.4", "hl": "ja", "gl": "JP",
                                   "visitorData": s["vd"]}}, "videoId": vid}
    h = {"Content-Type": "application/json", "User-Agent": IOS_UA, "X-Goog-Visitor-Id": s["vd"],
         "X-Youtube-Client-Name": "1", "X-Youtube-Client-Version": s["ver"], "Origin": "https://www.youtube.com"}
    req = urllib.request.Request("https://www.youtube.com/youtubei/v1/player?prettyPrint=false",
                                 data=json.dumps(body).encode(), headers=h)
    p = json.loads(s["op"].open(req, timeout=30).read())
    return (p.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks") or [])


def fetch(vid):
    """[(開始秒, 文字), ...] と字幕の種類（'字幕' / '自動字幕'）を返す。なければ (None, None)"""
    ts = tracks(vid)
    ja = [t for t in ts if t.get("languageCode", "").startswith("ja")]
    pick = ([t for t in ja if t.get("kind") != "asr"] or ja or [])
    if not pick:
        return None, None
    t = pick[0]
    xml = _session["op"].open(urllib.request.Request(t["baseUrl"], headers={"User-Agent": IOS_UA}),
                              timeout=30).read().decode()
    lines = [(float(a), html.unescape(re.sub(r"<[^>]+>", "", b)).replace("\n", " ").strip())
             for a, b in re.findall(r'<text start="([\d.]+)"[^>]*>(.*?)</text>', xml, re.S)]
    return [x for x in lines if x[1]], ("自動字幕" if t.get("kind") == "asr" else "字幕")


def to_markdown(lines, every=30):
    """だいたい every 秒ごとに1段落にまとめる"""
    out, buf, start = [], [], None
    for sec, text in lines:
        if start is None:
            start = sec
        buf.append(text)
        if sec - start >= every:
            out.append(f"[{int(start) // 60:02d}:{int(start) % 60:02d}] " + "".join(buf))
            buf, start = [], None
    if buf:
        out.append(f"[{int(start) // 60:02d}:{int(start) % 60:02d}] " + "".join(buf))
    return "\n\n".join(out)


if __name__ == "__main__":
    lines, kind = fetch(sys.argv[1])
    print(kind)
    print(to_markdown(lines) if lines else "字幕なし")
