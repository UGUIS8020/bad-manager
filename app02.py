import gradio as gr
from dotenv import load_dotenv
from langchain_community.chat_message_histories import ChatMessageHistory
from badminton_utils import search_cached_answer_badminton, store_response_in_pinecone_badminton, store_response_in_pinecone
import signal
import sys
from badminton_engine import chat_badminton_simple, get_badminton_index
import os
from datetime import datetime

from email_notification import send_email_async

load_dotenv()

# グローバル変数
badminton_index = None

def respond_badminton(message, chat_history):      
    global badminton_index    
    
    print("=" * 60)
    print("[BADMINTON] 処理開始")
    print(f"[BADMINTON] 受信メッセージ: '{message}'")
    print(f"[BADMINTON] 現在の履歴件数: {len(chat_history) if chat_history else 0}")
    print(f"[BADMINTON] インデックス状態: {'初期化済み' if badminton_index is not None else ' 未初期化'}")
    
    user_info = {
        'ip': 'Webアプリ経由',  # 固定値でOK
        'timestamp': datetime.now().isoformat()
    }
    print("[EMAIL] 質問通知メール送信中...")
    send_email_async(message, user_info)

    # ChatMessageHistory オブジェクトに現在の履歴を追加
    print("[BADMINTON] 履歴変換開始...")
    history = ChatMessageHistory()
    
    if chat_history:
        for i, chat_message in enumerate(chat_history):
            if isinstance(chat_message, dict):
                role = chat_message.get('role', 'unknown')
                content = chat_message.get('content', '')
                print(f"🏸 [BADMINTON] 履歴{i+1}: {role} -> {content[:30]}...")
                
                if role == 'user':
                    history.add_user_message(content)
                elif role == 'assistant':
                    history.add_ai_message(content)
            else:
                print(f"🏸 [BADMINTON] 警告: 履歴{i+1}が辞書形式ではありません: {type(chat_message)}")
    
    print(f"[BADMINTON] 履歴変換完了: {len(history.messages)}メッセージ")

    # 1. バドミントン専用キャッシュ検索
    print("[BADMINTON] キャッシュ検索開始...")    
    cached_result = search_cached_answer_badminton(message)
    # cached_result = {"found": False}
    print(f"[BADMINTON] キャッシュ検索結果: {cached_result}")

    if cached_result.get("found"):
        bot_message = cached_result.get("text", "") or cached_result.get("answer") or "回答が見つかりませんでした"
        print(f"[BADMINTON] キャッシュヒット！(類似度: {cached_result.get('similarity_score', 0):.3f}, ID: {cached_result.get('vector_id', 'N/A')})")
        print(f"[BADMINTON] キャッシュ回答長: {len(bot_message)}文字")
    else:
        print("[BADMINTON] キャッシュミス -> 新規回答生成を実行")
        print(f"[BADMINTON] 新規回答生成中: {message[:50]}...")
        
        # プロンプト作成
        print("[BADMINTON] プロンプト作成中...")
        prompt = f"""
        あなたはバドミントンサークル「鶯（うぐいす）」のアシスタントです。
        サークルメンバーや参加希望者からの質問に、自然な口調で回答してください。

        ## 回答の基本
        - 質問に直接的に答えることを最優先にする
        - 親しみやすい敬語で、適度に詳しく実用的に回答する
        - 初心者にも分かりやすく、具体的な情報を含めて説明する
        - 必要に応じて背景情報や実践的なアドバイスを2-3文で補足する
        - 関連するリンクがあれば自然に紹介する
        - 文末は質問を促すフレーズを必ず入れる必要はなく、内容に応じて自然に締めくくる

        質問: {message}
        """
        
        print(f"[BADMINTON] プロンプト作成完了: {len(prompt)}文字")
        print("[BADMINTON] AI回答生成開始...")
        
        try:
            # 開始時刻記録
            import time
            start_time = time.time()
            
            # 回答生成（グローバルインデックス使用）
            print("[BADMINTON] chat_badminton_simple 呼び出し中...")
            bot_message = chat_badminton_simple(prompt, history, badminton_index)
            
            # 完了時刻計算
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"[BADMINTON] AI回答生成完了!")
            print(f"[BADMINTON] 処理時間: {processing_time:.2f}秒")
            print(f"[BADMINTON] 生成回答長: {len(bot_message)}文字")
            print(f"[BADMINTON] 回答プレビュー: {bot_message[:100]}...")
            
        except Exception as e:
            print(f"[BADMINTON] AI回答生成エラー: {str(e)}")
            print(f"[BADMINTON] エラータイプ: {type(e).__name__}")
            import traceback
            print(f"[BADMINTON] スタックトレース:")
            traceback.print_exc()
            
            bot_message = f"""
            申し訳ございませんが、現在システムに問題が発生しています。
            
            もしバドミントンに関するお手伝いが必要でしたら、
            少し時間をおいて再度お試しください。
            
            サークルの練習は毎週火曜・木曜 19:00-21:00 で行っています！
            
            エラー: {str(e)}
            """

        # 4. バドミントン専用Pineconeに保存
        print("[BADMINTON] Pinecone保存処理...")
        print("[BADMINTON] 注意: Pinecone保存は現在無効化されています")
        store_result = store_response_in_pinecone_badminton(message, bot_message)
        if store_result:
            print("[BADMINTON] 新規回答を正常にPineconeに保存しました")

    # 新しい形式でチャット履歴を更新
    print("[BADMINTON] 履歴更新開始...")
    
    if not chat_history:
        chat_history = []
        print("[BADMINTON] 空の履歴を初期化")
    
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": bot_message})
    
    print(f"[BADMINTON] 履歴に追加: ユーザー質問 + AI回答")
    print(f"[BADMINTON] 更新後履歴件数: {len(chat_history)}")

    # 履歴長制限
    MAX_HISTORY_LENGTH = 4  # バドミントンチャットは履歴を短めに保持
    if len(chat_history) > MAX_HISTORY_LENGTH:
        removed_count = len(chat_history) - MAX_HISTORY_LENGTH
        chat_history = chat_history[-MAX_HISTORY_LENGTH:]
        print(f"[BADMINTON] 履歴制限適用: {removed_count}件削除, 残り{len(chat_history)}件")
    else:
        print(f"[BADMINTON] 履歴制限内: {len(chat_history)}/{MAX_HISTORY_LENGTH}件")

    print("[BADMINTON] 処理完了!")
    print("[BADMINTON] 戻り値: ('', updated_chat_history)")
    print("=" * 60)

    return "", chat_history


def signal_handler(sig, frame):
    """Ctrl+C での終了処理"""
    print('\n[INFO] サーバーを終了しています...')
    sys.exit(0)

def main():
    # シグナルハンドラ設定
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("鶯 バドミントンサークル アシスタント v2.0 起動中...")
    print("=" * 60)
    
    try:
        # バドミントンインデックス初期化
        global badminton_index
        badminton_index = get_badminton_index()
        print("バドミントンインデックス初期化完了")
        
        # スマホ最適化CSS
        mobile_css = """
        /* 全体のモバイル最適化 */
        .gradio-container {
            background: linear-gradient(135deg, #8ea604, #7a8f03) !important;
            max-width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* モバイルでのレスポンシブ調整 */
        @media (max-width: 768px) {
            .gradio-container {
                padding: 8px !important;
            }
            
            /* ヘッダー部分をコンパクトに */
            .markdown h2, .markdown h3 {
                font-size: 1.2rem !important;
                margin: 8px 0 !important;
                text-align: center !important;
                color: white !important;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.3) !important;
            }
            
            /* チャットボット領域の最適化 */
            .chatbot {
                height: 60vh !important;
                min-height: 400px !important;
                border-radius: 12px !important;
                border: 2px solid rgba(255,255,255,0.2) !important;
                background: rgba(255,255,255,0.95) !important;
            }
            
            /* メッセージバブルの調整 */
            .chatbot .message {
                margin: 8px !important;
                padding: 12px !important;
                border-radius: 12px !important;
                font-size: 0.9rem !important;
                line-height: 1.4 !important;
            }
            
            /* 入力欄の最適化 */
            .textbox {
                border-radius: 25px !important;
                border: 2px solid rgba(255,255,255,0.3) !important;
                background: rgba(255,255,255,0.9) !important;
                font-size: 1rem !important;
                padding: 12px 16px !important;
            }
            
            /* 入力欄のフォーカス時 */
            .textbox:focus {
                border-color: rgba(255,255,255,0.8) !important;
                box-shadow: 0 0 10px rgba(255,255,255,0.3) !important;
            }
            
            /* ラベルの調整 */
            .textbox label {
                color: white !important;
                font-weight: bold !important;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.3) !important;
                margin-bottom: 8px !important;
            }
            
            /* 送信ボタンエリアの調整 */
            .submit-btn {
                background: rgba(255,255,255,0.2) !important;
                border: 2px solid rgba(255,255,255,0.3) !important;
                border-radius: 20px !important;
                color: white !important;
                font-weight: bold !important;
                padding: 10px 20px !important;
                margin-top: 8px !important;
            }
        }
        
        /* ダークモード対応 */
        .dark .gradio-container {
            background: linear-gradient(135deg, #6b7a02, #5a6902) !important;
        }
        
        /* アクセシビリティ改善 */
        .textbox input {
            touch-action: manipulation !important;
            -webkit-appearance: none !important;
        }
        
        /* バドミントンテーマカラー */
        .chatbot .message.user {
            background: linear-gradient(135deg, rgba(142, 166, 4, 0.3), rgba(122, 143, 3, 0.4)) !important;
            color: #2d3748 !important;
            border: 1px solid rgba(142, 166, 4, 0.5) !important;
        }
        
        .chatbot .message.bot {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef) !important;
            color: #2d3748 !important;
        }
        
        /* スクロールバーの調整 */
        .chatbot::-webkit-scrollbar {
            width: 6px !important;
        }
        
        .chatbot::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.1) !important;
        }
        
        .chatbot::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.3) !important;
            border-radius: 3px !important;
        }
        """
        
        # Gradioアプリの作成
        with gr.Blocks(css=mobile_css, title="鶯 バドミントンサークル") as app:
            # ヘッダー
            gr.Markdown("## 鶯 アシスタント")
            gr.Markdown("### 鶯のことなら何でもお答えします！")
            
            # チャットボット（モバイル最適化）
            chatbot = gr.Chatbot(
                value=[],
                autoscroll=True,
                height=450,  # スマホでは少し小さめに
                type="messages",
                show_label=False,
                container=True,
                elem_classes=["chatbot"]
            )
            
            # 入力欄（モバイル最適化）
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="練習時間、場所、参加方法など何でもどうぞ！",
                    label="💬 ご質問・ご相談",
                    lines=1,
                    max_lines=3,
                    show_label=True,
                    container=True,
                    scale=4,
                    elem_classes=["textbox"]
                )
            
            # クリアボタン（スマホでは目立たないように）
            with gr.Row():
                clear_btn = gr.ClearButton(
                    [msg, chatbot], 
                    value="🗑️ クリア",
                    size="sm",
                    variant="secondary",
                    elem_classes=["clear-btn"]
                )
            
            # イベントハンドラ
            msg.submit(respond_badminton, [msg, chatbot], [msg, chatbot])
        
        print("バドミントンチャット: http://127.0.0.1:7860")
        print("=" * 60)
        print("スマホ最適化版で起動しました")
        print("モバイルフレンドリーなUIでお楽しみください")
        print("Ctrl+C で終了")

        port = int(os.getenv("PORT", 7860))

        app.launch(
            server_name="0.0.0.0", 
            server_port=port,
            quiet=False,
            share=False,
            # モバイル最適化のための追加設定
            favicon_path=None,  # お好みでバドミントンアイコンを設定
            app_kwargs={
                "docs_url": None,  # API docs を非表示
                "redoc_url": None  # ReDoc を非表示
            }
        )
            
    except Exception as e:
        print(f"[ERROR] 起動エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()