import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI
import json
import requests # 🌐 구글 클라우드 대신 인터넷 통신으로 데이터를 보냅니다.

# --- 0. 스타일 및 디자인 세팅 (실시간 서버 한글 폰트 강제 주입) ---
import matplotlib as mpl
import matplotlib.font_manager as fm
import os

# 스트림릿 리눅스 서버용 나눔 고딕 다운로드 꼼수 적용
@st.cache_resource
def load_korean_font():
    # 인터넷 주소에서 나눔고딕 폰트 파일을 직접 다운로드합니다.
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "./NanumGothic.ttf"
    if not os.path.exists(font_path):
        import requests
        res = requests.get(font_url)
        with open(font_path, "wb") as f:
            f.write(res.content)
    # 다운로드한 폰트를 Matplotlib 시스템에 등록합니다.
    fm.font_manager.addfont(font_path)
    return fm.FontProperties(fname=font_path).get_name()

try:
    korean_font_name = load_korean_font()
    mpl.rcParams['font.family'] = korean_font_name
except Exception:
    mpl.rcParams['font.family'] = 'sans-serif'

mpl.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font=mpl.rcParams['font.family'])

# --- 🛠️ 구글 클라우드 없이 시트에 데이터 전송하는 함수 ---
def save_data_without_google_cloud(headline, source, bias_risk, clickbait_risk, feedback):
    """구글 양식(Google Forms) 기술을 이용해 시트에 완전 무료/무인증으로 저장하는 함수"""
    try:
        # 스트림릿 시크릿에서 구글 폼 양식 주소를 가져옵니다.
        form_url = st.secrets["google_form"]["url"]
        
        # 구글 시트와 연결된 입력 칸들의 고유 ID와 매칭합니다.
        data = {
            st.secrets["google_form"]["entry_headline"]: headline,
            st.secrets["google_form"]["entry_source"]: source,
            st.secrets["google_form"]["entry_bias"]: str(bias_risk),
            st.secrets["google_form"]["entry_clickbait"]: str(clickbait_risk),
            st.secrets["google_form"]["entry_feedback"]: feedback
        }
        # 데이터를 구글 서버로 전송합니다 (인증키 불필요!)
        requests.post(form_url, data=data)
        return True
    except Exception as e:
        print(f"[Save Error] {str(e)}")
        return False

# --- 1. 미디어 균형 분석 GPT 엔진 (다양성 강화 버전) ---
class AdvancedEthicsAnalyzer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def analyze_with_gpt(self, headline, source):
        prompt = f"""
        당신은 사용자가 미디어의 홍수 속에서 '생각의 중심'을 잡도록 돕는 독창적이고 날카로운 미디어 밸런스 가이드입니다.
        다음 뉴스 헤드라인과 언론사 정보가 사용자의 '시선'을 특정 방향으로 왜곡하거나, 포털 알고리즘을 한쪽으로 치우치게 만들 위험이 있는지 분석하여 JSON 형식으로 응답하세요.
        
        [뉴스 헤드라인]: "{headline}"
        [언론사/출처]: "{source}"
        
        [🚨 중요 - 답변 다양성 확보 가이드]:
        - 'detailed_reason'와 'one_line_summary'를 작성할 때 절대 뻔하고 정형화된 틀로 시작하지 마세요.
        - 헤드라인에 쓰인 구체적인 단어나 사회적 맥락을 정확히 짚어내어 매번 '서로 완전히 다른 분석 내용'이 나오도록 개성 있게 작성하세요.
        
        [응답 형식 (JSON)]:
        {{
            "sentiment_score": -1.0에서 1.0 사이의 실수,
            "bias_risk": 1에서 10 사이의 정수 (시선 왜곡도),
            "clickbait_risk": 1에서 10 사이의 정수 (제목 자극성),
            "detailed_reason": "프레임 분석 및 포털 추천 알고리즘 오염 부작용 설명 (3~4문장)",
            "one_line_summary": "기사 내용에 매칭되는 위트 있고 날카로운 한 줄 경고 문구"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.85 
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "sentiment_score": 0.0, "bias_risk": 1, "clickbait_risk": 1, 
                "detailed_reason": f"분석 중 오류 발생: {str(e)}", "one_line_summary": "⚠️ 분석 실패"
            }

# --- 2. 웹 화면 구성 및 세션 상태 초기화 ---
st.set_page_config(layout="wide", page_title="뉴스 생각-중심 필터", page_icon="⚖️")
st.title("⚖️ 뉴스 생각-중심 필터 (News Balance Filter)")
st.warning("🎯 **이 서비스가 왜 필요할까요?** 뉴스를 읽다 보면 나도 모르게 세상에 대한 '색안경'이 끼워지곤 합니다. 한쪽으로 치우친 뉴스를 자꾸 클릭하면, 포털 알고리즘마저 내 피드를 편향된 정보로만 가득 채우게 됩니다.")
st.markdown("---")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("🚨 `Secrets`에 `OPENAI_API_KEY`를 설정해 주세요.")
    st.stop()

if 'analytics_history' not in st.session_state:
    st.session_state.analytics_history = []
if 'feedback_dict' not in st.session_state:
    st.session_state.feedback_dict = {}

with st.sidebar:
    st.header("🔍 균형 잡힌 뉴스 읽기")
    with st.form(key='news_input_form', clear_on_submit=True):
        input_headline = st.text_input("📝 뉴스 제목 입력")
        input_source = st.text_input("🏢 신문사 / 출처")
        submit_button = st.form_submit_button(label="⚡ 시선 왜곡도 측정 시작")

if submit_button:
    if not input_headline or not input_source:
        st.sidebar.warning("뉴스 제목과 신문사를 모두 입력해 주세요!")
    else:
        analyzer = AdvancedEthicsAnalyzer(api_key=api_key)
        with st.spinner("⚖️ AI가 뉴스를 다각도로 진단 중입니다..."):
            gpt_res = analyzer.analyze_with_gpt(input_headline, input_source)
            
            new_record = {
                '뉴스 헤드라인': input_headline, '언론사/출처': input_source,
                '감성 점수': gpt_res['sentiment_score'], '시선 왜곡도': gpt_res['bias_risk'], 
                '제목 자극성': gpt_res['clickbait_risk'], 'AI 미디어 가이드의 분석 소견': gpt_res['detailed_reason'],
                '추천 피드 오염 위험 요약': gpt_res['one_line_summary'],
                '감성 판정': '🟢 긍정적' if gpt_res['sentiment_score'] > 0.1 else ('🔴 부정/갈등' if gpt_res['sentiment_score'] < -0.1 else '🟡 단순 사실')
            }
            st.session_state.analytics_history.append(new_record)
        st.rerun()

# --- 3. 대시보드 출력 레이아웃 ---
if st.session_state.analytics_history:
    result_df = pd.DataFrame(st.session_state.analytics_history)

    # 1층: 스코어보드
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1: st.metric(label="📊 모니터링한 뉴스", value=f"{len(result_df)} 건")
    with col_m2: st.metric(label="👓 평균 시선 왜곡도", value=f"{result_df['시선 왜곡도'].mean():.1f} / 10.0")
    with col_m3: st.metric(label="🎣 평균 제목 자극성", value=f"{result_df['제목 자극성'].mean():.1f} / 10.0")

    st.markdown("---")

    # 2층: 데이터 테이블
    st.subheader("📋 실시간 뉴스 균형 진단 기록")
    result_df['유저 피드백'] = result_df['뉴스 헤드라인'].apply(lambda x: st.session_state.feedback_dict.get(x, '⏳ 확인 대기'))
    st.dataframe(result_df[['언론사/출처', '뉴스 헤드라인', '시선 왜곡도', '제목 자극성', '감성 판정', '유저 피드백']], use_container_width=True, hide_index=True)

    st.markdown("---")

    # 3층: 통계 그래프 (한글 깨짐 절대 방어 치트키 버전)
    st.subheader("📊 매체별 시선 편향 및 자극성 성향")
    
    # 1. 인터넷에서 나눔고딕 폰트 파일을 강제로 다운로드하여 경로를 확보합니다.
    import os, requests
    import matplotlib.font_manager as fm
    
    font_path = "./NanumGothic.ttf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        res = requests.get(font_url)
        with open(font_path, "wb") as f:
            f.write(res.content)
            
    # 2. 다운로드한 폰트 파일로 직접 FontProperties 오브젝트를 생성합니다 (핵심 ⭐)
    k_font = fm.FontProperties(fname=font_path)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5)) 
    
    # --- 왼쪽 그래프: 왜곡도 ---
    media_bias = result_df.groupby('언론사/출처')['시선 왜곡도'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='시선 왜곡도', data=media_bias, ax=axes[0], palette="Oranges_r", hue='언론사/출처', legend=False)
    
    # 글자가 들어가는 모든 요소에 fontproperties=k_font 를 억지로 쑤셔 넣습니다.
    axes[0].set_title('신문사별 평균 시선 왜곡도 (1-10)', fontproperties=k_font, fontsize=14, fontweight='bold')
    axes[0].set_ylabel('왜곡 점수 (1~10)', fontproperties=k_font, fontsize=11)
    axes[0].set_xlabel('신문사', fontproperties=k_font, fontsize=11)
    axes[0].set_ylim(0, 10)
    # X축에 들어가는 신문사 이름(예: 네이버, OO일보) 글씨 깨짐 방지
    for tick in axes[0].get_xticklabels():
        tick.set_fontproperties(k_font)
        tick.set_fontsize(10)

    # --- 오른쪽 그래프: 자극성 ---
    media_bait = result_df.groupby('언론사/출처')['제목 자극성'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='제목 자극성', data=media_bait, ax=axes[1], palette="Purples_r", hue='언론사/출처', legend=False)
    
    # 여기도 모든 텍스트에 fontproperties=k_font 를 강제 적용합니다.
    axes[1].set_title('신문사별 평균 제목 자극성 (1-10)', fontproperties=k_font, fontsize=14, fontweight='bold')
    axes[1].set_ylabel('자극 점수 (1~10)', fontproperties=k_font, fontsize=11)
    axes[1].set_xlabel('신문사', fontproperties=k_font, fontsize=11)
    axes[1].set_ylim(0, 10)
    # X축에 들어가는 신문사 이름 글씨 깨짐 방지
    for tick in axes[1].get_xticklabels():
        tick.set_fontproperties(k_font)
        tick.set_fontsize(10)
    
    plt.tight_layout()
    st.pyplot(fig)

    # 4층: 정밀 보고서 및 구글 전송 트리거
    st.subheader("🕵️‍♂️ AI 미디어 가이드의 정밀 진단 소견")
    recent_records = result_df.tail(3).iloc[::-1]
    tabs = st.tabs([f"⏱️ {i+1}번째 전 뉴스" for i in range(len(recent_records))])
    
    for idx, (original_idx, row) in enumerate(recent_records.iterrows()):
        headline_key = row['뉴스 헤드라인']
        with tabs[idx]:
            col_b1, col_b2 = st.columns([1, 4])
            with col_b1:
                st.markdown(f"**🏢 신문사:** {row['언론사/출처']}")
                st.markdown(f"**시선 왜곡도:** `{row['시선 왜곡도']}/10`  \n**제목 자극성:** `{row['제목 자극성']}/10`")
                st.markdown("---")
                st.markdown("**🤖 분석에 동의하시나요?**")
                
                current_feedback = st.session_state.feedback_dict.get(headline_key, None)
                if current_feedback is None:
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        if st.button("👍 공감해요", key=f"like_{original_idx}"):
                            st.session_state.feedback_dict[headline_key] = "👍 공감함"
                            with st.spinner("통계 데이터 전송 중..."):
                                save_data_without_google_cloud(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 왜곡도'], row['제목 자극성'], "👍 공감함")
                            st.rerun()
                    with col_f2:
                        if st.button("👎 글쎄요", key=f"dislike_{original_idx}"):
                            st.session_state.feedback_dict[headline_key] = "👎 동의 안 함"
                            with st.spinner("통계 데이터 전송 중..."):
                                save_data_without_google_cloud(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 왜곡도'], row['제목 자극성'], "👎 동의 안 함")
                            st.rerun()
                else:
                    st.success(f"참여 완료: {current_feedback}")
            with col_b2:
                st.markdown(f"📝 **뉴스 제목:** \"{row['뉴스 헤드라인']}\"")
                st.info(row['AI 미디어 가이드의 분석 소견'])
                st.warning(f"🎯 {row['추천 피드 오염 위험 요약']}")
else:
    st.info("👋 뉴스 제목을 왼쪽 사이드바에 입력하여 생각의 중심을 지키는 필터를 작동시켜 보세요!")
