import pandas as pd
import requests
import io
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# 1. 데이터 가져오기 함수
def get_pdf_data(date_str):
    url = f"https://timeetf.co.kr/pdf_excel.php?idx=2&cate=&pdfDate={date_str}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        # 데이터가 정상적으로 수신되었는지 확인 (최소 크기 체크)
        if res.status_code == 200 and len(res.content) > 1000:
            return pd.read_excel(io.BytesIO(res.content))
    except Exception as e:
        print(f"데이터 로딩 에러 ({date_str}): {str(e)}")
    return None

# 2. 네이버 메일 발송 함수
def send_naver_email(subject, html_body):
    user = os.environ.get('EMAIL_USER', '').strip()
    pw = os.environ.get('EMAIL_PASS', '').strip()
    to = os.environ.get('RECEIVER_EMAIL', '').strip()

    if not user or not pw or not to:
        print("❌ [설정오류] GitHub Secrets 값이 비어있습니다.")
        return

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(user, pw)
            server.sendmail(user, to, msg.as_string())
        print("✅ 네이버 메일 발송 성공!")
    except Exception as e:
        print(f"❌ 메일 발송 실패: {str(e)}")

# 3. 데이터 분석 및 HTML 리포트 생성
def run_analysis():
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = (today - timedelta(days=1)).strftime('%Y-%m-%d')

    print(f"분석 시작: {today_str}")
    
    df_today = get_pdf_data(today_str)
    df_yesterday = get_pdf_data(yesterday_str)

    if df_today is not None and df_yesterday is not None:
        # 컬럼명 유연하게 대응
        col_name = '비중(%)' if '비중(%)' in df_today.columns else '비중'
        
        t_sub = df_today[['종목명', col_name]].rename(columns={col_name: '오늘(%)'})
        y_sub = df_yesterday[['종목명', col_name]].rename(columns={col_name: '어제(%)'})
        
        # 데이터 병합 및 전처리
        merged = pd.merge(t_sub, y_sub, on='종목명', how='outer').fillna(0)
        
        # 숫자 타입 강제 변환 (문자열이 섞여 있어 발생하는 ValueError 방지)
        num_cols = ['오늘(%)', '어제(%)']
        for col in num_cols:
            merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0)
            
        merged['증감(P)'] = merged['오늘(%)'] - merged['어제(%)']
        result = merged.sort_values(by='오늘(%)', ascending=False).head(30)
        
        # --- HTML 표 스타일링 ---
        def color_pick(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #d9534f; font-weight: bold;'  # 빨강
                if val < 0: return 'color: #0275d8; font-weight: bold;'  # 파랑
            return 'color: #333;'

        # 스타일 적용 (map 사용 및 format 수정)
        styled_result = result.style \
            .map(color_pick, subset=['증감(P)']) \
            .format("{:.2f}", subset=['오늘(%)', '어제(%)', '증감(P)']) \
            .hide(axis='index')

        # CSS 스타일 시트
        html_style = """
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', Arial, sans-serif; 
                background-color: #f5f7fa;
                padding: 20px;
            }
            .report-container { 
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 30px;
            }
            .header-info { 
                margin-bottom: 30px;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 8px;
                color: white;
            }
            .header-info h2 {
                margin: 0 0 8px 0;
                font-size: 24px;
                font-weight: 700;
            }
            .header-info p {
                margin: 0;
                opacity: 0.95;
                font-size: 14px;
            }
            table { 
                border-collapse: separate;
                border-spacing: 0;
                width: 100%;
                margin-top: 20px;
                font-size: 13px;
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                overflow: hidden;
            }
            thead th { 
                background-color: #f8f9fc;
                color: #2d3748;
                font-weight: 600;
                padding: 14px 12px;
                text-align: center;
                border-bottom: 2px solid #e1e8ed;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            tbody tr {
                transition: background-color 0.2s;
            }
            tbody tr:hover {
                background-color: #f7fafc;
            }
            tbody tr:nth-child(even) {
                background-color: #fcfcfd;
            }
            td { 
                padding: 12px;
                text-align: right;
                border-bottom: 1px solid #f0f0f0;
                color: #2d3748;
            }
            td:first-child { 
                text-align: left;
                font-weight: 600;
                color: #1a202c;
                max-width: 250px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            tbody tr:last-child td {
                border-bottom: none;
            }
            .footer-note {
                margin-top: 25px;
                padding-top: 20px;
                border-top: 1px solid #e1e8ed;
                font-size: 12px;
                color: #718096;
                text-align: center;
            }
        </style>
        """

        html_table = styled_result.to_html()

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {html_style}
        </head>
        <body>
            <div class="report-container">
                <div class="header-info">
                    <h2>🚀 TIME 미국나스닥100 액티브 분석</h2>
                    <p>데이터 기준일: <b>{today_str}</b></p>
                </div>
                {html_table}
                <div class="footer-note">
                    📊 본 메일은 GitHub Actions를 통해 자동으로 생성되었습니다.
                </div>
            </div>
        </body>
        </html>
        """
        
        send_naver_email(f"[ETF 분석] {today_str} 포트폴리오 리포트", full_html)
    else:
        # 데이터가 없을 때의 로그 출력 강화
        print(f"⚠️ {today_str} 또는 {yesterday_str} 데이터를 가져오지 못했습니다. 업데이트 전이거나 URL을 확인하세요.")

if __name__ == "__main__":
    run_analysis()
