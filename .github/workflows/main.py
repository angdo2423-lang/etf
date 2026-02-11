import pandas as pd
import requests
import io
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# ... (get_pdf_data 함수는 그대로 유지) ...

def send_naver_email(subject, html_body):
    user = os.environ.get('EMAIL_USER', '').strip()
    pw = os.environ.get('EMAIL_PASS', '').strip()
    to = os.environ.get('RECEIVER_EMAIL', '').strip()

    if not user or not pw:
        print("❌ [설정오류] GitHub Secrets 값이 비어있습니다.")
        return

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = to
    msg['Subject'] = subject
    
    # [수정] 메일 형식을 'html'로 설정
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(user, pw)
            server.sendmail(user, to, msg.as_string())
        print("✅ HTML 메일 발송 성공!")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {str(e)}")

# --- 실행 로직 ---
today_str = datetime.now().strftime('%Y-%m-%d')
yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

df_today = get_pdf_data(today_str)
df_yesterday = get_pdf_data(yesterday_str)

if df_today is not None and df_yesterday is not None:
    col_name = '비중(%)' if '비중(%)' in df_today.columns else '비중'
    t_sub = df_today[['종목명', col_name]].rename(columns={col_name: '오늘(%)'})
    y_sub = df_yesterday[['종목명', col_name]].rename(columns={col_name: '어제(%)'})
    
    merged = pd.merge(t_sub, y_sub, on='종목명', how='outer').fillna(0)
    merged['증감(P)'] = merged['오늘(%)'] - merged['어제(%)']
    result = merged.sort_values(by='오늘(%)', ascending=False).head(30).round(2)
    
    # [추가] HTML 스타일 지정 (표 테두리, 폰트 등)
    html_style = """
    <style>
        table { border-collapse: collapse; width: 100%; max-width: 600px; font-family: sans-serif; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        .plus { color: red; }
        .minus { color: blue; }
    </style>
    """
    
    # [추가] 데이터프레임을 HTML 표로 변환
    html_table = result.to_html(index=False, classes='etf_table')
    
    # 최종 HTML 본문 구성
    full_html = f"""
    <html>
    <head>{html_style}</head>
    <body>
        <h2>🚀 ETF 포트폴리오 분석 리포트</h2>
        <p>날짜: {today_str}</p>
        <hr>
        {html_table}
        <br>
        <p style='font-size: 12px; color: #888;'>* 본 메일은 GitHub Actions를 통해 자동 발송되었습니다.</p>
    </body>
    </html>
    """
    
    send_naver_email(f"[ETF 분석] {today_str} 리포트", full_html)
else:
    print(f"❌ {today_str} 데이터를 가져올 수 없습니다.")
