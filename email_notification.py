# email_notification.py - OCNメール対応版

import smtplib
import ssl
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
import threading

# def send_email_notification(question: str, user_info: Optional[dict] = None) -> bool:
#     """
#     新しい質問をOCNメールで通知する
    
#     Args:
#         question: ユーザーの質問内容
#         user_info: ユーザー情報（IPアドレス、時刻など）
    
#     Returns:
#         bool: 送信成功時True、失敗時False
#     """
#     try:
#         # OCNメール設定を環境変数から取得
#         smtp_server = os.getenv("MAIL_SERVER", "smtp.ocn.ne.jp")
#         smtp_port = int(os.getenv("MAIL_PORT", "465"))
#         use_ssl = os.getenv("MAIL_USE_SSL", "True").lower() == "true"
#         use_tls = os.getenv("MAIL_USE_TLS", "False").lower() == "true"
#         sender_email = os.getenv("MAIL_USERNAME")
#         sender_password = os.getenv("MAIL_PASSWORD")
#         notify_email = os.getenv("MAIL_NOTIFICATION_RECIPIENT")
#         default_sender = os.getenv("MAIL_DEFAULT_SENDER")
        
#         print(f"[EMAIL] メール設定確認:")
#         print(f"  サーバー: {smtp_server}:{smtp_port}")
#         print(f"  SSL: {use_ssl}, TLS: {use_tls}")
#         print(f"  送信者: {sender_email}")
#         print(f"  受信者: {notify_email}")
        
#         if not all([sender_email, sender_password, notify_email]):
#             print("[EMAIL] 必須のメール設定が不完全です")
#             print(f"  MAIL_USERNAME: {'設定済み' if sender_email else '未設定'}")
#             print(f"  MAIL_PASSWORD: {'設定済み' if sender_password else '未設定'}")
#             print(f"  MAIL_NOTIFICATION_RECIPIENT: {'設定済み' if notify_email else '未設定'}")
#             return False
        
#         # メール内容を作成
#         subject = f"🏸 鶯サークル - 新しい質問が届きました"
        
#         # HTMLメール本文
#         html_body = f"""
#         <html>
#         <head>
#             <style>
#                 body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; }}
#                 .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
#                 .header {{ background-color: #8ea604; color: white; padding: 15px; border-radius: 8px 8px 0 0; text-align: center; }}
#                 .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
#                 .question {{ background-color: white; padding: 15px; border-left: 4px solid #8ea604; margin: 10px 0; font-size: 16px; line-height: 1.5; }}
#                 .info {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 15px 0; }}
#                 .footer {{ background-color: #f0f0f0; padding: 10px; font-size: 12px; color: #666; border-radius: 0 0 8px 8px; text-align: center; }}
#                 .btn {{ background-color: #8ea604; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
#                 .btn:hover {{ background-color: #76901e; }}
#                 ul {{ margin: 10px 0; padding-left: 20px; }}
#                 li {{ margin: 5px 0; }}
#             </style>
#         </head>
#         <body>
#             <div class="container">
#                 <div class="header">
#                     <h2>🏸 バドミントンサークル「鶯」</h2>
#                     <p style="margin: 5px 0;">新しい質問が届きました</p>
#                 </div>
                
#                 <div class="content">
#                     <h3 style="color: #8ea604; margin-top: 0;">📝 質問内容</h3>
#                     <div class="question">
#                         {question}
#                     </div>
                    
#                     <div class="info">
#                         <h4 style="color: #2c5282; margin-top: 0;">ℹ️ 詳細情報</h4>
#                         <ul style="margin: 0;">
#                             <li><strong>受信時刻:</strong> {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</li>
#                             <li><strong>送信者:</strong> {user_info.get('ip', '不明') if user_info else '不明'}</li>
#                             <li><strong>質問文字数:</strong> {len(question)}文字</li>
#                         </ul>
#                     </div>
                    
#                     <div style="text-align: center; margin: 20px 0;">
#                         <a href="http://127.0.0.1:7860" class="btn">💬 チャットボットを確認</a>
#                     </div>
#                 </div>
                
#                 <div class="footer">
#                     このメールは鶯バドミントンサークルのチャットボットから自動送信されています。<br>
#                     返信は不要です。
#                 </div>
#             </div>
#         </body>
#         </html>
#         """
        
#         # テキスト版も用意
#         text_body = f"""
# 🏸 バドミントンサークル「鶯」- 新しい質問

# 📝 質問内容:
# {question}

# ℹ️ 詳細情報:
# ・受信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
# ・送信者: {user_info.get('ip', '不明') if user_info else '不明'}
# ・質問文字数: {len(question)}文字

# 💬 チャットボットURL: http://127.0.0.1:7860

# ---
# このメールは鶯バドミントンサークルのチャットボットから自動送信されています。
#         """
        
#         # MIMEメッセージをテキストのみで作成
#         message = MIMEText(text_body, "plain", "utf-8")
#         message["Subject"] = subject
#         message["From"] = default_sender if default_sender else sender_email
#         message["To"] = notify_email
        
#         # OCNメール用のSMTP接続
#         print(f"[EMAIL] SMTP接続開始...")
        
#         if use_ssl:
#             # SSL接続（ポート465）
#             context = ssl.create_default_context()
#             with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
#                 print(f"[EMAIL] SSL接続確立")
#                 server.login(sender_email, sender_password)
#                 print(f"[EMAIL] ログイン成功")
#                 server.send_message(message)
#                 print(f"[EMAIL] メール送信完了")
#         elif use_tls:
#             # TLS接続（ポート587）
#             with smtplib.SMTP(smtp_server, smtp_port) as server:
#                 server.starttls()
#                 print(f"[EMAIL] TLS接続確立")
#                 server.login(sender_email, sender_password)
#                 print(f"[EMAIL] ログイン成功")
#                 server.send_message(message)
#                 print(f"[EMAIL] メール送信完了")
#         else:
#             # 通常接続
#             with smtplib.SMTP(smtp_server, smtp_port) as server:
#                 print(f"[EMAIL] 通常接続確立")
#                 server.login(sender_email, sender_password)
#                 print(f"[EMAIL] ログイン成功")
#                 server.send_message(message)
#                 print(f"[EMAIL] メール送信完了")
        
#         print(f"[EMAIL] 通知メール送信成功: {notify_email}")
#         return True
        
#     except Exception as e:
#         print(f"[EMAIL] メール送信失敗: {e}")
#         print(f"[EMAIL] エラータイプ: {type(e).__name__}")
        
#         # 詳細エラー情報
#         import traceback
#         print(f"[EMAIL] エラー詳細:")
#         traceback.print_exc()
        
#         return False
    






def send_email_notification(question: str, user_info: Optional[dict] = None) -> bool:
    """
    新しい質問をOCNメールで通知する
    
    Args:
        question: ユーザーの質問内容
        user_info: ユーザー情報（IPアドレス、時刻など）
    
    Returns:
        bool: 送信成功時True、失敗時False
    """
    try:
        # OCNメール設定を環境変数から取得
        smtp_server = os.getenv("MAIL_SERVER", "smtp.ocn.ne.jp")
        smtp_port = int(os.getenv("MAIL_PORT", "465"))
        use_ssl = os.getenv("MAIL_USE_SSL", "True").lower() == "true"
        use_tls = os.getenv("MAIL_USE_TLS", "False").lower() == "true"
        sender_email = os.getenv("MAIL_USERNAME")
        sender_password = os.getenv("MAIL_PASSWORD")
        notify_email = os.getenv("MAIL_NOTIFICATION_RECIPIENT")
        default_sender = os.getenv("MAIL_DEFAULT_SENDER")
        
        print(f"[EMAIL] メール設定確認:")
        print(f"  サーバー: {smtp_server}:{smtp_port}")
        print(f"  SSL: {use_ssl}, TLS: {use_tls}")
        print(f"  送信者: {sender_email}")
        print(f"  受信者: {notify_email}")
        
        if not all([sender_email, sender_password, notify_email]):
            print("[EMAIL] 必須のメール設定が不完全です")
            print(f"  MAIL_USERNAME: {'設定済み' if sender_email else '未設定'}")
            print(f"  MAIL_PASSWORD: {'設定済み' if sender_password else '未設定'}")
            print(f"  MAIL_NOTIFICATION_RECIPIENT: {'設定済み' if notify_email else '未設定'}")
            return False
        
        # メール内容を作成
        subject = f"🏸 鶯サークル - 新しい質問が届きました"
        
        # テキスト版メール本文
        text_body = f"""
🏸 バドミントンサークル「鶯」- 新しい質問

📝 質問内容:
{question}

ℹ️ 詳細情報:
・受信時刻: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
・送信者: {user_info.get('ip', '不明') if user_info else '不明'}
・質問文字数: {len(question)}文字

💬 チャットボットURL: http://127.0.0.1:7860

---
このメールは鶯バドミントンサークルのチャットボットから自動送信されています。
        """
        
        # MIMEメッセージをテキストのみで作成
        message = MIMEText(text_body, "plain", "utf-8")
        message["Subject"] = subject
        message["From"] = default_sender if default_sender else sender_email
        message["To"] = notify_email
        
        # 送信前の最終確認
        print(f"[EMAIL] メッセージサイズ: {len(message.as_string())} bytes")
        print(f"[EMAIL] 件名: {subject}")
        
        # OCNメール用のSMTP接続
        print(f"[EMAIL] SMTP接続開始...")
        
        if use_ssl:
            # SSL接続（ポート465）
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=context)
            print(f"[EMAIL] SSL接続確立")
            
            server.login(sender_email, sender_password)
            print(f"[EMAIL] ログイン成功")
            
            # ここが重要！送信結果を確認
            result = server.sendmail(sender_email, notify_email, message.as_string())
            
            # 結果詳細確認
            if result:
                print(f"[EMAIL] 送信エラー: {result}")
                server.quit()
                return False
            else:
                print("[EMAIL] SMTP受理成功（空の辞書）")
                
            # SMTP応答コード確認
            try:
                noop_result = server.noop()
                print(f"[EMAIL] 最後のSMTP応答: {noop_result}")
            except Exception as noop_e:
                print(f"[EMAIL] NOOP応答確認失敗: {noop_e}")
            
            server.quit()
            print(f"[EMAIL] メール送信完了")
            
        elif use_tls:
            # TLS接続（ポート587）
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            print(f"[EMAIL] TLS接続確立")
            
            server.login(sender_email, sender_password)
            print(f"[EMAIL] ログイン成功")
            
            # 送信結果を確認
            result = server.sendmail(sender_email, notify_email, message.as_string())
            
            if result:
                print(f"[EMAIL] 送信エラー: {result}")
                server.quit()
                return False
            else:
                print("[EMAIL] SMTP受理成功（空の辞書）")
                
            try:
                noop_result = server.noop()
                print(f"[EMAIL] 最後のSMTP応答: {noop_result}")
            except Exception as noop_e:
                print(f"[EMAIL] NOOP応答確認失敗: {noop_e}")
            
            server.quit()
            print(f"[EMAIL] メール送信完了")
            
        else:
            # 通常接続
            server = smtplib.SMTP(smtp_server, smtp_port)
            print(f"[EMAIL] 通常接続確立")
            
            server.login(sender_email, sender_password)
            print(f"[EMAIL] ログイン成功")
            
            # 送信結果を確認
            result = server.sendmail(sender_email, notify_email, message.as_string())
            
            if result:
                print(f"[EMAIL] 送信エラー: {result}")
                server.quit()
                return False
            else:
                print("[EMAIL] SMTP受理成功（空の辞書）")
                
            try:
                noop_result = server.noop()
                print(f"[EMAIL] 最後のSMTP応答: {noop_result}")
            except Exception as noop_e:
                print(f"[EMAIL] NOOP応答確認失敗: {noop_e}")
            
            server.quit()
            print(f"[EMAIL] メール送信完了")
        
        print(f"[EMAIL] 通知メール送信成功: {notify_email}")
        return True
        
    except Exception as e:
        print(f"[EMAIL] メール送信失敗: {e}")
        print(f"[EMAIL] エラータイプ: {type(e).__name__}")
        
        # 詳細エラー情報
        import traceback
        print(f"[EMAIL] エラー詳細:")
        traceback.print_exc()
        
        return False


def send_email_async(question: str, user_info: Optional[dict] = None):
    """
    非同期でメール送信（チャットボットの応答速度を下げないため）
    """
    def send_in_background():
        try:
            print(f"[EMAIL] バックグラウンドでメール送信開始")
            result = send_email_notification(question, user_info)
            if result:
                print(f"[EMAIL] バックグラウンド送信成功")
            else:
                print(f"[EMAIL] バックグラウンド送信失敗")
        except Exception as e:
            print(f"[EMAIL] バックグラウンド送信エラー: {e}")
    
    # バックグラウンドスレッドで実行
    thread = threading.Thread(target=send_in_background, daemon=True)
    thread.start()
    print(f"[EMAIL] メール送信スレッド開始")