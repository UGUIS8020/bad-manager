import gradio as gr
from dotenv import load_dotenv
from langchain_community.chat_message_histories import ChatMessageHistory
from badminton_utils import search_cached_answer_badminton, store_response_in_pinecone_badminton, store_response_in_pinecone
import signal
import sys
from badminton_engine import chat_badminton_simple, get_badminton_index
import os
from datetime import datetime
import boto3
from decimal import Decimal
from save_dynamo import save_to_dynamodb_async
import uuid
from qdrant_client import QdrantClient
import time

load_dotenv()

badminton_index = None
qdrant_client = None
MAX_HISTORY_LENGTH = 4

def respond_badminton(message, chat_history):      
    global badminton_index, qdrant_client
    
    overall_start_time = time.time()
    
    print("=" * 60)
    print("[BADMINTON] 処理開始")
    print(f"[BADMINTON] 受信メッセージ: '{message}'")
    print(f"[BADMINTON] 現在の履歴件数: {len(chat_history) if chat_history else 0}")
    print(f"[BADMINTON] インデックス状態: {'初期化済み' if badminton_index is not None else '未初期化'}")
    
    user_info = {
        'ip': 'Webアプリ経由',
        'timestamp': datetime.now().isoformat()
    }
    
    # 履歴変換
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
    
    print(f"[BADMINTON] 履歴変換完了: {len(history.messages)}メッセージ")

    # キャッシュ検索
    print("[BADMINTON] キャッシュ検索開始...")
    try:
        cached_result = search_cached_answer_badminton(message, qdrant_client)    
        print(f"[BADMINTON] キャッシュ検索結果: {cached_result}")
    except Exception as e:
        print(f"[ERROR] キャッシュ検索でエラー: {e}")
        cached_result = {"found": False}

    processing_time = None
    saved_vector_id = None

    if cached_result.get("found"):
        # キャッシュヒット
        bot_message = cached_result.get("answer") or cached_result.get("text") or "回答が見つかりませんでした"
        processing_time = time.time() - overall_start_time
        saved_vector_id = cached_result.get('vector_id')
        
        print(f"[BADMINTON] キャッシュヒット！")
        print(f"[BADMINTON] 類似度: {cached_result.get('score', 0):.3f}")
        print(f"[BADMINTON] 処理時間: {processing_time:.3f}秒")
        print(f"[BADMINTON] 回答長: {len(bot_message)}文字")
    else:
        # 新規生成
        print("[BADMINTON] キャッシュミス -> 新規回答生成を実行")
        print(f"[BADMINTON] 新規回答生成中: {message[:50]}...")
        
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
        
        try:
            start_time = time.time()
            
            print("[BADMINTON] AI回答生成開始...")
            bot_message = chat_badminton_simple(prompt, history, badminton_index)
            
            processing_time = time.time() - start_time
            
            print(f"[BADMINTON] AI回答生成完了!")
            print(f"[BADMINTON] 処理時間: {processing_time:.2f}秒")
            print(f"[BADMINTON] 生成回答長: {len(bot_message)}文字")
            print(f"[BADMINTON] 回答プレビュー: {bot_message[:100]}...")
            
        except Exception as e:
            print(f"[BADMINTON] AI回答生成エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            
            bot_message = ERROR_MESSAGE_TEMPLATE.format(error=str(e))
            processing_time = 0

        # Qdrantに保存
        print("[BADMINTON] Qdrant保存処理...")        
        store_result = store_response_in_pinecone_badminton(message, bot_message)
        if store_result:
            print("[BADMINTON] 新規回答を正常にQdrantに保存しました")
        
        saved_vector_id = str(uuid.uuid4()) if store_result else None

    # DynamoDB保存
    print("[DYNAMODB] 質問・回答データ保存中...")
    save_result = save_to_dynamodb_async(message, bot_message, user_info, cached_result, processing_time, saved_vector_id)
    
    if save_result.get('success'):
        print(f"[DYNAMODB] 保存成功: ID={save_result['chat_id']}")
    else:
        print(f"[DYNAMODB] 保存失敗: {save_result.get('error')}")

    # チャット履歴更新
    print("[BADMINTON] 履歴更新開始...")
    
    if not chat_history:
        chat_history = []
    
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": bot_message})
    
    print(f"[BADMINTON] 更新後履歴件数: {len(chat_history)}")

    # 履歴長制限
    if len(chat_history) > MAX_HISTORY_LENGTH:
        removed_count = len(chat_history) - MAX_HISTORY_LENGTH
        chat_history = chat_history[-MAX_HISTORY_LENGTH:]
        print(f"[BADMINTON] 履歴制限適用: {removed_count}件削除, 残り{len(chat_history)}件")

    total_time = time.time() - overall_start_time
    print(f"[BADMINTON] 処理完了! (合計: {total_time:.2f}秒)")
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
        # グローバル変数の宣言
        global badminton_index, qdrant_client
        
        # Qdrantクライアントの初期化
        print("[INFO] Qdrantクライアント初期化中...")
        qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        print("[INFO] Qdrantクライアント初期化完了")
        
        # バドミントンインデックス初期化
        badminton_index = get_badminton_index()
        print("バドミントンインデックス初期化完了")
        
        # Gradioアプリの作成
        with gr.Blocks(css=".gradio-container {background-color:rgb(142, 166, 4)}") as app:
            gr.Markdown("## 鶯 アシスタント v2.5")
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
            
            msg.submit(respond_badminton, [msg, chatbot], [msg, chatbot])
        
        port = int(os.getenv("PORT", 7861))

        print(f"バドミントンチャット: http://127.0.0.1:{port}")
        print("=" * 60)
        print("サーバーが起動しました")
        print("Ctrl+C で終了")

        # シンプルな起動設定
        app.launch(
            server_name="0.0.0.0",
            server_port=port,
            share=False
        )
            
    except Exception as e:
        print(f"[ERROR] 起動エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()