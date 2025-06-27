from openai import OpenAI
from pinecone import Pinecone
import boto3  # 追加: boto3のインポートが必要
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import os
from typing import Optional, Dict, Any, List
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from uuid import uuid4
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
from dotenv import load_dotenv
import re


load_dotenv()

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
enhancement_llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

CACHE_INDEX_NAME = "badminton-cache"


client = OpenAI()

def enhance_with_ai_badminton(question: str) -> Dict[str, Any]:
    try:
        system_prompt = """
        あなたは、バドミントンサークル「鶯（うぐいす）」専属のAIアシスタントです。

        ユーザーからの質問を以下の観点で総合的に分析し、
        その主旨を要約し、関連するキーワード、カテゴリ、難易度を特定してください。

        【分析観点】
        - 参加資格（年齢・学生・子供など）
        - 参加形式（1回のみ・親子・友人同伴・途中参加）
        - レベル（初心者・経験者・ブランクあり）
        - 練習内容・雰囲気（形式・人数・ゲーム・指導）
        - 費用・支払い方法（現金・PayPay・キャンセル）
        - 安全性や保険・撮影などの配慮
        - 初心者向けの「Boot Camp15」関連

        【出力形式（JSONのみ）】
        {
        "summary": "質問の主旨（30文字以内）",
        "keywords": ["キーワード1", "キーワード2", "キーワード3"],
        "category": "カテゴリ名（例：参加資格、親子参加、初心者、費用、雰囲気、その他）",
        "difficulty_level": "初級 / 中級 / 上級"
        }

        説明文や解説は不要です。JSON形式でのみ出力してください。
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"次のバドミントンに関する質問を分析してください：{question}"}
            ],
            temperature=0.3
        )

        result = {
            "summary": extract_summary_badminton(response),
            "keywords": extract_keywords_badminton(response),
            "category": classify_badminton_category(question),
            "difficulty_level": assess_difficulty_level(question),
            "timestamp": datetime.now().isoformat()
        }

        print("[BADMINTON] AI拡張処理完了")
        return result

    except Exception as e:
        print(f"[ERROR] バドミントンAI拡張処理失敗: {e}")
        return {
            "summary": question,
            "keywords": [],
            "category": "その他",
            "difficulty_level": "初級",
            "timestamp": datetime.now().isoformat()
        }

    
def search_cached_answer_badminton(question: str, similarity_threshold: float = 0.84) -> Dict[str, Any]:
    try:
        print("[BADMINTON] Pineconeキャッシュ検索開始...")

        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index = pc.Index("badminton-cache")
        question_embedding = get_embedding_badminton(question)

        if not question_embedding:
            raise ValueError("埋め込みベクトルが生成されませんでした")

        search_results = index.query(
            vector=question_embedding,
            top_k=5,
            include_metadata=True
        )

        print(f"[BADMINTON] 類似度スコア一覧:")
        for i, match in enumerate(search_results.matches):
            question_preview = match.metadata.get("question", "")[:30]
            print(f"  {i+1}. Score: {match.score:.3f}, ID: {match.id}, Question: '{question_preview}...'")

        print(f"[BADMINTON] キャッシュ検索実行: {len(search_results.matches)} 件取得")

        for i, match in enumerate(search_results.matches):
            print(f"  - 候補{i+1}: ID={match.id}, 類似度={match.score:.3f}, 質問={match.metadata.get('question', '')[:20]}...")

        # ここにデバッグコードを挿入
        if search_results.matches:
            best_score = search_results.matches[0].score
            print(f"[DEBUG] 最高スコア: {best_score}, しきい値: {similarity_threshold}")
            print(f"[DEBUG] 比較結果: {best_score >= similarity_threshold}")
            
            if best_score >= similarity_threshold:
                best_match = search_results.matches[0]
                print(f"[BADMINTON] キャッシュヒット！（類似度: {best_match.score:.3f}, ID: {best_match.id}）")

                return {
                    "found": True,
                    "text": best_match.metadata.get('text', ''),
                    "similarity_score": best_match.score,
                    "category": best_match.metadata.get('category'),
                    "difficulty_level": best_match.metadata.get('difficulty_level'),
                    "cached_timestamp": best_match.metadata.get('timestamp'),
                    "vector_id": best_match.id
                }

        print(f"[BADMINTON] キャッシュミス（しきい値 {similarity_threshold:.2f} 未満）")
        return {"found": False}

    except Exception as e:
        print(f"[ERROR] キャッシュ検索中にエラー発生: {e}")
        return {"found": False}

def get_badminton_statistics() -> Dict[str, Any]:
    try:
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = 'badminton-cache'
        index = pc.Index(index_name)
        stats = index.describe_index_stats()

        return {
            "total_qa_pairs": stats.total_vector_count,
            "index_name": index_name,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"[ERROR] バドミントン統計取得失敗: {e}")
        return {"total_qa_pairs": 0, "index_name": "unknown"}

def classify_badminton_category(question: str) -> str:
    question_lower = question.lower()

    categories = {
        "技術": ["スマッシュ", "クリア", "ドロップ", "ネット", "サーブ", "レシーブ", "フォア", "バック", "フットワーク"],
        "戦術": ["戦術", "戦略", "ダブルス", "シングルス", "ポジション", "攻撃", "守備", "ローテーション"],
        "道具": ["ラケット", "ガット", "シューズ", "ウェア", "グリップ", "シャトル", "バッグ"],
        "練習": ["練習", "トレーニング", "メニュー", "上達", "コツ", "基礎", "応用", "筋トレ"],
        "ルール": ["ルール", "反則", "得点", "審判", "コート", "サイズ", "線", "規則"],
        "怪我・健康": ["怪我", "痛み", "予防", "ストレッチ", "準備運動", "アイシング", "テーピング"],
        "サークル運営": ["サークル", "練習日", "会費", "新人", "イベント", "大会", "合宿"]
    }

    for category, keywords in categories.items():
        if any(keyword in question_lower for keyword in keywords):
            return category

    return "その他"

def assess_difficulty_level(question: str) -> str:
    question_lower = question.lower()

    beginner_keywords = ["初心者", "始める", "基礎", "基本", "簡単", "教えて"]
    intermediate_keywords = ["上達", "コツ", "改善", "練習方法"]
    advanced_keywords = ["高度", "応用", "戦術", "競技", "大会", "プロ"]

    if any(keyword in question_lower for keyword in advanced_keywords):
        return "上級"
    elif any(keyword in question_lower for keyword in intermediate_keywords):
        return "中級"
    elif any(keyword in question_lower for keyword in beginner_keywords):
        return "初級"
    else:
        return "中級"

def extract_summary_badminton(response) -> str:
    try:
        content = response.choices[0].message.content
        lines = content.split('\n')
        return lines[0][:100] if lines else content[:100]
    except:
        return "バドミントンに関する質問"

def extract_keywords_badminton(question_text: str) -> List[str]:
    try:
        followup = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """あなたは日本語のバドミントン専門アシスタントです。

質問から重要なキーワードを3〜5個抽出してください。以下の点に注意してください：

1. 質問の具体的な意図を明確に区別してください：
   - 場所関連: 「どこ」「場所」「会場」「体育館」「住所」「アクセス」
   - 内容関連: 「どんな」「内容」「メニュー」「何をする」「練習内容」「プログラム」
   - 時間関連: 「いつ」「曜日」「時間」「スケジュール」「日程」
   - 費用関連: 「料金」「費用」「いくら」「お金」「参加費」
   - 参加関連: 「初心者」「レベル」「条件」「年齢」「経験」
   - 準備関連: 「持ち物」「ラケット」「シューズ」「服装」「用意」

2. 汎用的すぎる単語（「バドミントン」「練習」「サークル」）は避け、より具体的な意図を表すキーワードを選んでください。

3. 必ず以下の形式でのみ返してください：[\"キーワード1\", \"キーワード2\", \"キーワード3\"]"""},
                {"role": "user", "content": f"この質問から重要なキーワードを抽出してください：\n\n{question_text}"}
            ],
            temperature=0.1  # より一貫した結果のため低めに設定
        )

        import json
        result = followup.choices[0].message.content.strip()
        
        # デバッグ用ログ
        print(f"[DEBUG] 質問からのキーワード抽出結果: {result}")
        
        return json.loads(result)
    
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON解析エラー: {e}")
        print(f"[DEBUG] 受信したテキスト: {followup.choices[0].message.content}")
        return []
    except Exception as e:
        print(f"[ERROR] キーワード抽出エラー: {e}")
        return []

def get_embedding_badminton(text: str) -> list:
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=[text]
        )

        if not response.data or not response.data[0].embedding:
            raise ValueError("埋め込みが空です")

        return response.data[0].embedding

    except Exception as e:
        print(f"[ERROR] バドミントン埋め込み生成失敗: {e}")
        return []

def cleanup_old_badminton_cache(days_to_keep: int = 90):
    try:
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = 'badminton-cache'
        index = pc.Index(index_name)

        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()

        print(f"[BADMINTON] {days_to_keep}日より古いキャッシュをクリーンアップしました")

    except Exception as e:
        print(f"[ERROR] バドミントンキャッシュクリーンアップ失敗: {e}")



class BadmintonScheduleManager:
    def __init__(self):
        """DynamoDBクライアントを初期化"""
        try:
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=os.getenv('AWS_REGION', 'ap-northeast-1'),
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            
            # テーブル名（既存のbad_schedulesテーブルを使用）
            self.schedule_table_name = os.getenv('DYNAMODB_SCHEDULE_TABLE', 'bad_schedules')
            self.schedule_table = self.dynamodb.Table(self.schedule_table_name)
            
            print(f"[INFO] DynamoDBテーブル '{self.schedule_table_name}' に接続しました")
        except Exception as e:
            print(f"[ERROR] DynamoDB初期化失敗: {e}")
            raise
    
    def get_upcoming_practices(self, days_ahead: int = 14) -> List[Dict[str, Any]]:
        try:
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            print(f"[INFO] 練習予定を検索中: {today} ～ {end_date}")
            
            response = self.schedule_table.scan(
                FilterExpression=(
                    '#date BETWEEN :start_date AND :end_date AND #status = :active_status'
                ),
                ExpressionAttributeNames={
                    '#date': 'date',
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':start_date': today.isoformat(),
                    ':end_date': end_date.isoformat(),
                    ':active_status': 'active'
                }
            )

            practices = response.get('Items', [])
            print(f"[INFO] {len(practices)}件の練習予定を取得しました")

            # 日付順ソート
            practices.sort(key=lambda x: x.get('date', ''))

            return practices

        except ClientError as e:
            print(f"[ERROR] DynamoDB練習予定取得エラー: {e}")
            return []
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            return []
    
    def get_practice_by_date(self, target_date: str) -> Optional[Dict[str, Any]]:
        """
        特定日の練習予定を取得
        
        Args:
            target_date: 取得したい日付 (YYYY-MM-DD形式)
            
        Returns:
            練習予定の詳細情報
        """
        try:
            print(f"[INFO] {target_date}の練習予定を検索中...")
            
            # まずGSIを試す
            try:
                response = self.schedule_table.query(
                    IndexName='date-index',  # GSIを使用する場合
                    KeyConditionExpression='#date = :date',
                    ExpressionAttributeNames={
                        '#date': 'date'
                    },
                    ExpressionAttributeValues={
                        ':date': target_date
                    }
                )
                
                items = response.get('Items', [])
                return items[0] if items else None
                
            except ClientError as e:
                print(f"[ERROR] DynamoDB特定日練習予定取得エラー: {e}")
                # GSIがない場合はscanにフォールバック
                response = self.schedule_table.scan(
                    FilterExpression='#date = :date',
                    ExpressionAttributeNames={'#date': 'date'},
                    ExpressionAttributeValues={':date': target_date}
                )
                items = response.get('Items', [])
                return items[0] if items else None
            
        except Exception as e:
            print(f"[ERROR] 予期しないエラー: {e}")
            return None
    
    def format_schedule_for_chat(self, schedules: List[Dict[str, Any]]) -> str:
        if not schedules:
            return "現在、登録されている練習予定はありません。通常は毎週木曜日19:00-21:00に越谷市立地域スポーツセンターで練習を行っております。"

        formatted_text = "📅 **今後の練習予定**\n\n"

        for schedule in schedules:
            date_str = schedule.get('date', '')
            day_of_week = schedule.get('day_of_week', '')
            start_time = schedule.get('start_time', '19:00')
            end_time = schedule.get('end_time', '21:00')
            venue = schedule.get('venue', '場所未定')
            court = schedule.get('court', '')
            max_participants = schedule.get('max_participants', 0)
            registered = schedule.get('participants_count', 0)
            remaining = max_participants - registered

            # 日付の整形
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%m月%d日')
            except:
                formatted_date = date_str

            formatted_text += f"• **{formatted_date}（{day_of_week}）** {start_time}〜{end_time}\n"
            formatted_text += f"  📍 {venue}（{court}）\n"
            formatted_text += f"  👥 定員: {max_participants}人 / 登録: {registered}人 / 空き: {remaining}人\n"
            formatted_text += "\n"

        return formatted_text.strip()


# チャットボット統合用の関数（クラス外の独立関数）
def get_schedule_response(user_message: str) -> str:
    """
    ユーザーメッセージに基づいて練習スケジュール情報を返す
    
    Args:
        user_message: ユーザーからのメッセージ
        
    Returns:
        練習スケジュール情報のレスポンス
    """
    try:
        schedule_manager = BadmintonScheduleManager()
        today = datetime.now().date()
        
        # メッセージ内容に基づいて処理を分岐
        message_lower = user_message.lower()
        
        if '今週' in user_message or 'この週' in user_message:
            practices = schedule_manager.get_upcoming_practices(days_ahead=7)
            return schedule_manager.format_schedule_for_chat(practices)
        
        elif '来週' in user_message or '次週' in user_message:
            # 来週の練習予定を取得
            days_to_next_week = 7 - today.weekday()
            practices = schedule_manager.get_upcoming_practices(days_ahead=14)
            
            # 来週分のみフィルタリング
            next_week_practices = []
            for practice in practices:
                try:
                    practice_date = datetime.strptime(practice['date'], '%Y-%m-%d').date()
                    if practice_date >= today + timedelta(days=days_to_next_week):
                        next_week_practices.append(practice)
                except Exception as e:
                    print(f"[WARN] 日付解析エラー: {e}")
                    continue
            
            return schedule_manager.format_schedule_for_chat(next_week_practices)
        
        elif '今月' in user_message or 'この月' in user_message:
            # 修正: 今月のデータのみを正確に取得
            practices = schedule_manager.get_upcoming_practices(days_ahead=60)  # 十分な範囲で取得
            
            # 今月分のみフィルタリング
            current_month = today.month
            current_year = today.year
            current_month_practices = []
            
            for practice in practices:
                try:
                    practice_date = datetime.strptime(practice['date'], '%Y-%m-%d').date()
                    # 今月かつ今日以降のデータのみ
                    if (practice_date.year == current_year and 
                        practice_date.month == current_month and 
                        practice_date >= today):
                        current_month_practices.append(practice)
                except Exception as e:
                    print(f"[WARN] 日付解析エラー: {e}")
                    continue
            
            return schedule_manager.format_schedule_for_chat(current_month_practices)
        
        else:
            # デフォルトは今後2週間
            practices = schedule_manager.get_upcoming_practices()
            return schedule_manager.format_schedule_for_chat(practices)
    
    except Exception as e:
        print(f"[ERROR] スケジュール取得エラー: {e}")
        return "申し訳ございません、現在スケジュール情報を取得できません。"


def store_response_in_pinecone_badminton(question: str, answer: str) -> bool:
    """
    バドミントン用チャットのQAペアを Pinecone キャッシュに保存する関数。
    """
    return store_response_in_pinecone(
        question=question,
        answer=answer,
        index_name="badminton-cache"
    )

def store_response_in_pinecone(question, answer, index_name=CACHE_INDEX_NAME):
    """
    質問と回答のペアをPineconeに保存する関数。AIで拡張した情報も保存。
    """
    try:
        pc = Pinecone(api_key=PINECONE_API_KEY)

        # インデックスの接続確認
        try:
            pinecone_index = pc.Index(index_name)
            print(f"インデックス {index_name} に接続しました")
        except Exception as e:
            print(f"インデックス {index_name} 接続失敗: {e}")
            return False

        # AI拡張情報の取得
        enhanced_data = enhance_with_ai(question, answer)

        # ベクトル生成（ここで summary ではなく question を使う）
        question_embedding = embedding_model.embed_query(question)
        print(f"質問の埋め込みベクトル生成完了 (長さ: {len(question_embedding)})")

        # 保存前にキャッシュ類似チェック（重複防止）
        search_results = pinecone_index.query(
            vector=question_embedding,
            top_k=5,
            include_metadata=True
        )
        for match in search_results.matches:
            if match.score >= 0.95:
                print(f"[INFO] 類似質問が既に存在（ID: {match.id}, Score: {match.score:.3f}）→ 保存をスキップ")
                return True

        # 一意IDの生成
        unique_id = str(uuid4())

        # メタデータの準備（summary は別フィールドに分ける）
        metadata = {
            "text": answer,
            "question": question,  # ← ここをsummaryではなくquestionに
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "chatbot_response",
            "question_summary": enhanced_data.get("question_summary", ""),
            "answer_summary": enhanced_data.get("answer_summary", ""),
            "alternative_questions": enhanced_data.get("alternative_questions", []),
            "keywords": enhanced_data.get("keywords", []),
            "category": enhanced_data.get("category", "未分類")
        }

        # アップサート
        pinecone_index.upsert([
            {
                "id": unique_id,
                "values": question_embedding,
                "metadata": metadata
            }
        ])
        print(f"オリジナル質問ベクトルをアップサート: {unique_id}")

        # 類義語の処理（必要であれば）
        alt_questions = enhanced_data.get("alternative_questions", [])
        original_embedding = np.array(question_embedding).reshape(1, -1)

        if alt_questions:
            print("===== 類義語の類似度分析 =====")
            for i, alt_question in enumerate(alt_questions):
                if alt_question and len(alt_question) > 5:
                    print(f"類義語 {i+1}: '{alt_question}'")

                    alt_embedding = embedding_model.embed_query(alt_question)
                    similarity = cosine_similarity(original_embedding, [alt_embedding])[0][0]
                    print(f"  元の質問との類似度: {similarity:.4f}")

                    pinecone_index.upsert([
                        {
                            "id": f"{unique_id}-alt-{i}",
                            "values": alt_embedding,
                            "metadata": metadata
                        }
                    ])
                else:
                    print(f"類義語 {i+1}: '{alt_question}' - スキップ（短すぎ）")

        print(f"拡張Q&AをIDで保存しました: {unique_id} (インデックス: {index_name})")
        return True

    except Exception as e:
        print(f"Pineconeへの応答保存エラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def enhance_with_ai(question: str, answer: str) -> dict:
    try:
        print("===== AI拡張処理開始 =====")
        print(f"元の質問: {question}")

        prompt = f"""
以下のバドミントンに関する質問と回答のペアに対して、次の拡張情報を生成してください:

1. 質問の要約 (30文字以内)
2. 回答の要約 (50文字以内)
3. 質問のキーワード (5つまで)
4. 回答のカテゴリ（例: 練習方法、道具、戦術、ルール、体験、その他）

質問: {question}

回答: {answer}

出力は以下のJSON形式で返してください:
{{
  "question_summary": "質問の要約",
  "answer_summary": "回答の要約",
  "keywords": ["キーワード1", "キーワード2", "キーワード3"],
  "category": "カテゴリ"
}}

出力はJSON形式のみにしてください。説明などは不要です。
        """

        # LLM応答取得
        response = enhancement_llm.invoke(prompt)

        # content 抽出
        raw = getattr(response, "content", "").strip()
        print("=== LLM応答（raw） ===")
        print(raw)
        print("======================")

        # ✅ コードブロック除去処理
        if raw.startswith("```json"):
            raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.DOTALL)

        # JSONとしてパース
        if not raw or not raw.strip().startswith("{"):
            raise ValueError("LLMから空または無効なJSONが返されました")

        enhanced_data = json.loads(raw)

        # 結果表示
        print("===== AI拡張結果 =====")
        print(f"  要約: {enhanced_data.get('question_summary', '')}")
        print(f"  キーワード: {enhanced_data.get('keywords', [])}")
        print(f"  カテゴリ: {enhanced_data.get('category', '')}")
        print("===== AI拡張処理完了 =====")

        # タイムスタンプ付加
        enhanced_data["timestamp"] = datetime.now().isoformat()
        return enhanced_data

    except Exception as e:
        print(f"[ERROR] AI拡張処理失敗: {e}")
        return {
            "question_summary": question[:30] + "…" if len(question) > 30 else question,
            "answer_summary": answer[:50] + "…" if len(answer) > 50 else answer,
            "keywords": [],
            "category": "その他",
            "timestamp": datetime.now().isoformat()
        }
    
def save_response_data(message, bot_message, user_info, cached_result, processing_time, vector_id_data):
    """
    回答データをDynamoDBに保存する関数
    
    Args:
        message: ユーザーの質問
        bot_message: AI/キャッシュからの回答
        user_info: ユーザー情報
        cached_result: キャッシュ検索結果
        processing_time: 処理時間
        vector_id_data: ベクトルID情報のディクショナリ
                       {'cache_vector_id': str, 'saved_vector_id': str}
    """
    print("[SAVE] データ保存処理開始...")
    
    try:
        # 保存データの整合性チェック
        if not message or not bot_message:
            print("[SAVE] 警告: メッセージまたは回答が空です")
        
        if processing_time is None:
            processing_time = 0.0
            print("[SAVE] 警告: processing_timeがNoneのため0.0に設定")
        
        # キャッシュヒット時と新規回答時で保存処理を分ける
        if cached_result.get("found"):
            print(f"[SAVE] キャッシュヒット時の保存処理 (cache_vector_id: {vector_id_data.get('cache_vector_id')})")
            save_result = save_to_dynamodb_async(
                message,
                bot_message,
                user_info,
                cached_result,
                processing_time,
                cache_vector_id=vector_id_data.get('cache_vector_id'),  # キャッシュ時のベクトルID
                saved_vector_id=None  # 新規生成ではないのでNone
            )
        else:
            print(f"[SAVE] 新規回答時の保存処理 (saved_vector_id: {vector_id_data.get('saved_vector_id')})")
            save_result = save_to_dynamodb_async(
                message,
                bot_message,
                user_info,
                cached_result,
                processing_time,
                cache_vector_id=None,  # キャッシュではないのでNone
                saved_vector_id=vector_id_data.get('saved_vector_id')  # 新規生成時のベクトルID
            )

        if save_result and save_result.get('success'):
            print(f"[SAVE] 保存成功: ID={save_result.get('chat_id', 'N/A')}")
            return True
        else:
            error_msg = save_result.get('error', '不明なエラー') if save_result else 'save_result がNone'
            print(f"[SAVE] 保存失敗: {error_msg}")
            return False
            
    except Exception as save_error:
        print(f"[SAVE] 保存処理でエラー発生: {str(save_error)}")
        import traceback
        traceback.print_exc()
        return False


