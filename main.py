
import os
import re
# Flask: PythonでWebサーバーを構築するためのライブラリ
from flask import Flask, request, jsonify, send_from_directory
# CORS: クロスオリジンリクエストを許可
from flask_cors import CORS

# Google API クライアント (YouTube用)
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
# Google AI (Gemini用)
import google.generativeai as genai

# Flaskアプリケーションを作成
# static_folder='.' : index.html などの静的ファイルをこのファイルと同じ場所から探す設定
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app) # CORSを有効化

# --- ユーティリティ関数 ---

def get_video_id(youtube_url):
    """ YouTubeのURLから動画IDを抽出します """
    # 様々な形式のURL (watch, youtu.be, embed) に対応
    patterns = [
        r"watch\?v=([a-zA-Z0-9_-]+)",
        r"youtu\.be/([a-zA-Z0-9_-]+)",
        r"/(embed|v)/([a-zA-Z0-9_-]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, youtube_url)
        if match:
            # 抽出したIDを返す
            return match.group(1) if "watch" in pattern or "youtu.be" in pattern else match.group(2)
    return None # 見つからなかった場合

def get_transcript(youtube_api_key, video_id, lang='ja'):
    """ YouTube Data API v3 を使って字幕データを取得します """
    try:
        # YouTube APIサービスに接続
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
        # 字幕リストを取得
        caption_list_request = youtube.captions().list(part='snippet', videoId=video_id)
        caption_list_response = caption_list_request.execute()
        
        track_id = None
        # 1. まず「日本語(ja)」の手動字幕を探す
        for item in caption_list_response.get('items', []):
            if item['snippet']['language'] == lang:
                track_id = item['id']
                print(f"Found manual transcript: {lang}")
                break
        
        # 2. 手動字幕がなければ「自動生成(a.ja)」の字幕を探す
        if not track_id:
            auto_lang_code = 'a.' + lang
            for item in caption_list_response.get('items', []):
                if item['id'].startswith(auto_lang_code):
                    track_id = item['id']
                    print(f"Found auto-generated transcript: {auto_lang_code}")
                    break

        # どちらも見つからなかった場合
        if not track_id:
            return None, "指定された言語の字幕(手動または自動生成)が見つかりませんでした。"
            
        # 見つかった字幕(SRT形式)をダウンロード
        subtitle_request = youtube.captions().download(id=track_id, tfmt='srt')
        subtitle_data_srt = subtitle_request.execute()
        return subtitle_data_srt, None # 字幕データとエラーなしを返す

    except HttpError as e:
        # APIキーが無効、クォータ超過などのエラーハンドリング
        error_message = e.error_details[0]['message'] if e.error_details else str(e)
        if e.resp.status == 403: return None, f"YouTube APIエラー(403): APIキーが無効か、クォータ上限の可能性があります。 ({error_message})"
        if e.resp.status == 404: return None, f"YouTube APIエラー(404): 動画または字幕が見つかりません。 ({error_message})"
        return None, f"YouTube APIエラー: {error_message}"
    except Exception as e:
        return None, f"予期せぬエラー (YouTube API): {str(e)}"

def clean_srt(srt_text):
    """ SRT形式のテキストから、タイムスタンプや行番号を除去し、テキスト本文だけを抽出します """
    transcript_lines = []
    lines = srt_text.split('\n')
    for line in lines:
        if line.isdigit(): continue # 行番号をスキップ
        if '-->' in line: continue # タイムスタンプをスキップ
        if not line.strip(): continue # 空行をスキップ
        transcript_lines.append(line.strip())
    
    # 重複する行（字幕が複数行にまたがる場合など）を除去
    unique_lines = []
    last_line = ""
    for line in transcript_lines:
        if line != last_line: 
            unique_lines.append(line)
            last_line = line
    return '\n'.join(unique_lines) # テキストを改行で連結して返す

def analyze_with_gemini(gemini_api_key, transcript_text):
    """ Gemini API を使って文字起こしを分析します """
    try:
        # Gemini APIキーを設定
        genai.configure(api_key=gemini_api_key)
        # モデルを定義 (Flashモデルを使用)
        model = genai.GenerativeModel(
            'gemini-2.5-flash-preview-09-2025',
            # AIの役割（ペルソナ）を設定
            system_instruction="あなたはプロの動画構成作家またはコンテンツアナリストです。提供された文字起こしテキストを分析し、その構成や流れ、作成者の意図を的確に見抜いてください。"
        )
        # AIへの指示（プロンプト）
        prompt = f"""
以下のYouTube動画の文字起こしテキストを分析してください。

【文字起こしテキスト】
---
{transcript_text}
---

【分析項目】
以下の3つの項目について、詳細かつ具体的に分析し、結果をまとめてください。

1.  **台本構成:**
    (例: 序論・本論・結論、起承転結、問題提起→具体例→解決策、結論ファースト→理由説明→具体例、など、動画全体の構成がどのようになっているか)

2.  **話の流れ:**
    (どのようなトピックが、どのような順序で展開されているか。時間軸や論理的な流れを簡潔に説明してください)

3.  **運営者の台本構成作成意図:**
    (なぜこの構成・流れにしたのか？ 視聴者に何を最も伝えたいのか、視聴者をどう誘導し、どのような感情や行動（例: チャンネル登録、商品の購入）を引き出そうとしていると考えられるか)

分析結果は読みやすいHTML形式（見出し、リストなど）で出力してください。
"""
        # Gemini APIを実行し、結果をHTML形式で受け取る
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "text/html"}
        )
        return response.text, None # 分析結果とエラーなしを返す
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

@app.route('/analyze', methods=['POST'])
def handle_analysis():
    """ 
    '/analyze' エンドポイント (例: https://myapp.vercel.app/analyze)
    フロントエンドからの分析リクエストを処理します 
    """
    print("Received analysis request...") # サーバーログ
    data = request.json
    youtube_url = data.get('youtube_url')
    youtube_api_key = data.get('youtube_api_key')
    gemini_api_key = data.get('gemini_api_key')

    # 必須項目チェック
    if not all([youtube_url, youtube_api_key, gemini_api_key]):
        return jsonify({"error": "必須項目が不足しています。"}), 400

    # 1. URLから動画IDを抽出
    video_id = get_video_id(youtube_url)
    if not video_id:
        return jsonify({"error": "有効なYouTube動画URLではありません。"}), 400

    # 2. YouTube APIで文字起こしを取得
    print(f"Fetching transcript for video ID: {video_id}")
    srt_data, error = get_transcript(youtube_api_key, video_id)
    if error:
        print(f"Error fetching transcript: {error}")
        return jsonify({"error": error}), 500

    # 3. 文字起こしを整形
    transcript_text = clean_srt(srt_data)
    if not transcript_text:
        return jsonify({"error": "文字起こしデータからテキストを抽出できませんでした。"}), 500

    # 4. Gemini APIで分析
    print("Analyzing transcript with Gemini...")
    analysis_html, error = analyze_with_gemini(gemini_api_key, transcript_text)
    if error:
        print(f"Error analyzing with Gemini: {error}")
        return jsonify({"error": error}), 500

    # 5. 正常な結果をフロントエンドに返す
    print("Analysis successful. Sending response.")
    return jsonify({
        "transcript": transcript_text, # ダウンロード用
        "analysis_html": analysis_html  # 表示用
    })

# --- サーバーの実行 ---
# Vercelのような本番環境では、この if ブロックは実行されません。
# (Vercelは 'app' オブジェクトを直接使います)
# これは、PC上でローカルテスト（例: python main.py）を実行する場合にのみ使われます。
if __name__ == '__main__':
    # 0.0.0.0 を指定すると、PCのローカルIPアドレス経由で携帯からテストできます
    app.run(host='0.0.0.0', port=5000, debug=True)

