import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from langchain_community.chat_message_histories import ChatMessageHistory

# DynamoDB機能をインポート
try:
    from badminton_utils import get_schedule_response
    DYNAMODB_AVAILABLE = True
    print("[INFO] DynamoDB機能が利用可能です")
except ImportError as e:
    print(f"[WARN] DynamoDB機能が利用できません: {e}")
    DYNAMODB_AVAILABLE = False

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_badminton_index():
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index("badminton")
    stats = index.describe_index_stats()
    print(f"Total vectors in badminton index: {stats.total_vector_count}")
    return index

def chat_badminton_simple(prompt: str, history: ChatMessageHistory, index) -> str:
    start_time = time.time()
    try:
        print(f"[BADMINTON] DynamoDB統合版での処理開始: {prompt}")

        # スケジュール関連のキーワードをチェック
        schedule_keywords = ['練習', 'スケジュール', '予定', '日程', 'いつ', '時間', '場所', '今週', '来週', '今月']
        is_schedule_question = any(keyword in prompt for keyword in schedule_keywords)

        print(f"[BADMINTON] スケジュール関連質問: {is_schedule_question}")

        # DynamoDBからスケジュール情報を取得（利用可能な場合のみ）
        schedule_context = ""
        if is_schedule_question and DYNAMODB_AVAILABLE:
            try:
                print(f"[BADMINTON] DynamoDBからスケジュール取得中...")
                schedule_response = get_schedule_response(prompt)
                if schedule_response and "予定されている練習はありません" not in schedule_response:
                    schedule_context = f"\n\n【最新の練習スケジュール】\n{schedule_response}"
                    print(f"[BADMINTON] DynamoDBからスケジュール情報を取得: {len(schedule_response)}文字")
                else:
                    print(f"[BADMINTON] DynamoDBスケジュール: 予定なし")
            except Exception as e:
                print(f"[BADMINTON] DynamoDBスケジュール取得失敗: {e}")

        # ベクトル生成＆検索（既存のコード）
        try:
            embedding = client.embeddings.create(
                model="text-embedding-3-small",
                input=[f"バドミントン: {prompt}"]
            ).data[0].embedding

            search_results = index.query(
                vector=embedding,
                top_k=3,
                include_metadata=True
            )

            context_text = ""
            for match in search_results.matches:
                context_text += match.metadata.get("text", "") + "\n"
        except Exception as e:
            print(f"[WARN] Pinecone検索失敗: {e}")
            context_text = ""

        # メッセージ構成
        messages = [
            {"role": "system", "content": """あなたはバドミントンサークルの親しみやすいアシスタント「鶯（うぐいす）」です。

以下の点を心がけて回答してください：
- 親しみやすく、丁寧な言葉遣い
- バドミントンの専門知識を活用
- 練習スケジュールについては最新の情報を提供
- 初心者にも分かりやすい説明"""}
        ]

        for msg in history.messages[-2:]:
            messages.append({
                "role": "user" if msg.type == "human" else "assistant",
                "content": msg.content
            })

        if context_text:
            messages.append({"role": "system", "content": f"参考情報:\n{context_text}"})

        if schedule_context:
            messages.append({"role": "system", "content": schedule_context})
            print(f"[BADMINTON] スケジュール情報をプロンプトに追加")

        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        final_response = response.choices[0].message.content

        if is_schedule_question and not schedule_context and not DYNAMODB_AVAILABLE:
            final_response += "\n\n💡 練習スケジュールの詳細については、サークル管理者にお問い合わせください。"

        # 回答の保存（スケジュール質問のときは保存スキップメッセージだけ出力）
        if is_schedule_question:
            print("[SKIP] スケジュール質問のため回答の保存をスキップします") 
        return final_response 
    
    except Exception as e:
        print(f"[ERROR] バドミントンチャット処理失敗: {e}")
        return "申し訳ございません、現在回答を生成できません。しばらくしてから再度お試しください。"
