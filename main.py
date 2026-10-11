
import os
import re
# Flask: PythonでWebサーバーを構築するためのライブラリ
from flask import Flask, request, jsonify, send_from_directory
# CORS: クロスオリジンリクエストを許可
from flask_cors import CORS

# Google AI (Gemini用)
from google import genai
from google.genai import types

# Flaskアプリケーションを作成
# static_folder='.' : index.html などの静的ファイルをこのファイルと同じ場所から探す設定
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app) # CORSを有効化

# 使うGeminiのモデル（動画を見て文字起こしできるもの）
GEMINI_MODEL = 'gemini-2.5-flash'

# --- ユーティリティ関数 ---

def get_video_id(youtube_url):
    """ YouTubeのURLから動画IDを抽出します """
    # 様々な形式のURL (watch, youtu.be, embed, shorts) に対応
    patterns = [
        r"watch\?v=([a-zA-Z0-9_-]+)",
        r"youtu\.be/([a-zA-Z0-9_-]+)",
        r"/(?:embed|v|shorts)/([a-zA-Z0-9_-]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            return match.group(1)
    return None # 見つからなかった場合

def get_transcript_with_gemini(gemini_api_key, video_id):
    """
    Gemini に YouTube 動画を直接見てもらい、台本（話している内容）を書き起こしてもらいます。
    YouTube Data API では他人の動画の字幕を取り出せないため、この方法にしています。
    ※ 公開されている動画のみ対応（限定公開・非公開は不可）
    """
    try:
        client = genai.Client(api_key=gemini_api_key)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        prompt = """
この YouTube 動画で話している内容を、台本データとして書き起こしてください。

【ルール】
- 話している言葉を、できるだけそのまま書き起こす（要約しない・言い換えない）
- 「えー」「あのー」などのつなぎ言葉は省いてよい
- 話の区切りごとに改行し、段落の頭に [分:秒] の目安時間をつける（例: [01:23]）
- 話している人が複数いる場合は、行の頭に「話者A:」「話者B:」のように書く
- テロップや画面の文字で大事なものは（テロップ: 〜）として入れる
- 書き起こし以外の説明・前置き・まとめは書かない
"""
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=types.Content(parts=[
                types.Part(file_data=types.FileData(file_uri=video_url)),
                types.Part(text=prompt),
            ]),
            # 映像は低画質で読ませて、長い動画でも処理できるようにする
            config=types.GenerateContentConfig(
                media_resolution=types.MediaResolution.MEDIA_RESOLUTION_LOW,
            ),
        )
        transcript_text = (response.text or '').strip()
        if not transcript_text:
            return None, "Geminiから台本データが返ってきませんでした。動画が公開されているか確認してください。"
        return transcript_text, None
    except Exception as e:
        return None, f"Gemini APIエラー: {str(e)}"

# --- APIエンドポイントの定義 ---

@app.route('/')
def index():
    """
    ルートURL('/') にアクセスがあった場合 (例: https://myapp.vercel.app/)
    index.html を返します
    """
    return send_from_directory('.', 'index.html')

@app.route('/config')
def config():
    """ サーバー側にGemini APIキーが設定済みかどうかを画面に伝えます（キー自体は返しません） """
    return jsonify({"has_server_key": bool(os.environ.get('GEMINI_API_KEY'))})

@app.route('/analyze', methods=['POST'])
def handle_analysis():
    """
    '/analyze' エンドポイント (例: https://myapp.vercel.app/analyze)
    動画URLを受け取り、Gemini経由で台本データを取得して返します
    """
    print("Received transcript request...") # サーバーログ
    data = request.json or {}
    youtube_url = data.get('youtube_url')
    # サーバーの環境変数 GEMINI_API_KEY を優先し、なければ画面で入力されたキーを使う
    gemini_api_key = os.environ.get('GEMINI_API_KEY') or data.get('gemini_api_key')

    # 必須項目チェック
    if not youtube_url:
        return jsonify({"error": "YouTube動画のURLを入力してください。"}), 400
    if not gemini_api_key:
        return jsonify({"error": "Gemini APIキーが設定されていません。"}), 400

    # 1. URLから動画IDを抽出
    video_id = get_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "有効なYouTube動画URLではありません。"}), 400

    # 2. Geminiで台本データを取得
    print(f"Fetching transcript with Gemini for video ID: {video_id}")
    transcript_text, error = get_transcript_with_gemini(gemini_api_key, video_id)
    if error:
        print(f"Error fetching transcript: {error}")
        return jsonify({"error": error}), 500

    # 3. 正常な結果をフロントエンドに返す
    print("Transcript fetched. Sending response.")
    return jsonify({
        "video_id": video_id,
        "transcript": transcript_text
    })

# --- サーバーの実行 ---
# Vercelのような本番環境では、この if ブロックは実行されません。
# (Vercelは 'app' オブジェクトを直接使います)
# これは、PC上でローカルテスト（例: python main.py）を実行する場合にのみ使われます。
if __name__ == '__main__':
    # 0.0.0.0 を指定すると、PCのローカルIPアドレス経由で携帯からテストできます
    app.run(host='0.0.0.0', port=5000, debug=True)
