import boto3
from datetime import datetime
from decimal import Decimal
import uuid

# DynamoDBクライアントを初期化
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')  # 東京リージョンの例
table = dynamodb.Table('badminton_chat_logs')  # テーブル名

def save_to_dynamodb_async(message, bot_response, user_info, cached_result=None, processing_time=None, vector_id=None):
    """
    バドミントンチャットのやり取りをDynamoDBに保存（saved_vector_id対応版）
    
    Args:
        message: ユーザーの質問
        bot_response: AIの回答
        user_info: ユーザー情報（IP、タイムスタンプ等）
        cached_result: キャッシュ結果（ヒットした場合）
        processing_time: AI処理時間（秒）
        vector_id: 新規回答生成時のベクトルID（キャッシュ時はNone）
    """
    try:
        print("[DYNAMODB] データ保存開始...")
        
        # 一意のIDを生成
        chat_id = str(uuid.uuid4())
        
        # キャッシュ利用かどうかを判定
        is_cached = cached_result.get('found', False) if cached_result else False
        
        # DynamoDBに保存するデータを構築
        item = {
            'chat_id': chat_id,  # プライマリキー
            'timestamp': user_info.get('timestamp', datetime.now().isoformat()),
            'date': datetime.now().strftime('%Y-%m-%d'),  # 日付別検索用
            'user_question': message,
            'bot_response': bot_response,
            'user_ip': user_info.get('ip', 'unknown'),            
            'service_type': 'badminton_chat',
            
            # キャッシュ情報
            'is_cached_response': is_cached,
            'cache_similarity_score': float(cached_result.get('similarity_score', 0)) if cached_result and cached_result.get('found') else 0,
            'cache_vector_id': cached_result.get('vector_id', '') if cached_result else '',
            
            # パフォーマンス情報
            'processing_time_seconds': float(processing_time) if processing_time else 0,
            
            # 統計用
            'created_at': datetime.now().isoformat(),
            'month': datetime.now().strftime('%Y-%m'),  # 月別統計用
            'hour': datetime.now().hour,  # 時間帯分析用
            'weekday': datetime.now().weekday(),  # 曜日分析用（0=月曜）
        }
        
        # 新規回答生成時のみsaved_vector_idを追加
        if not is_cached and vector_id:
            item['saved_vector_id'] = vector_id
            print(f"[DYNAMODB] 新規生成 - ベクトルID保存: {vector_id}")
        elif is_cached:
            print(f"[DYNAMODB] キャッシュ利用 - ベクトルID保存なし")
        
        # Decimal型に変換（DynamoDBの数値型要件）
        if 'cache_similarity_score' in item:
            item['cache_similarity_score'] = Decimal(str(item['cache_similarity_score']))
        if 'processing_time_seconds' in item:
            item['processing_time_seconds'] = Decimal(str(item['processing_time_seconds']))
        
        # DynamoDBに保存
        response = table.put_item(Item=item)
        
        print(f"[DYNAMODB] 保存成功: {chat_id}")
        print(f"[DYNAMODB] キャッシュ利用: {'はい' if item['is_cached_response'] else 'いいえ'}")
        print(f"[DYNAMODB] 処理時間: {item['processing_time_seconds']}秒")
        
        return {
            'success': True,
            'chat_id': chat_id,
            'saved_at': item['created_at'],
            'saved_vector_id': vector_id if not is_cached else None  # 新規生成時のベクトルIDを返す
        }
        
    except Exception as e:
        print(f"[DYNAMODB] 保存エラー: {str(e)}")
        print(f"[DYNAMODB] エラータイプ: {type(e).__name__}")
        return {
            'success': False,
            'error': str(e)
        }

def get_chat_statistics():
    """
    チャット統計を取得
    """
    try:
        # 今日の統計
        today = datetime.now().strftime('%Y-%m-%d')
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('date').eq(today)
        )
        
        today_chats = response['Items']
        cached_count = sum(1 for item in today_chats if item.get('is_cached_response', False))
        
        return {
            'today_total': len(today_chats),
            'today_cached': cached_count,
            'today_new_responses': len(today_chats) - cached_count,
            'cache_hit_rate': (cached_count / len(today_chats) * 100) if today_chats else 0
        }
        
    except Exception as e:
        print(f"[DYNAMODB] 統計取得エラー: {str(e)}")
        return None

