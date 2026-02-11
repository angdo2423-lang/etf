import pandas as pd
import requests
import io
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

def get_pdf_data(date_str):
    url = f"https://timeetf.co.kr/pdf_excel.php?idx=2&cate=&pdfDate={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200 and len(res.content) > 1000:
            return pd.read_excel(io.BytesIO(res.content))
    except:
        return None
    return None

def send_naver_email(subject, body):
    # GitHub Secrets 설정값 가져오기
    sender_email = os.environ.get('EMAIL_USER')
    sender_pass = os.environ.get('EMAIL_PASS')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # 네이버 SMTP 서버 설정 (SSL 사용)
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(sender_email, sender_pass)
            server.send_message(msg)
        print("✅ 네이버 메일 발송 성공!")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {e}")

# 데이터 분석 실행
today_str = datetime.now().strftime('%Y-%m-%d')
yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

df_today = get_pdf_data(today_str)
df_yesterday = get_pdf_data(yesterday_str)

if df_today is not None and df_yesterday is not None:
    col_name = '비중(%)' if '비중(%)' in df_today.columns else '비중'
    today_sub = df_today[['종목명', col_name]].rename(columns={col_name: '오늘(%)'})
    yesterday_sub = df_yesterday[['종목명', col_name]].rename(columns={col_name: '어제(%)'})
    
    merged = pd.merge(today_sub, yesterday_sub, on='종목명', how='outer').fillna(0)
    merged['증감(P)'] = merged['오늘(%)'] - merged['어제(%)']
    result = merged.sort_values(by='오늘(%)', ascending=False).round(2)
    
    # 상위 30개 종목 리포트 작성
    content = f"🚀 TIME 미국나스닥100 액티브 분석 ({today_str})\n"
    content += "-" * 50 + "\n"
    content += result.head(30).to_string(index=False)
    
    send_naver_email(f"[ETF 분석] {today_str} 포트폴리오 변동 현황", content)
else:
    print("❌ 데이터를 불러오지 못했습니다. (장 시작 전이거나 휴장일일 수 있습니다.)")
