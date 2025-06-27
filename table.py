import boto3
from pprint import pprint

# DynamoDB クライアントを作成
dynamodb = boto3.client('dynamodb', region_name='ap-northeast-1')

# テーブル名
table_name = 'badminton_chat_logs'

# テーブル構成を取得
response = dynamodb.describe_table(TableName=table_name)

# テーブル全体の情報を表示
pprint(response['Table'])

# 特に見たい項目だけ取り出して表示するなら：
print("\n🔑 主キー構成:")
pprint(response['Table']['KeySchema'])

print("\n📋 属性定義:")
pprint(response['Table']['AttributeDefinitions'])

print("\n📦 項目数:")
print(response['Table']['ItemCount'])

print("\n🧩 その他:")
print("テーブルステータス:", response['Table']['TableStatus'])
print("作成日:", response['Table']['CreationDateTime'])