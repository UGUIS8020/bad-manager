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
        
        # Gradioアプリの作成
        with gr.Blocks(css=".gradio-container {background-color:rgb(142, 166, 4)}") as app:
            gr.Markdown("## 鶯 アシスタント v2.0")
            gr.Markdown("### ご質問・ご相談はこちらでなんでもお答えいたします")        
            
            
            chatbot = gr.Chatbot(
                autoscroll=True,
                height=500,
                type="messages"
            )
            
            msg = gr.Textbox(
                placeholder="鶯に関することなら何でもお気軽にどうぞ！",
                label="質問・相談"
            )
            
            # clear = gr.ClearButton([msg, chatbot])
            msg.submit(respond_badminton, [msg, chatbot], [msg, chatbot])
        
        print("バドミントンチャット: http://127.0.0.1:7860")
        print("=" * 60)
        print("サーバーが起動しました")
        print("Ctrl+C で終了")

        port = int(os.getenv("PORT", 7860))

        app.launch(
            server_name="0.0.0.0", 
            server_port=port,
            quiet=False,
            share=False
        )
            
    except Exception as e:
        print(f"[ERROR] 起動エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()