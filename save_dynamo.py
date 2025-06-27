import boto3
import json
from datetime import datetime
from decimal import Decimal
import uuid

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
table = dynamodb.Table('badminton_chat_logs')

def save_to_dynamodb_async(message, bot_response, user_info, cached_result=None, processing_time=None, saved_vector_id=None):
    """
    バドミントンチャットのやり取りをDynamoDBに保存
    """
    try:
        print("[DYNAMODB] データ保存開始...")

        # 一意のIDと現在時刻
        chat_id = str(uuid.uuid4())
        now = datetime.now()
        timestamp = user_info.get('timestamp', now.isoformat())

        # saved_vector_idの安全な処理
        safe_saved_vector_id = ""
        if saved_vector_id:
            if isinstance(saved_vector_id, dict):
                safe_saved_vector_id = saved_vector_id.get('vector_id') or saved_vector_id.get('id', '')
            elif isinstance(saved_vector_id, bool):
                safe_saved_vector_id = "保存成功" if saved_vector_id else ""
            else:
                safe_saved_vector_id = str(saved_vector_id)

        item = {
            'chat_id': chat_id,
            'timestamp': timestamp,  # ISO形式の完全な日時
            'user_question': message,
            'bot_response': bot_response,            
            'service_type': 'badminton_chat',
            'is_cached_response': cached_result.get('found', False) if cached_result else False,
            'cache_similarity_score': float(cached_result.get('similarity_score', 0)) if cached_result and cached_result.get('found') else 0,
            'cache_vector_id': cached_result.get('vector_id', '') if cached_result and cached_result.get('found') else '',
            'saved_vector_id': safe_saved_vector_id,
            'processing_time_seconds': float(processing_time) if processing_time else 0,
            'created_at': now.isoformat(),
            'weekday': now.weekday()  # 0 = Monday
        }

        # 数値項目は Decimal に変換（DynamoDB要件）
        item['cache_similarity_score'] = Decimal(str(item['cache_similarity_score']))
        item['processing_time_seconds'] = Decimal(str(item['processing_time_seconds']))

        # 保存
        table.put_item(Item=item)

        print(f"[DYNAMODB] 保存成功: {chat_id}")
        print(f"[DYNAMODB] キャッシュ利用: {'はい' if item['is_cached_response'] else 'いいえ'}")
        print(f"[DYNAMODB] ベクトルID: {safe_saved_vector_id}")
        
        return {
            'success': True,
            'chat_id': chat_id,
            'saved_at': item['created_at']
        }

    except Exception as e:
        print(f"[DYNAMODB] 保存エラー: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


def get_chat_statistics():
    """
    チャット統計を取得
    ※ timestamp の日付を用いて今日のチャット数を抽出
    """
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')

        # スキャンして日付一致フィルタ（timestamp から日付部分を抽出）
        response = table.scan()
        all_items = response.get('Items', [])

        today_items = [
            item for item in all_items
            if item.get('timestamp', '').startswith(today_str)
        ]

        cached_count = sum(1 for item in today_items if item.get('is_cached_response', False))

        return {
            'today_total': len(today_items),
            'today_cached': cached_count,
            'today_new_responses': len(today_items) - cached_count,
            'cache_hit_rate': (cached_count / len(today_items) * 100) if today_items else 0
        }

    except Exception as e:
        print(f"[DYNAMODB] 統計取得エラー: {str(e)}")
        return None
