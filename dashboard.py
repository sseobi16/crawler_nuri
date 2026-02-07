import streamlit as st
import pandas as pd
import os
import time

# 1. 페이지 설정
st.set_page_config(
    page_title="누리장터 모니터링",
    layout="wide"
)

st.title("📊 누리장터 입찰공고 실시간 크롤링 대시보드")
st.markdown("---")

EXCEL_FILE = "data/nuri_data.xlsx"

# 2. 데이터 로드
def load_data():
    if not os.path.exists(EXCEL_FILE):
        return pd.DataFrame()
    try:
        return pd.read_excel(EXCEL_FILE)
    except Exception:
        return pd.DataFrame()

# 3. 사이드바 
with st.sidebar:
    st.header("⚙️ 모니터링 설정")
    auto_refresh = st.checkbox('실시간 자동 새로고침 (5초)', value=True)
    
    if st.button("수동 새로고침"):
        st.rerun()
    
    st.markdown("---")
    st.info("크롤러가 생성한 엑셀 파일을\n실시간으로 시각화합니다.")


# 4. 메인 화면
df = load_data()

if df.empty:
    st.warning("⚠️ 아직 데이터가 없습니다. 크롤러가 10개 이상 수집할 때까지 기다려주세요.")
else:
    # 주요 지표
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 총 수집 공고", f"{len(df)}건")
    
    last_time = df['수집일시'].max() if '수집일시' in df.columns else "-"
    col2.metric("⏱️ 최근 수집", str(last_time)[5:16]) 
    
    file_count = df['첨부파일_개수'].sum() if '첨부파일_개수' in df.columns else 0
    col3.metric("📎 수집된 파일 수", f"{file_count}개")

    # 검색 필터
    st.subheader("🔍 데이터 검색")
    search = st.text_input("검색어 입력", placeholder="입찰 방식, 공고명 등 키워드로 검색")

    display_df = df
    if search:
        mask = df.apply(lambda x: x.astype(str).str.contains(search, case=False).any(), axis=1)
        display_df = df[mask]

    # (3) 최신순 정렬 및 표시
    if '수집일시' in display_df.columns:
        display_df = display_df.sort_values(by='수집일시', ascending=False)

    st.dataframe(display_df, width="stretch", height=700, hide_index=True)

# 5. 자동 새로고침 로직
if auto_refresh:
    time.sleep(5)
    st.rerun()