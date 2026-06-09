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

# --- 0. 스타일 및 디자인 세팅 (한글 폰트 강제 로드 유틸리티) ---
font_path = "./NanumGothic.ttf"
if not os.path.exists(font_path):
    try:
        res = requests.get("https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf")
        with open(font_path, "wb") as f:
            f.write(res.content)
    except Exception as e:
        print(f"[Font Download Error] {e}")

# Matplotlib에 폰트 등록 및 시스템 기본 폰트로 강제 설정하여 경고 원천 차단 ⭐
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

# --- 2. 페이지 설정 및 데이터 초기화 ---
st.set_page_config(layout="wide", page_title="뉴스 생각-중심 필터", page_icon="⚖️")
st.title("⚖️ 뉴스 편향도 분석기 (News Balance Filter)")

if 'input_headline' not in st.session_state: st.session_state.input_headline = ""
if 'input_source' not in st.session_state: st.session_state.input_source = ""
if 'analytics_history' not in st.session_state: st.session_state.analytics_history = []
if 'feedback_dict' not in st.session_state: st.session_state.feedback_dict = {}

st.warning("""
🎯 **알고리즘의 '편식'에서 벗어나세요!** 이 서비스는 뉴스의 시선 편향도를 분석하여 당신의 미디어 리터러시를 돕습니다.
🚨 **[데이터 수집 안내]** 분석 결과 하단에서 **공감/글쎄요** 버튼을 누르시면 해당 데이터가 연구용 DB(GitHub)로 실시간 전송됩니다. 성실한 참여 부탁드립니다!
""")

HOT_ISSUES = [
    {"title": "의대 증원 갈등 심화, 의료 공백 장기화 조짐", "source": "중앙일보"},
    {"title": "대통령 거부권 행사, 여야 대치 정국 급랭", "source": "한겨레 신문"},
    {"title": "금리 동결 결정에 영끌족 한숨, 부동산 시장 어디로?", "source": "조선 일보"},
    {"title": "AI 반도체 전쟁, 한국 기업들의 생존 전략은?", "source": "매일 경제"},
    {"title": "기후 위기 현실화, 올여름 역대급 폭염 예고", "source": "SBS 뉴스"},
    {"title": "포털 알고리즘이 우리 사회를 분열시키는 방법", "source": "네이바 뉴스"}
]

with st.sidebar:
    st.header("🔍 균형 잡힌 뉴스 읽기")
    
    with st.form(key='news_input_form', clear_on_submit=False):
        input_h = st.text_input("📝 뉴스 제목 입력", value=st.session_state.input_headline)
        input_s = st.text_input("🏢 신문사 / 출처", value=st.session_state.input_source)
        submit_button = st.form_submit_button(label="⚡ 시선 편향도 측정 시작")

    st.markdown("---")
    st.subheader("💡 입력하기 귀찮으신가요?")
    
    if st.button("🎲 오늘의 랜덤 뉴스 추천"):
        picked = random.choice(HOT_ISSUES)
        st.session_state.input_headline = picked['title']
        st.session_state.input_source = picked['source']
        st.toast("랜덤 뉴스가 입력창에 채워졌습니다!")
        st.rerun()

    st.markdown("👇 **아래 트렌드 뉴스를 클릭하면 자동 입력됩니다.**")
    for issue in HOT_ISSUES:
        # [이전 피드백 반영] 마우스 올리면(help) 전체 제목이 말풍선 툴팁으로 뜨도록 보완 ⭐
        if st.button(f"🔥 {issue['title'][:18]}...", key=issue['title'], help=issue['title']):
            st.session_state.input_headline = issue['title']
            st.session_state.input_source = issue['source']
            st.toast("선택한 뉴스가 입력창에 채워졌습니다!")
            st.rerun()

    st.markdown("---")
    st.header("📊 진단 지표 평가 기준")
    metrics_data = {"점수 범위": ["1~3점", "4~7점", "8~10점"], "시선 편향도": ["🟢 객관적/중립적", "🟡 은근한 시선 유도", "🔴 특정 진영 편중"], "제목 자극성": ["🟢 담백한 사실 전달", "🟡 호기심 유발 유도", "🔴 낚시성/선동"]}
    st.table(pd.DataFrame(metrics_data))

# --- 3. 분석 실행 및 출력 ---
try: api_key = st.secrets["OPENAI_API_KEY"]
except: st.error("🚨 Secrets 설정 필요"); st.stop()

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

# --- 대시보드 레이아웃 ---
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
    
    # 🌟 [FutureWarning 해결] hue를 x값과 동일하게 주고 legend=False 처리!
    # 그래프 1: 편향도
    bias_data = result_df.groupby('언론사/출처')['시선 편향도'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='시선 편향도', data=bias_data, ax=axes[0], palette="Oranges_r", hue='언론사/출처', legend=False)
    axes[0].set_title('신문사별 평균 시선 편향도', fontproperties=k_font, fontsize=12)
    axes[0].set_xlabel('언론사/출처', fontproperties=k_font)
    axes[0].set_ylabel('시선 편향도', fontproperties=k_font)
    
    # 그래프 2: 자극성
    bait_data = result_df.groupby('언론사/출처')['제목 자극성'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='제목 자극성', data=bait_data, ax=axes[1], palette="Purples_r", hue='언론사/출처', legend=False)
    axes[1].set_title('신문사별 평균 제목 자극성', fontproperties=k_font, fontsize=12)
    axes[1].set_xlabel('언론사/출처', fontproperties=k_font)
    axes[1].set_ylabel('제목 자극성', fontproperties=k_font)
    
    # 🌟 [UserWarning 해결] 축 눈금 글자 폰트까지 싹 잡아 한글 안 깨지게 방어
    for ax in axes:
        if k_font:
            for t in ax.get_xticklabels(): t.set_fontproperties(k_font)
            for t in ax.get_yticklabels(): t.set_fontproperties(k_font)
            
    st.pyplot(fig)

    st.markdown("---")
    st.subheader("🕵️‍♂️ AI의 정밀 진단 소견")
    recent = result_df.tail(3).iloc[::-1]
    tabs = st.tabs([f"⏱️ {i+1}번째 분석 뉴스" for i in range(len(recent))])
    for idx, (o_idx, row) in enumerate(recent.iterrows()):
        with tabs[idx]:
            c1, c2 = st.columns([1, 3])
            with c1:
                st.write(f"**🏢 {row['언론사/출처']}**")
                st.write(f"편향도: `{row['시선 편향도']}` | 자극성: `{row['제목 자극성']}`")
                key = row['뉴스 헤드라인']
                if st.session_state.feedback_dict.get(key) is None:
                    if st.button("👍 공감해요", key=f"L_{o_idx}"):
                        st.session_state.feedback_dict[key] = "공감"
                        save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "공감")
                        st.rerun()
                    if st.button("👎 글쎄요", key=f"D_{o_idx}"):
                        st.session_state.feedback_dict[key] = "비공감"
                        save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "비공감")
                        st.rerun()
                else: st.success(f"참여 완료: {st.session_state.feedback_dict[key]}")
            with c2:
                st.info(row['AI의 미디어 가이드 분석 소견'])
                st.warning(row['추천 피드 오염 위험 요약'])
else:
    st.info("👋 왼쪽 사이드바에서 뉴스를 직접 입력하거나 '랜덤 뉴스 추천'을 클릭해 분석을 시작해보세요!")
