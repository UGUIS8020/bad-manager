from uuid import uuid4
import time
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from pinecone import Pinecone
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# from text_normalizer import basic_normalize_text

# 環境変数のロード
load_dotenv()

PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
enhancement_llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

CACHE_INDEX_NAME = "raiden-cache"

SIMILARITY_THRESHOLD = 0.8  # 希望通りに0.85に設定

def enhance_with_ai(question, answer):
    """
    質問と回答にAIを使って類義語や要約を追加する
    
    Parameters:
    -----------
    question : str
        ユーザーからの質問
    answer : str
        チャットボットの回答
    
    Returns:
    --------
    dict
        拡張された情報を含む辞書
    """
    try:
        print(f"===== AI拡張処理開始 =====")
        print(f"元の質問: {question}")
        
        # システムプロンプトを設定
        prompt = f"""
以下の歯科医療に関する質問と回答のペアに対して、次の拡張情報を生成してください:

1. 質問の要約 (30文字以内)
2. 回答の要約 (50文字以内)
3. 質問のキーワード (5つまで)
4. 回答のカテゴリ（例: 治療法、診断、予防、症状、技術、材料）

質問: {question}

回答: {answer}

出力は以下のJSON形式で返してください:
{{
  "question_summary": "質問の要約",
  "answer_summary": "回答の要約",
  "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
  "category": "カテゴリ"
}}

出力はJSON形式のみにしてください。説明などは不要です。
類義語はできるだけ多様にしてください。例えば「自家歯牙移植のメリットは?」と「自家歯の移植の利点は?」のように異なる言い回しや言葉を使ってください。
        """
        
        # LLMに処理を依頼
        response = enhancement_llm.invoke(prompt)
        
        # 応答をパースしてJSONに変換
        enhanced_data = json.loads(response.content)
        
        print(f"AI拡張結果:")
        print(f"  要約: {enhanced_data.get('question_summary', 'なし')}")
        print(f"  類義語: {enhanced_data.get('alternative_questions', [])}")
        print(f"  キーワード: {enhanced_data.get('keywords', [])}")
        print(f"  カテゴリ: {enhanced_data.get('category', '未分類')}")
        print(f"===== AI拡張処理完了 =====")
        
        return enhanced_data
    except Exception as e:
        print(f"AI拡張処理エラー: {e}")
        # エラー時はデフォルト値を返す
        return {
            "question_summary": question[:30] + "..." if len(question) > 30 else question,
            "answer_summary": answer[:50] + "..." if len(answer) > 50 else answer,
            "alternative_questions": [],
            "keywords": [],
            "category": "未分類"
        }

def store_response_in_pinecone(question, answer, index_name=CACHE_INDEX_NAME):
    """
    質問と回答のペアをPineconeに保存する関数。AIで拡張した情報も保存。
    
    Parameters:
    -----------
    question : str
        ユーザーからの質問
    answer : str
        チャットボットの回答
    index_name : str
        Pineconeのインデックス名（デフォルトは"raiden-cache"）
    
    Returns:
    --------
    bool
        保存が成功したらTrue、失敗したらFalse
    """
    try:
        # Pineconeの初期化
        pc = Pinecone(api_key=PINECONE_API_KEY)
        
        # インデックスが存在するか確認し、なければ作成を試みる
        try:
            pinecone_index = pc.Index(index_name)
            print(f"インデックス {index_name} に接続しました")
        except Exception as e:
            print(f"インデックス {index_name} が見つかりません: {e}")
            # インデックスが存在するか確認
            indexes = pc.list_indexes()
            print(f"利用可能なインデックス: {indexes}")
            if not indexes or index_name not in [idx.name for idx in indexes]:
                print(f"インデックス {index_name} が存在しません。作成してください。")
                # 代替としてraidenインデックスを使用
                print(f"代替として 'raiden-main' インデックスを使用します")
                index_name = "raiden-main"
                try:
                    pinecone_index = pc.Index(index_name)
                except Exception as e:
                    print(f"代替インデックスへの接続も失敗: {e}")
                    return False
            else:
                try:
                    pinecone_index = pc.Index(index_name)
                except Exception as e:
                    print(f"インデックス接続エラー: {e}")
                    return False
        
        # AI拡張情報を取得
        enhanced_data = enhance_with_ai(question, answer)
        
        # Q&Aペア用の一意のIDを作成
        unique_id = str(uuid4())
        
        # 質問の埋め込みを取得
        summary = enhanced_data.get("question_summary", question)
        question_embedding = embedding_model.embed_query(summary)
        print(f"質問の埋め込みベクトル生成完了 (長さ: {len(question_embedding)})")
        
        # 質問と回答を含むメタデータを準備
        metadata = {
            "text": answer,  # 検索用にtextフィールドに回答を保存
            "question": summary,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": "chatbot_response",
            "question_summary": enhanced_data.get("question_summary", ""),
            "answer_summary": enhanced_data.get("answer_summary", ""),
            "alternative_questions": enhanced_data.get("alternative_questions", []),
            "keywords": enhanced_data.get("keywords", []),
            "category": enhanced_data.get("category", "未分類")
        }
        
        # ベクトルをPineconeにアップサート
        pinecone_index.upsert(
            vectors=[
                {
                    "id": unique_id,
                    "values": question_embedding,
                    "metadata": metadata
                }
            ]
        )
        print(f"オリジナル質問ベクトルをアップサート: {unique_id}")
        
        # 類義語のインデックスも追加
        alt_questions = enhanced_data.get("alternative_questions", [])
        print(f"類義語の数: {len(alt_questions)}")
        
        # 元の質問と類義語の類似度の計算と出力
        if alt_questions:
            original_embedding = np.array(question_embedding).reshape(1, -1)
            print(f"===== 類義語の類似度分析 =====")
            
            for i, alt_question in enumerate(alt_questions):
                if alt_question and len(alt_question) > 5:  # 短すぎる類義語は除外
                    print(f"類義語 {i+1}: '{alt_question}'")
                    
                    # 類義語の埋め込みベクトルを取得
                    alt_embedding = embedding_model.embed_query(alt_question)
                    alt_embedding_array = np.array(alt_embedding).reshape(1, -1)
                    
                    # 元の質問との類似度を計算
                    similarity = cosine_similarity(original_embedding, alt_embedding_array)[0][0]
                    print(f"  元の質問との類似度: {similarity:.4f}")
                    
                    # 類義語をアップサート
                    alt_id = f"{unique_id}-alt-{i}"
                    pinecone_index.upsert(
                        vectors=[
                            {
                                "id": alt_id,
                                "values": alt_embedding,
                                "metadata": metadata  # 同じメタデータを使用
                            }
                        ]
                    )
                    print(f"  類義語ベクトルをアップサート: {alt_id}")
                else:
                    print(f"類義語 {i+1}: '{alt_question}' - 短すぎるためスキップ")
        
        print(f"拡張Q&AをIDで保存しました: {unique_id} (インデックス: {index_name})")
        return True
    except Exception as e:
        print(f"Pineconeへの応答保存エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_previous_responses(query, index_name=CACHE_INDEX_NAME):
    print(f"DEBUG: 渡された検索クエリ → {query}")
    print(f"===== 類似質問検索開始 =====")
    print(f"検索インデックス: {index_name}")

    try:
        # AIによる要約を取得してから埋め込みを生成
        enhanced = enhance_with_ai(query, answer="")
        query_summary = enhanced.get("question_summary", query)
        print(f"AI要約: {query_summary}")
        
        # 要約されたクエリでベクトル生成
        query_embedding = embedding_model.embed_query(query_summary)
        print(f"要約での埋め込みベクトル生成完了 (長さ: {len(query_embedding)})")

        # Pineconeに接続
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index = pc.Index(index_name)
        print(f"インデックス {index_name} に接続成功")

        stats = index.describe_index_stats()
        print(f"インデックス統計: ベクトル数={stats.total_vector_count}")

        if stats.total_vector_count == 0:
            print(f"ベクトル未登録。別インデックス 'raiden' を試みます。")
            index = pc.Index("raiden")
            stats = index.describe_index_stats()
            if stats.total_vector_count == 0:
                return {"found": False}
            index_name = "raiden"
            print(f"代替インデックス 'raiden' 使用中")

        # 類似質問検索（フィルター付き）
        query_results = index.query(
            vector=query_embedding,
            top_k=5,
            include_metadata=True,
            filter={"type": "chatbot_response"}
        )

        print(f"検索結果: {len(query_results.matches)}件")

        # 結果がなければフィルターなし再検索
        if not query_results.matches:
            print("フィルターなしで再検索")
            query_results = index.query(
                vector=query_embedding,
                top_k=5,
                include_metadata=True
            )

        if not query_results.matches:
            return {"found": False}

        # 最良マッチを選定
        best_match = query_results.matches[0]
        print(f"最良スコア: {best_match.score:.4f}, 閾値: {SIMILARITY_THRESHOLD:.2f}")

        if best_match.score > SIMILARITY_THRESHOLD:
            return {
                "found": True,
                "question": best_match.metadata.get("question", ""),
                "answer": best_match.metadata.get("text", ""),
                "similarity": best_match.score,
                "timestamp": best_match.metadata.get("timestamp", "不明"),
                "category": best_match.metadata.get("category", "未分類"),
                "summary": best_match.metadata.get("answer_summary", "")
            }

        return {"found": False}

    except Exception as e:
        print(f"過去の応答チェックエラー: {e}")
        import traceback
        traceback.print_exc()
        return {"found": False}

def search_cached_answer(question: str):
    """
    質問から類似質問を検索し、キャッシュ回答を返す。
    
    Parameters:
    - question (str): ユーザーの質問
    
    Returns:
    - dict: {
        "found": True/False,
        "answer": 回答テキスト,
        "question": 質問テキスト,
        "similarity": 類似度スコア,
        "timestamp": 保存日時
    }
    """
    search_result = check_previous_responses(question)
    
    if search_result.get("found"):
        print(f"キャッシュヒット: {search_result['question']}")
        print(f"類似度スコア: {search_result['similarity']}")
        print(f"保存された回答: {search_result['timestamp']}")
        return search_result
    
    print("キャッシュは見つかりませんでした")
    return {"found": False}
