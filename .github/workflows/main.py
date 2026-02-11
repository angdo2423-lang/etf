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
        if res.status_code == 200 and len(res.content) > 1000:
            # bytes 데이터를 BytesIO로 읽어서 엑셀 변환
            return pd.read_excel(io.BytesIO(res.content))
    except Exception as e:
        print(f"데이터 로딩 에러 ({date_str}): {str(e)}")
    return None

# 2. 네이버 메일 발송 함수 (HTML 지원)
def send_naver_email(subject, html_body):
    user = os.environ.get('EMAIL_USER', '').strip()
    pw = os.environ.get('EMAIL_PASS', '').strip()
    to = os.environ.get('RECEIVER_EMAIL', '').strip()

    if not user or not pw or not to:
        print("❌ [설정오류] GitHub Secrets 값이 비어있습니다. Repository Secrets를 확인하세요.")
        return

    msg = MIMEMultipart()
    msg['From'] = user
    msg['To'] = to
    msg['Subject'] = subject
    
    # HTML 형식으로 본문 부착
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL("smtp.naver.com", 465) as server:
            server.login(user, pw)
            # RFC-5322 규격을 준수하기 위해 sendmail 방식 사용
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
        
        merged = pd.merge(t_sub, y_sub, on='종목명', how='outer').fillna(0)
        merged['증감(P)'] = merged['오늘(%)'] - merged['어제(%)']
        result = merged.sort_values(by='오늘(%)', ascending=False).head(30).round(2)
        
        # --- HTML 표 스타일링 ---
        # 증감에 따른 색상 정의 함수
        def color_pick(val):
            if val > 0: return 'color: #d9534f; font-weight: bold;' # 빨강 (상승)
            if val < 0: return 'color: #0275d8; font-weight: bold;' # 파랑 (하락)
            return 'color: #333;' # 검정 (변동없음)

        # 스타일 적용 (증감 컬럼)
        styled_result = result.style.applymap(color_pick, subset=['증감(P)']) \
                                    .format("{:.2f}") \
                                    .hide(axis='index') # 인덱스 숨기기

        # CSS 스타일 시트
        html_style = """
        <style>
            .report-container { font-family: 'Malgun Gothic', dotum, sans-serif; line-height: 1.6; color: #333; }
            table { border-collapse: collapse; width: 100%; max-width: 600px; margin-top: 10px; font-size: 14px; }
            th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 12px; text-align: center; border-bottom: 2px solid #ccc; }
            td { border: 1px solid #dee2e6; padding: 10px; text-align: right; }
            td:first-child { text-align: left; background-color: #fafafa; font-weight: bold; } /* 종목명 열 */
            .header-info { margin-bottom: 20px; padding: 15px; background-color: #f1f3f5; border-radius: 5px; }
        </style>
        """

        html_table = styled_result.to_html()

        full_html = f"""
        <html>
        <head>{html_style}</head>
        <body>
            <div class="report-container">
                <div class="header-info">
                    <h2 style="margin:0; color:#212529;">🚀 TIME 미국나스닥100 액티브 분석</h2>
                    <p style="margin:5px 0 0 0; color:#666;">데이터 기준일: <b>{today_str}</b></p>
                </div>
                {html_table}
                <p style="font-size: 12px; color: #999; margin-top: 20px;">
                    * 본 메일은 GitHub Actions를 통해 자동으로 생성 및 발송되었습니다.
                </p>
            </div>
        </body>
        </html>
        """
        
        send_naver_email(f"[ETF 분석] {today_str} 포트폴리오 리포트", full_html)
    else:
        print(f"❌ {today_str} 데이터가 아직 업데이트되지 않았습니다.")

if __name__ == "__main__":
    run_analysis()
