from openai import OpenAI
from pinecone import Pinecone
import boto3  # 追加: boto3のインポートが必要
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import os
from typing import Optional, Dict, Any, List
from chatbot_utils import store_response_in_pinecone

client = OpenAI()

def enhance_with_ai_badminton(question: str) -> Dict[str, Any]:
    try:
        system_prompt = """
        あなたはバドミントンに詳しいAIアシスタントです。
        バドミントンサークル向けの質問を分析してください。
        技術、戦術、道具、練習方法などの観点で分析してください。
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

def search_cached_answer_badminton(question: str, similarity_threshold: float = 0.85) -> Dict[str, Any]:
    try:
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = 'badminton-cache'
        index = pc.Index(index_name)

        # 🔽 要約（summary）を取得
        enhanced_data = enhance_with_ai_badminton(question)
        summary = enhanced_data.get("summary", question)

        # 🔽 要約を使ってベクトルを生成
        question_embedding = get_embedding_badminton(summary)

        if not question_embedding:
            raise ValueError("埋め込みベクトルが空です")

        filter_condition = {"system_type": "badminton"}

        search_results = index.query(
            vector=question_embedding,
            filter=filter_condition,
            top_k=5,
            include_metadata=True
        )

        print(f"[BADMINTON] キャッシュ検索実行: {len(search_results.matches)} 件取得")

        if search_results.matches and search_results.matches[0].score >= similarity_threshold:
            best_match = search_results.matches[0]
            cached_answer = best_match.metadata.get('answer', '')

            print(f"[BADMINTON] キャッシュヒット！(類似度: {best_match.score:.3f}, ID: {best_match.id})")

            return {
                "found": True,
                "answer": cached_answer,
                "similarity_score": best_match.score,
                "category": best_match.metadata.get('category'),
                "difficulty_level": best_match.metadata.get('difficulty_level'),
                "cached_timestamp": best_match.metadata.get('timestamp'),
                "vector_id": best_match.id
            }
        else:
            print(f"[BADMINTON] キャッシュミス（閾値: {similarity_threshold}）")
            return {"found": False}

    except Exception as e:
        print(f"[ERROR] バドミントンキャッシュ検索失敗: {e}")
        return {"found": False}
    
def search_cached_answer_badminton(question: str, similarity_threshold: float = 0.85) -> Dict[str, Any]:
    try:
        pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        index_name = 'badminton-cache'
        index = pc.Index(index_name)

        question_embedding = get_embedding_badminton(question)

        if not question_embedding:
            raise ValueError("埋め込みベクトルが空です")

        filter_condition = {"system_type": "badminton"}

        search_results = index.query(
            vector=question_embedding,
            filter=filter_condition,
            top_k=5,
            include_metadata=True
        )

        print(f"[BADMINTON] キャッシュ検索実行: {len(search_results.matches)} 件取得")

        if search_results.matches and search_results.matches[0].score >= similarity_threshold:
            best_match = search_results.matches[0]
            cached_answer = best_match.metadata.get('answer', '')

            print(f"[BADMINTON] キャッシュヒット！(類似度: {best_match.score:.3f}, ID: {best_match.id})")

            return {
                "found": True,
                "answer": cached_answer,
                "similarity_score": best_match.score,
                "category": best_match.metadata.get('category'),
                "difficulty_level": best_match.metadata.get('difficulty_level'),
                "cached_timestamp": best_match.metadata.get('timestamp'),
                "vector_id": best_match.id
            }
        else:
            print(f"[BADMINTON] キャッシュミス（閾値: {similarity_threshold}）")
            return {"found": False}

    except Exception as e:
        print(f"[ERROR] バドミントンキャッシュ検索失敗: {e}")
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
    """
    質問内容から重要なバドミントン関連キーワードをAIに抽出させる。
    """
    try:
        followup = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "あなたは日本語のバドミントン専門アシスタントです。以下の質問から、重要なバドミントンに関連するキーワードを3〜5個抽出してください。質問の内容や意図を表すキーワードを選んでください。必ず以下の形式でのみ返してください：[\"キーワード1\", \"キーワード2\", \"キーワード3\"]"},
                {"role": "user", "content": f"この質問から重要なキーワードを抽出してください：\n\n{question_text}"}
            ],
            temperature=0.2
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
        enhanced_text = f"バドミントン: {text}"

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=[enhanced_text]
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