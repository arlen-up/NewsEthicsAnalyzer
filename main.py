import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI
import json
import requests
from datetime import datetime
import io
import random
import os  
import matplotlib.font_manager as fm
from bs4 import BeautifulSoup  

# --- 0. 스타일 및 디자인 세팅 (한글 폰트 무결성 확보) ---
font_path = "./NanumGothic.ttf"
if not os.path.exists(font_path):
    try:
        res = requests.get("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf")
        with open(font_path, "wb") as f:
            f.write(res.content)
    except Exception as e:
        print(f"[Font Download Error] {e}")

if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    import matplotlib as mpl
    mpl.rcParams['font.family'] = prop.get_name()
    mpl.rcParams['axes.unicode_minus'] = False

sns.set_theme(style="whitegrid")

# --- 🛠️ 깃허브 저장소의 CSV 파일에 실시간 누적 저장하는 함수 ---
def save_data_to_github(headline, source, bias_risk, clickbait_risk, feedback):
    try:
        GITHUB_TOKEN = st.secrets["github"]["token"]
        REPO_NAME = st.secrets["github"]["repo"]
        FILE_PATH = "data.csv"
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        
        res = requests.get(url, headers=headers)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame([{"날짜": current_time, "뉴스 제목": headline, "신문사": source, "시선 편향도": bias_risk, "제목 자극성": clickbait_risk, "유저 피드백": feedback}])
        
        if res.status_code == 200:
            file_data = res.json()
            sha = file_data["sha"]
            from base64 import b64decode
            existing_content = b64decode(file_data["content"]).decode("utf-8-sig")
            old_df = pd.read_csv(io.StringIO(existing_content))
            updated_df = pd.concat([old_df, new_row], ignore_index=True)
        else:
            sha = None
            updated_df = new_row
            
        csv_buffer = io.StringIO()
        updated_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        from base64 import b64encode
        content_encoded = b64encode(csv_buffer.getvalue().encode("utf-8-sig")).decode("utf-8")
        put_data = {"message": "🔥 데이터 적재", "content": content_encoded}
        if sha: put_data["sha"] = sha
        requests.put(url, headers=headers, json=put_data)
        return True
    except: return False

# --- 1. GPT 분석 엔진 ---
class AdvancedEthicsAnalyzer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def analyze_with_gpt(self, headline, source):
        prompt = f"""
        당신은 뉴스 텍스트 정제 전문가이자 미디어 밸런스 가이드입니다.
        [임무] 
        1. 신문사명(cleaned_source)과 뉴스 제목(cleaned_headline)의 오타/탈자를 표준 명칭으로 교정하세요.
        2. 뉴스 제목의 시선 편향도(bias_risk, 1-10)와 제목 자극성(clickbait_risk, 1-10)을 분석하세요.
        
        [뉴스 제목]: "{headline}"
        [신문사]: "{source}"
        
        응답은 반드시 아래 JSON 형식을 지키세요:
        {{
            "cleaned_source": "정제된 신문사명",
            "cleaned_headline": "정제된 뉴스 제목",
            "sentiment_score": -1.0~1.0 사이 실수,
            "bias_risk": 1~10 정수,
            "clickbait_risk": 1~10 정수,
            "detailed_reason": "분석 소견(3~4문장)",
            "one_line_summary": "날카로운 한 줄 요약"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"cleaned_source": source, "cleaned_headline": headline, "sentiment_score": 0.0, "bias_risk": 1, "clickbait_risk": 1, "detailed_reason": f"에러: {e}", "one_line_summary": "⚠️ 분석 실패"}

# --- 2. 📡 실시간 구글 뉴스 대량 크롤링 엔진 (수정 포인트 🌟) ---
@st.cache_data(ttl=600)  
def get_realtime_large_news_pool():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.page_content, features="xml")
            items = soup.find_all("item")
            
            realtime_issues = []
            # 랜덤 샘플링 폭을 넓히기 위해 상위 35개의 실시간 뉴스를 넉넉하게 긁어옵니다!
            for item in items[:35]:  
                title_raw = item.title.text
                if " - " in title_raw:
                    title, source = title_raw.rsplit(" - ", 1)
                else:
                    title, source = title_raw, "실시간 뉴스"
                realtime_issues.append({"title": title.strip(), "source": source.strip()})
            return realtime_issues
    except Exception as e:
        print(f"[뉴스 크롤링 실패] {e}")
    
    # 크롤링 실패 시 백업 풀
    return [{"title": f"백업 실시간 이슈 뉴스 {i}", "source": "종합뉴스"} for i in range(1, 10)]

# 전체 35개짜리 대형 뉴스 풀 확보!
TOTAL_NEWS_POOL = get_realtime_large_news_pool()
# 대시보드 리스트용으로는 기존처럼 최상위 6개만 슬라이싱해서 지정!
HOT_ISSUES = TOTAL_NEWS_POOL[:6]

# --- 3. 페이지 설정 및 데이터 초기화 ---
st.set_page_config(layout="wide", page_title="뉴스 생각-중심 필터", page_icon="⚖️")
st.title("⚖️ 뉴스 편향도 분석기 (News Balance Filter)")

if 'input_headline' not in st.session_state: st.session_state.input_headline = ""
if 'input_source' not in st.session_state: st.session_state.input_source = ""
if 'analytics_history' not in st.session_state: st.session_state.analytics_history = []
if 'feedback_dict' not in st.session_state: st.session_state.feedback_dict = {}

st.warning("""
🎯 **알고리즘의 '편식'에서 벗어나세요!** 이 서비스는 뉴스의 시선 편향도를 분석하여 당신의 미디어 리터러시를 돕습니다.

---
🚨 **[이용자 필수 안내 및 데이터 수집 경고]**
1. 본 서비스는 AI를 활용한 뉴스 데이터 편향 연구 및 분석 과제의 일환으로 운영됩니다.
2. 분석 결과 하단의 **[🕵️‍♂️ AI의 정밀 진단 소견 및 집단지성 피드백]** 구역에서 **`👍 공감해요`** 또는 **`👎 글쎄요`** 버튼을 꼭 눌러주세요.
3. **버튼을 누르시는 순간, 입력하신 [뉴스 제목, 신문사, AI 분석 지표, 선택한 피드백] 데이터가 개발자의 데이터베이스(GitHub 저장소)로 안전하게 실시간 전송 및 적재됩니다.**
4. 수집된 정보는 통계 분석 목적으로만 활용되며, 개인 식별 정보는 일절 수집되지 않습니다. 신중하고 성실한 피드백 참여에 감사드립니다!
""")

# --- 🚀 사이드바 레이아웃 (진짜 실시간 무작위 추천 적용) ---
with st.sidebar:
    st.header("🔍 균형 잡힌 뉴스 읽기")
    
    with st.form(key='news_input_form', clear_on_submit=False):
        input_h = st.text_input("📝 뉴스 제목 입력", value=st.session_state.input_headline)
        input_s = st.text_input("🏢 신문사 / 출처", value=st.session_state.input_source)
        submit_button = st.form_submit_button(label="⚡ 시선 편향도 측정 시작")

    st.markdown("---")
    st.subheader("💡 입력하기 귀찮으신가요?")
    
    # 🌟 [로직 변경 완료] 아래 리스트에 없는 35개의 넓은 풀에서 '진짜 실시간 랜덤' 추출!
    if st.button("🎲 실시간 랜덤 뉴스 추천"):
        picked = random.choice(TOTAL_NEWS_POOL)
        st.session_state.input_headline = picked['title']
        st.session_state.input_source = picked['source']
        st.toast("실시간 대형 뉴스 풀에서 무작위 1건을 추첨했습니다!")
        st.rerun()

    st.markdown("👇 **아래 실시간 트렌드를 클릭하면 자동 입력됩니다.**")
    for issue in HOT_ISSUES:
        if st.button(f"🔥 {issue['title'][:18]}...", key=issue['title'], help=issue['title']):
            st.session_state.input_headline = issue['title']
            st.session_state.input_source = issue['source']
            st.toast("선택한 뉴스가 입력창에 채워졌습니다!")
            st.rerun()

    st.markdown("---")
    st.header("📊 진단 지표 평가 기준")
    metrics_data = {
        "점수 범위": ["1~3점", "4~7점", "8~10점"], 
        "시선 편향도": ["🟢 객관적/중립적", "🟡 은근한 시선 유도", "🔴 특정 진영 편중"], 
        "제목 자극성": ["🟢 담백한 사실 전달", "🟡 호기심 유발 유도", "🔴 낚시성/선동"]
    }
    st.table(pd.DataFrame(metrics_data))

# --- 4. 분석 실행 가동 제어 ---
try: api_key = st.secrets["OPENAI_API_KEY"]
except: st.error("🚨 Secrets에 OPENAI_API_KEY 설정이 필요합니다."); st.stop()

if submit_button:
    if not input_h or not input_s:
        st.sidebar.warning("입력창을 채워주세요!")
    else:
        analyzer = AdvancedEthicsAnalyzer(api_key=api_key)
        with st.spinner("⚖️ AI 진단 중..."):
            gpt_res = analyzer.analyze_with_gpt(input_h, input_s)
            new_record = {
                '뉴스 헤드라인': gpt_res.get('cleaned_headline', input_h),
                '언론사/출처': gpt_res.get('cleaned_source', input_s),
                '감성 점수': gpt_res['sentiment_score'],
                '시선 편향도': gpt_res['bias_risk'],
                '제목 자극성': gpt_res['clickbait_risk'],
                'AI의 미디어 가이드 분석 소견': gpt_res['detailed_reason'],
                '추천 피드 오염 위험 요약': gpt_res['one_line_summary'],
                '감성 판정': '🟢 긍정적' if gpt_res['sentiment_score'] > 0.1 else ('🔴 부정/갈등' if gpt_res['sentiment_score'] < -0.1 else '🟡 단순 사실')
            }
            st.session_state.analytics_history.append(new_record)
        st.rerun()

# --- 5. 메인 화면 대시보드 레이아웃 출력 구역 ---
if st.session_state.analytics_history:
    result_df = pd.DataFrame(st.session_state.analytics_history)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📊 분석 뉴스", f"{len(result_df)} 건")
    col2.metric("👓 평균 편향도", f"{result_df['시선 편향도'].mean():.1f} / 10")
    col3.metric("🎣 평균 자극성", f"{result_df['제목 자극성'].mean():.1f} / 10")
    
    st.markdown("---")
    st.subheader("📋 뉴스 진단 기록")
    result_df['유저 피드백'] = result_df['뉴스 헤드라인'].apply(lambda x: st.session_state.feedback_dict.get(x, '⏳ 대기'))
    st.dataframe(result_df[['언론사/출처', '뉴스 헤드라인', '시선 편향도', '제목 자극성', '유저 피드백']], width=1200, hide_index=True)
    
    st.markdown("---")
    st.subheader("📊 매체별 편향성 통계")
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    k_font = fm.FontProperties(fname=font_path) if os.path.exists(font_path) else None
    
    bias_data = result_df.groupby('언론사/출처')['시선 편향도'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='시선 편향도', data=bias_data, ax=axes[0], palette="Oranges_r", hue='언론사/출처', legend=False)
    axes[0].set_title('신문사별 평균 시선 편향도', fontproperties=k_font, fontsize=12)
    axes[0].set_xlabel('언론사/출처', fontproperties=k_font)
    axes[0].set_ylabel('시선 편향도', fontproperties=k_font)
    
    bait_data = result_df.groupby('언론사/출처')['제목 자극성'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='제목 자극성', data=bait_data, ax=axes[1], palette="Purples_r", hue='언론사/출처', legend=False)
    axes[1].set_title('신문사별 평균 제목 자극성', fontproperties=k_font, fontsize=12)
    axes[1].set_xlabel('언론사/출처', fontproperties=k_font)
    axes[1].set_ylabel('제목 자극성', fontproperties=k_font)
    
    for ax in axes:
        if k_font:
            for t in ax.get_xticklabels(): t.set_fontproperties(k_font)
            for t in ax.get_yticklabels(): t.set_fontproperties(k_font)
            
    st.pyplot(fig)

    st.markdown("---")
    
    st.subheader("🕵️‍♂️ AI의 정밀 진단 소견 및 집단지성 피드백")
    recent = result_df.tail(3).iloc[::-1]
    tabs = st.tabs([f"⏱️ {i+1}번째 분석 뉴스" for i in range(len(recent))])
    
    try:
        token = st.secrets["github"]["token"]
        repo = st.secrets["github"]["repo"]
        csv_url = f"https://raw.githubusercontent.com/{repo}/main/data.csv"
        db_res = requests.get(csv_url, headers={"Authorization": f"token {token}"})
        global_df = pd.read_csv(io.StringIO(db_res.text)) if db_res.status_code == 200 else pd.DataFrame()
    except:
        global_df = pd.DataFrame()

    for idx, (o_idx, row) in enumerate(recent.iterrows()):
        key = row['뉴스 헤드라인']
        with tabs[idx]:
            c1, c2 = st.columns([1.5, 3])
            with c1:
                st.write(f"**🏢 {row['언론사/출처']}**")
                st.write(f"편향도: `{row['시선 편향도']}` | 자극성: `{row['제목 자극성']}`")
                st.markdown("---")
                
                st.markdown("👥 **다른 사람들의 피드백 통계**")
                if not global_df.empty and '뉴스 제목' in global_df.columns:
                    same_news = global_df[global_df['뉴스 제목'] == key]
                    if len(same_news) > 0:
                        likes = len(same_news[same_news['유저 피드백'] == '공감'])
                        dislikes = len(same_news[same_news['유저 피드백'] == '비공감'])
                        total = likes + dislikes
                        if total > 0:
                            st.info(f"이 뉴스는 총 **{total}명**이 평가했습니다.  \n"
                                    f"▶️ 👍 공감해요: `{likes}명` ({likes/total*100:.1f}%)  \n"
                                    f"▶️ 👎 글쎄요: `{dislikes}명` ({dislikes/total*100:.1f}%)")
                        else: st.caption("아직 버튼 피드백을 남긴 유저가 없습니다.")
                    else: st.caption("이 뉴스를 분석한 첫 번째 주자입니다! 🥇")
                else: st.caption("⏳ 데이터베이스 연결을 확인 중입니다.")
                
                st.markdown("---")
                st.write("**🤖 당신의 분석 의견은 어떤가요?**")
                
                if st.session_state.feedback_dict.get(key) is None:
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("👍 공감해요", key=f"L_{o_idx}"):
                            st.session_state.feedback_dict[key] = "공감"
                            save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "공감")
                            st.toast("피드백이 수집되었습니다! 통계가 실시간 갱신됩니다.")
                            st.rerun()
                    with col_b2:
                        if st.button("👎 글쎄요", key=f"D_{o_idx}"):
                            st.session_state.feedback_dict[key] = "비공감"
                            save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "비공감")
                            st.toast("피드백이 수집되었습니다! 통계가 실시간 갱신됩니다.")
                            st.rerun()
                else: st.success(f"참여 완료: {st.session_state.feedback_dict[key]}")
            with c2:
                st.info(row['AI의 미디어 가이드 분석 소견'])
                st.warning(row['추천 피드 오염 위험 요약'])
else:
    st.info("👋 왼쪽 사이드바에서 뉴스를 직접 입력하거나 아래의 '실시간 트렌드 메뉴'를 클릭해 분석을 시작해보세요!")
