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
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200 and len(res.content) > 1000:
            # bytes 데이터를 BytesIO로 감싸서 전달
            return pd.read_excel(io.BytesIO(res.content))
    except Exception as e:
        print(f"데이터 로드 실패 ({date_str}): {str(e)}")
    return None

def send_naver_email(subject, body):
    # 환경변수를 읽어올 때 기본값으로 빈 문자열 설정
    sender_email = os.environ.get('EMAIL_USER', '')
    sender_pass = os.environ.get('EMAIL_PASS', '')
    receiver_email = os.environ.get('RECEIVER_EMAIL', '')

    if not sender_email or not sender_pass:
        print("❌ 에러: Secrets(ID/PW)를 찾을 수 없습니다. 설정 확인 필수!")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    # 본문(body)을 확실하게 str 타입으로 변환하여 인코딩 설정
    msg.attach(MIMEText(str(body), 'plain', 'utf-8'))

    try:
        # SMTP_SSL을 사용하여 네이버 서버 연결
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(sender_email, sender_pass)
            server.send_message(msg)
        print("✅ 네이버 메일 발송 성공!")
    except Exception as e:
        # 에러 메시지를 강제로 문자열로 변환하여 출력
        print(f"❌ 메일 발송 중 실제 에러 발생: {str(e)}")

# 실행부
today = datetime.now()
today_str = today.strftime('%Y-%m-%d')
yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')

df_today = get_pdf_data(today_str)
df_yesterday = get_pdf_data(yesterday_str)

if df_today is not None and df_yesterday is not None:
    # 컬럼명 처리 (비중% vs 비중)
    col_name = '비중(%)' if '비중(%)' in df_today.columns else '비중'
    
    t_sub = df_today[['종목명', col_name]].rename(columns={col_name: '오늘(%)'})
    y_sub = df_yesterday[['종목명', col_name]].rename(columns={col_name: '어제(%)'})
    
    merged = pd.merge(t_sub, y_sub, on='종목명', how='outer').fillna(0)
    merged['증감(P)'] = merged['오늘(%)'] - merged['어제(%)']
    result = merged.sort_values(by='오늘(%)', ascending=False).head(30).round(2)
    
    # 텍스트로 변환
    content = f"🚀 TIME 미국나스닥100 액티브 분석 ({today_str})\n"
    content += "-" * 50 + "\n"
    content += result.to_string(index=False)
    
    send_naver_email(f"[ETF 분석] {today_str} 포트폴리오 변동 현황", content)
else:
    print(f"❌ {today_str} 데이터를 불러오지 못했습니다. 장 시작 전이거나 데이터 미업데이트 상태입니다.")
