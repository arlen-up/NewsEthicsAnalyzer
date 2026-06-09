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
def save_data_to_github(headline, source, bias_risk, clickbait_risk, feedback, user_comment=""):
    try:
        GITHUB_TOKEN = st.secrets["github"]["token"]
        REPO_NAME = st.secrets["github"]["repo"]
        FILE_PATH = "data.csv"
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        
        res = requests.get(url, headers=headers)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_row = pd.DataFrame([{
            "날짜": current_time, 
            "뉴스 제목": headline, 
            "신문사": source, 
            "시선 편향도": bias_risk, 
            "제목 자극성": clickbait_risk, 
            "유저 피드백": feedback,
            "유저 상세 의견": user_comment if user_comment else "작성 안 함"
        }])
        
        if res.status_code == 200:
            file_data = res.json()
            sha = file_data["sha"]
            from base64 import b64decode
            existing_content = b64decode(file_data["content"]).decode("utf-8-sig")
            old_df = pd.read_csv(io.StringIO(existing_content))
            
            if "유저 상세 의견" not in old_df.columns:
                old_df["유저 상세 의견"] = "작성 안 함"
                
            updated_df = pd.concat([old_df, new_row], ignore_index=True)
        else:
            sha = None
            updated_df = new_row
            
        csv_buffer = io.StringIO()
        updated_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        from base64 import b64encode
        content_encoded = b64encode(csv_buffer.getvalue().encode("utf-8-sig")).decode("utf-8")
        put_data = {"message": "🔥 데이터 적재 (유저 상세 의견 포함)", "content": content_encoded}
        if sha: put_data["sha"] = sha
        requests.put(url, headers=headers, json=put_data)
        return True
    except: return False

# --- 1. GPT 분석 엔진 (유저 상세 피드백 오답노트 학습 루프 반영) ---
class AdvancedEthicsAnalyzer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def analyze_with_gpt(self, headline, source, learning_context=""):
        feedback_learning_prompt = ""
        if learning_context:
            feedback_learning_prompt = f"""
            [⚠️ 중요 유저 피드백 및 상세 코멘트 자가 학습 사항]
            과거 당신의 뉴스 편향 분석 결과에 대해 유저들이 아래와 같은 실망 섞인 코멘트와 함께 '비공감(별로에요)' 의견을 남겼습니다.
            이 오답노트 내용을 철저히 분석해서, 유저가 왜 당신의 판단에 실망했는지 파악하고 이번 분석에 강력히 반영하세요.
            
            수정해야 할 과거 분석 실패 사례와 유저들의 생생한 한 줄 평 리스트:
            {learning_context}
            
            위 유저 피드백을 토대로, 이번 분석에서는 기계적이거나 수박 겉핥기식 분석을 탈피하여 왜 이 뉴스가 그렇게 분석되었는지 맥락을 날카롭고 유용하게 파고들어야 합니다.
            """

        prompt = f"""
        당신은 미디어 리터러시를 쉽고 재밌게 알려주는 친근한 '뉴스 탐정'이자 텍스트 정제 전문가입니다.
        제공된 뉴스 제목과 언론사를 바탕으로, 딱딱하고 전문적인 용어 대신 동네 친한 형/누나가 이야기하듯 쉽고 친근하게(해요체, ~요, ~죠 사용) 숨겨진 프레임을 해부해 주세요.
        
        [뉴스 제목]: "{headline}"
        [신문사]: "{source}"
        
        {feedback_learning_prompt}
        
        [진단 임무 및 기준]
        1. 텍스트 정제: 신문사명(cleaned_source)과 뉴스 뉴스 제목(cleaned_headline)의 오타나 불필요한 특수문자를 정제하고 표준 명칭으로 교정하세요.
        2. 시선 편향도(bias_risk, 1-10): 특정 이념, 집단, 진영의 이해관계를 대변하거나 갈등을 부추기는 감정적 어휘가 투영되었는지 평가하세요.
        3. 제목 자극성(clickbait_risk, 1-10): 인과관계 생략, 과장된 형용사 사용, 자극적 단어 배치로 독자의 낚시성 클릭을 유도하는지 평가하세요.
        4. 정밀 심층 소견(detailed_reason): 반드시 일반 대중도 직관적으로 이해할 수 있는 비유와 친근한 대화체 문장으로 아래 3가지 테마를 명확히 구분하여 작성하세요.
           - [🕵️‍♂️ 뉴스 속 숨은 의도]: 이 제목이 은근슬쩍 대중에게 어떤 생각이나 프레임을 심어주려고 판을 짜고 있는지 쉽고 친근하게 설명
           - [🧐 제목 뒤 숨겨진 사실]: 독자의 눈을 가리기 위해 제목에서 일부러 말 안 하거나 구렁이 담 넘어가듯 생략해 버린 진짜 핵심 팩트나 배경 추론
           - [💡 다시 읽어볼까요?]: 이 뉴스를 볼 때 확증 편향이나 낚시에 당하지 않고 중심을 잡기 위해 독자가 가져야 할 유쾌하고 명쾌한 비판적 자세 제안
        
        응답은 반드시 철저하게 아래 JSON 형식을 준수해야 합니다:
        {{
            "cleaned_source": "정제된 신문사명",
            "cleaned_headline": "정제된 뉴스 제목",
            "sentiment_score": -1.0~1.0 사이 실수,
            "bias_risk": 1~10 정수,
            "clickbait_risk": 1~10 정수,
            "detailed_reason": "[🕵️‍♂️ 뉴스 속 숨은 의도]\\n(쉽고 친근한 분석 내용, 해요체로 작성)\\n\\n[🧐 제목 뒤 숨겨진 팩트]\\n(쉽고 친근한 분석 내용, 해요체로 작성)\\n\\n[💡 다시 읽어볼까요?]\\n(쉽고 친근한 분석 내용, 해요체로 작성)",
            "one_line_summary": "독자의 확증 편향을 깨부수는 위트 있고 날카로운 한 줄 경고 요약"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.4
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "cleaned_source": source, 
                "cleaned_headline": headline, 
                "sentiment_score": 0.0, 
                "bias_risk": 1, 
                "clickbait_risk": 1, 
                "detailed_reason": f"[에러 발생] 분석에 실패했어요.\n\n원인: {e}", 
                "one_line_summary": "⚠️ 분석 실패"
            }

# --- 2. 📡 실시간 구글 뉴스 대량 크롤링 엔진 (10분 캐싱 고정) ---
@st.cache_data(ttl=600)  
def get_realtime_large_news_pool():
    try:
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "xml")
            items = soup.find_all("item")
            
            realtime_issues = []
            for item in items:
                if len(realtime_issues) >= 35:
                    break
                if item and item.title and item.title.text:
                    title_raw = item.title.text.strip()
                    if " - " in title_raw:
                        parts = title_raw.rsplit(" - ", 1)
                        title = parts[0].strip()
                        source = parts[1].strip()
                    else:
                        title = title_raw
                        source = "실시간 뉴스"
                        
                    if title and len(title) > 5:
                        realtime_issues.append({"title": title, "source": source})
            
            if len(realtime_issues) >= 10:
                return realtime_issues
    except Exception as e:
        print(f"[뉴스 크롤링 실패] {e}")
    
    return [
        {"title": "정부, 실시간 민생 안정 대책 및 경제 활성화 방안 발표", "source": "종합뉴스"},
        {"title": "글로벌 기술 박람회 개막, 차세대 AI 혁신 기술 대거 공개", "source": "IT한국"},
        {"title": "올해 여름 역대급 폭염 우려, 기후 위기 대응책 긴급 점검", "source": "환경일보"},
        {"title": "한국 중앙은행, 기준 금리 동결 결정... 시장 전망은?", "source": "경제신문"}
    ]

TOTAL_NEWS_POOL = get_realtime_large_news_pool()
HOT_ISSUES = TOTAL_NEWS_POOL[:6]

# --- 3. 페이지 설정 및 데이터 초기화 ---
st.set_page_config(layout="wide", page_title="뉴스 생각-중심 필터", page_icon="⚖️")
st.title("⚖️ 뉴스 편향도 분석기 (News Balance Filter)")

if 'input_headline' not in st.session_state: st.session_state.input_headline = ""
if 'input_source' not in st.session_state: st.session_state.input_source = ""
if 'analytics_history' not in st.session_state: st.session_state.analytics_history = []
if 'feedback_dict' not in st.session_state: st.session_state.feedback_dict = {}

# 🌟 메인 화면 안내 구역: (데이터가 없을 때만 노출하도록 조건 추가)
if not st.session_state.analytics_history:
    st.warning("""
    🎯 **알고리즘의 '편식'에서 벗어나세요!** 이 프로젝트는 뉴스의 시선 편향도를 분석하여 당신의 이해를 돕습니다.

    ---

    ### 🔍 왜 이 프로젝트는 '본문'이 아닌 '헤드라인'만 분석할까요?

    현대인들이 뉴스 한 편을 끝까지 읽는 비율은 갈수록 줄어들고 있으며, 대다수는 SNS나 포털 화면에서 **오직 '헤드라인'만 훑어보고 세상사를 판단**합니다. 바쁜 뇌가 에너지를 아끼려는 본능(인지적 구두쇠) 때문이죠.

    문제는 언론사와 알고리즘이 바로 이 점을 파고든다는 것입니다. 본문에는 평범한 내용을 적어두고도, **제목에는 자극적인 어휘, 인과관계 생략, 은근한 진영 프레임**을 심어 독자의 생각과 클릭을 교묘하게 유도합니다. 제목을 보는 그 짧은 3초 동안 우리의 무의식은 이미 오염되는 셈입니다.

    따라서 본 프로젝트는 **미디어 편향성과 선동이 일어나는 '최전선'이 바로 헤드라인**이라는 점에 주목했습니다. 본문 뒤에 숨어 제목으로 장난치는 프레임을 날카롭게 해부하여, 여러분이 단 3초짜리 헤드라인만 보고도 낚이지 않는 '단단한 방패'를 채워드리는 것이 이 프로젝트의 존재 이유입니다! 😎

    ---

    ### 🧠 여러분의 '한 줄 평'이 AI 탐정을 성장시킵니다!

    분석 결과 아래에 있는 피드백 공간에 여러분의 날카로운 생각이나 판단 이유(한 줄 평)를 남겨주세요! 

    여러분이 남겨주신 생생한 피드백은 데이터베이스에 안전하게 저장된 후, **GPT 분석 엔진의 '오답노트'이자 학습 데이터로 실시간 반영**됩니다. AI가 미처 보지 못한 인간의 정교한 맥락과 피드백을 직접 읽고 스스로의 편향성을 교정하며 진화하는 **'집단지성형 자가 학습 루프'**에 동참해 주세요! 🚀

    ---
    🚨 **[이용자 필수 안내 및 데이터 수집 경고]**
    1. 본 서비스는 AI를 활용한 뉴스 데이터 편향 연구 및 분석 과제의 일환으로 운영됩니다.
    2. 분석 결과 하단의 **[🕵️‍♂️ AI의 정밀 진단 소견 및 집단지성 피드백]** 구역에서 **`👍 공감해요`** 또는 **`👎 글쎄요`** 버튼을 꼭 눌러주세요.
    3. **버튼을 누르시는 순간, 입력하신 [뉴스 제목, 신문사, AI 분석 지표, 선택한 피드백, 유저 의견(선택)] 데이터가 개발자의 데이터베이스(GitHub 저장소)로 안전하게 실시간 전송 및 적재됩니다.**
    4. 수집된 정보는 통계 분석 목적으로만 활용되며, 개인 식별 정보는 일절 수집되지 않습니다. 신중하고 성실한 피드백 참여에 감사드립니다!
    """)

# --- 🚀 사이드바 레이아웃 ---
with st.sidebar:
    st.header("🔍 균형 잡힌 뉴스 읽기")
    
    with st.form(key='news_input_form', clear_on_submit=False):
        input_h = st.text_input("📝 뉴스 제목 입력", value=st.session_state.input_headline)
        input_s = st.text_input("🏢 신문사 / 출처", value=st.session_state.input_source)
        submit_button = st.form_submit_button(label="⚡ 시선 편향도 측정 시작")

    st.markdown("---")
    st.subheader("💡 입력하기 귀찮으신가요?")
    
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
    
    st.markdown("""
| 점수 범위 | 시선 편향도 | 제목 자극성 |
| :--- | :--- | :--- |
| **1~3점** | 🟢 **객관적 / 중립적** | 🟢 **담백한 사실 전달** |
| **4~7점** | 🟡 **은근한 시선 유도** | 🟡 **호기심 유발 유도** |
| **8~10점** | 🔴 **특정 진영 편중** | 🔴 **낚시성 / 선동** |
""")

# --- 4. 분석 실행 가동 제어 ---
try: api_key = st.secrets["OPENAI_API_KEY"]
except: st.error("🚨 Secrets에 OPENAI_API_KEY 설정이 필요합니다."); st.stop()

try:
    token = st.secrets["github"]["token"]
    repo = st.secrets["github"]["repo"]
    csv_url = f"https://raw.githubusercontent.com/{repo}/main/data.csv"
    db_res = requests.get(csv_url, headers={"Authorization": f"token {token}"})
    global_df = pd.read_csv(io.StringIO(db_res.text)) if db_res.status_code == 200 else pd.DataFrame()
except:
    global_df = pd.DataFrame()

if submit_button:
    if not input_h or not input_s:
        st.sidebar.warning("입력창을 채워주세요!")
    else:
        # 비공감 피드백과 함께 유저가 남긴 정성 코멘트 데이터를 추출하여 GPT 오답노트 컨텍스트 구성
        learning_context = ""
        if not global_df.empty and '유저 피드백' in global_df.columns:
            disliked_samples = global_df[global_df['유저 피드백'] == '비공감'].tail(5)
            if not disliked_samples.empty:
                context_list = []
                for _, r in disliked_samples.iterrows():
                    headline_col = r['뉴스 뉴스 제목' if '뉴스 뉴스 제목' in global_df.columns else '뉴스 제목']
                    comment_val = r.get('유저 상세 의견', '의견 미작성')
                    context_list.append(f"- 뉴스명: {headline_col} [유저 한줄평: {comment_val}]")
                learning_context = "\n".join(context_list)

        analyzer = AdvancedEthicsAnalyzer(api_key=api_key)
        with st.spinner("⚖️ AI 진단 중..."):
            gpt_res = analyzer.analyze_with_gpt(input_h, input_s, learning_context=learning_context)
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
    
    st.dataframe(
        result_df[['언론사/출처', '뉴스 헤드라인', '시선 편향도', '제목 자극성', '유저 피드백']], 
        width=1200, 
        hide_index=True,
        column_config={
            "언론사/출처": st.column_config.TextColumn("🏢 언론사/출처"),
            "뉴스 헤드라인": st.column_config.TextColumn("📰 뉴스 헤드라인"),
            "시선 편향도": st.column_config.TextColumn("👓 시선 편향도"),
            "제목 자극성": st.column_config.TextColumn("🎣 제목 자극성"),
            "유저 피드백": st.column_config.TextColumn("👥 유저 피드백")
        }
    )
    
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
                        else: st.caption("아직 피드백을 남긴 유저가 없습니다.")
                    else: st.caption("이 뉴스를 분석한 첫 번째 주자입니다! 🥇")
                else: st.caption("⏳ 데이터베이스 연결을 확인 중입니다.")
                
                st.markdown("---")
                st.write("**🤖 당신의 분석 의견은 어떤가요?**")
                
                if st.session_state.feedback_dict.get(key) is None:
                    user_note = st.text_input("💬 판단하신 이유나 한 줄 평을 남겨주세요 (선택)", key=f"note_{o_idx}", placeholder="예: 분석이 정확해요 / 프레임 왜곡이 심하네요.")
                    
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("👍 공감해요", key=f"L_{o_idx}"):
                            st.session_state.feedback_dict[key] = "공감"
                            save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "공감", user_comment=user_note)
                            st.toast("피드백이 수집되었습니다! 통계가 실시간 갱신됩니다.")
                            st.rerun()
                    with col_b2:
                        if st.button("👎 글쎄요", key=f"D_{o_idx}"):
                            st.session_state.feedback_dict[key] = "비공감"
                            save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "비공감", user_comment=user_note)
                            st.toast("피드백을 반영했습니다! 다음 분석에 오답노트로 자동 활용됩니다.")
                            st.rerun()
                else:
                    st.success(f"참여 완료: {st.session_state.feedback_dict[key]}")
            with c2:
                st.markdown("### 🔍 AI 심층 진단 리포트")
                st.markdown(row['AI의 미디어 가이드 분석 소견'])
                st.markdown("---")
                st.warning(row['추천 피드 오염 위험 요약'])
else:
    st.info("👋 왼쪽 사이드바에서 뉴스를 직접 입력하거나 아래의 '실시간 트렌드 메뉴'를 클릭해 분석을 시작해보세요!")
