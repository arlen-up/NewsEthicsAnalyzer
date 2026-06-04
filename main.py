import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI
import json

# --- 0. 스타일 및 디자인 세팅 ---
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid", font="AppleGothic")

# --- 1. 일반 사용자 친화적인 미디어 균형 분석 GPT 엔진 ---
class AdvancedEthicsAnalyzer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def analyze_with_gpt(self, headline):
        prompt = f"""
        당신은 사용자가 미디어의 홍수 속에서 휩쓸리지 않고 '생각의 중심'을 잡도록 돕는 미디어 밸런스 가이드입니다.
        다음 뉴스 헤드라인이 사용자의 '시선'을 특정 방향으로 왜곡하거나, 포털 알고리즘을 한쪽으로 치우치게 만들 위험이 있는지 분석하여 JSON 형식으로 응답하세요.
        
        [뉴스 헤드라인]: "{headline}"
        
        [분석 및 채점 지침 - 10점 만점]:
        1. 'bias_risk' (핵심 - 시선 왜곡 위험도): 1점(객관적 사실)부터 10점(특정 진영/집단에 대한 선입견이나 색안경을 강하게 씌우는 뉴스)까지 채점하세요.
        2. 'clickbait_risk' (보조 - 제목 자극성): 이 왜곡된 시선을 퍼뜨리기 위해 제목에 얼마나 자극적인 어휘(충격, 경악, 결국 등)를 썼는지 1~10점으로 채점하세요.
        
        [응답 형식 (JSON)]:
        {{
            "sentiment_score": -1.0에서 1.0 사이의 실수,
            "bias_risk": 1에서 10 사이의 정수 (시선 왜곡 위험도),
            "clickbait_risk": 1에서 10 사이의 정수 (제목 자극성),
            "detailed_reason": "이 뉴스가 일상적인 사용자의 시각에 어떤 색안경을 끼우려 하는지, 그리고 이 기사를 무심코 클릭했을 때 사용자의 포털 추천 피드(알고리즘)가 어떻게 한쪽으로 치우치게 되는지 그 부작용을 친절하게 설명하세요 (3~4문장)",
            "one_line_summary": "⚠️ 알고리즘 치우침 경고 요약"
        }}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "sentiment_score": 0.0, 
                "bias_risk": 1, 
                "clickbait_risk": 1, 
                "detailed_reason": f"분석 중 오류 발생: {str(e)}",
                "one_line_summary": "⚠️ 분석 실패"
            }

# --- 2. 웹 화면 구성 및 세션 상태 초기화 (Streamlit) ---
st.set_page_config(layout="wide", page_title="뉴스 생각-중심 필터", page_icon="⚖️")

# 🌟 일반 사용자 눈높이에 맞춘 타이틀과 안내 (뇌 ➡️ 시선, 생각의 중심)
st.title("⚖️ 뉴스 생각-중심 필터 (News Balance Filter)")
st.warning("🎯 **이 서비스가 왜 필요할까요?** 뉴스를 읽다 보면 나도 모르게 세상에 대한 '색안경'이 끼워지곤 합니다. 한쪽으로 치우친 뉴스를 자꾸 클릭하면, 포털 알고리즘마저 내 피드를 편향된 정보로만 가득 채우게 됩니다. 이 필터는 제목 뒤에 숨은 **시선 왜곡과 추천 피드 오염을 방어하여 내 생각의 중심을 지켜주는 일상 도구**입니다.")
st.markdown("---")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    st.error("🚨 `.streamlit/secrets.toml` 파일에 `OPENAI_API_KEY`를 설정해 주세요.")
    st.stop()

if 'analytics_history' not in st.session_state:
    st.session_state.analytics_history = []
if 'feedback_dict' not in st.session_state:
    st.session_state.feedback_dict = {}

# [사이드바] 문구 친근하게 변경
with st.sidebar:
    st.header("🔍 균형 잡힌 뉴스 읽기")
    st.markdown("유독 자극적이거나 한쪽 의견만 담은 듯한 뉴스 제목이 있다면 검사해 보세요.")
    
    with st.form(key='news_input_form', clear_on_submit=True):
        input_headline = st.text_input("📝 뉴스 제목 입력", placeholder="예: [충격] 결국 드러난 그 집단의 본색... 난리 났다")
        input_source = st.text_input("🏢 신문사 / 출처", placeholder="예: OO일보")
        submit_button = st.form_submit_button(label="⚡ 시선 왜곡도 측정 시작")

if submit_button:
    if not input_headline or not input_source:
        st.sidebar.warning("뉴스 제목과 신문사를 모두 입력해 주세요!")
    else:
        analyzer = AdvancedEthicsAnalyzer(api_key=api_key)
        with st.spinner("⚖️ AI가 뉴스 속 '색안경'과 '알고리즘 치우침 위험'을 분석하고 있습니다..."):
            gpt_res = analyzer.analyze_with_gpt(input_headline)
            
            new_record = {
                '뉴스 헤드라인': input_headline,
                '언론사/출처': input_source,
                '감성 점수': gpt_res['sentiment_score'],
                '시선 왜곡도': gpt_res['bias_risk'], # 일반 사용자용 용어 변경
                '제목 자극성': gpt_res['clickbait_risk'], # 일반 사용자용 용어 변경
                'AI 미디어 가이드의 분석 소견': gpt_res['detailed_reason'],
                '추천 피드 오염 위험 요약': gpt_res['one_line_summary'],
                '감성 판정': '🟢 긍정적 뉘앙스' if gpt_res['sentiment_score'] > 0.1 else ('🔴 부정/갈등 유도' if gpt_res['sentiment_score'] < -0.1 else '🟡 단순 사실 전달')
            }
            st.session_state.analytics_history.append(new_record)
        st.rerun()

# --- 3. 대시보드 레이아웃 ---
if st.session_state.analytics_history:
    result_df = pd.DataFrame(st.session_state.analytics_history)

    # 1층: 스코어보드
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(label="📊 모니터링한 뉴스", value=f"{len(result_df)} 건")
    with col_m2:
        avg_bias = result_df['시선 왜곡도'].mean()
        bias_status = "⚠️ 치우침 위험" if avg_bias >= 6.0 else "🕊️ 균형 잡힘"
        st.metric(label=f"👓 평균 시선 왜곡도 (색안경 지수)", value=f"{avg_bias:.1f} / 10.0")
    with col_m3:
        avg_clickbait = result_df['제목 자극성'].mean()
        bait_status = "🔥 자극적" if avg_clickbait >= 6.0 else "🍃 담백함"
        st.metric(label=f"🎣 평균 제목 자극성 (어그로)", value=f"{avg_clickbait:.1f} / 10.0")

    st.markdown("---")

    # 2층: 데이터 대장 표 (컬럼명 일반인 타겟팅으로 수정)
    st.subheader("📋 실시간 뉴스 균형 진단 기록")
    
    result_df['유저 피드백'] = result_df['뉴스 헤드라인'].apply(
        lambda x: st.session_state.feedback_dict.get(x, '⏳ 확인 대기')
    )
    
    display_df = result_df[['언론사/출처', '뉴스 헤드라인', '시선 왜곡도', '제목 자극성', '감성 판정', '유저 피드백']]
    
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "언론사/출처": st.column_config.TextColumn("신문사", width="small"),
            "뉴스 헤드라인": st.column_config.TextColumn("뉴스 제목", width="large"),
            "시선 왜곡도": st.column_config.ProgressColumn("🔶 시선 왜곡도 (1~10)", min_value=1, max_value=10, format="%d", width="medium"),
            "제목 자극성": st.column_config.ProgressColumn("🟣 제목 자극성 (1~10)", min_value=1, max_value=10, format="%d", width="small"),
            "감성 판정": st.column_config.TextColumn("감성 뉘앙스", width="small"),
            "유저 피드백": st.column_config.TextColumn("나의 공감", width="small")
        }
    )

    st.markdown("---")

    # 3층: 통계 그래프 (텍스트 톤앤매너 변경)
    st.subheader("📊 매체별 시선 편향 및 자극성 성향")
    fig, axes = plt.subplots(1, 2, figsize=(15, 5)) 
    
    # 좌측 그래프: 왜곡도
    media_bias = result_df.groupby('언론사/출처')['시선 왜곡도'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='시선 왜곡도', data=media_bias, ax=axes[0], palette="Oranges_r", hue='언론사/출처', legend=False)
    axes[0].set_title('🔶 어떤 신문사가 내 시선을 가장 치우치게 만드는가? (왜곡도)', fontsize=12, fontweight='bold', pad=10)
    axes[0].set_ylabel('왜곡 점수 (1~10)', fontsize=10)
    axes[0].set_ylim(0, 10)

    # 우측 그래프: 자극성
    media_bait = result_df.groupby('언론사/출처')['제목 자극성'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='제목 자극성', data=media_bait, ax=axes[1], palette="Purples_r", hue='언론사/출처', legend=False)
    axes[1].set_title('🎣 클릭을 유도하기 위해 제목을 얼마나 낚시성으로 쓰는가? (자극성)', fontsize=12, fontweight='bold', pad=10)
    axes[1].set_ylabel('자극 점수 (1~10)', fontsize=10)
    axes[1].set_xlabel('신문사', fontsize=10)
    axes[1].set_ylim(0, 10)
    
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("---")

    # 4층: 정밀 보고서 영역
    st.subheader("🕵️‍♂️ AI 미디어 가이드의 정밀 진단 소견")
    
    recent_records = result_df.tail(3).iloc[::-1]
    
    tab_titles = [f"⏱️ {i+1}번째 전 뉴스" for i in range(len(recent_records))]
    if tab_titles:
        tab_titles[0] = "🔍 [방금 진단한 뉴스]"
        
    tabs = st.tabs(tab_titles)
    
    for idx, (original_idx, row) in enumerate(recent_records.iterrows()):
        headline_key = row['뉴스 헤드라인']
        
        with tabs[idx]:
            with st.container():
                col_b1, col_b2 = st.columns([1, 4])
                with col_b1:
                    st.markdown(f"**🏢 신문사:** {row['언론사/출처']}")
                    st.markdown(f"**시선 왜곡도:** `{row['시선 왜곡도']} / 10`")
                    st.markdown(f"**제목 자극성:** `{row['제목 자극성']} / 10`")
                    
                    st.markdown("---")
                    st.markdown("**🤖 AI의 분석에 동의하시나요?**")
                    
                    current_feedback = st.session_state.feedback_dict.get(headline_key, None)
                    
                    if current_feedback is None:
                        col_f1, col_f2 = st.columns(2)
                        with col_f1:
                            if st.button("👍 공감해요", key=f"like_{original_idx}"):
                                st.session_state.feedback_dict[headline_key] = "👍 공감함"
                                st.rerun()
                        with col_f2:
                            if st.button("👎 글쎄요", key=f"dislike_{original_idx}"):
                                st.session_state.feedback_dict[headline_key] = "👎 동의 안 함"
                                st.rerun()
                    else:
                        st.success(f"참여 완료: {current_feedback}")
                            
                with col_b2:
                    st.markdown(f"📝 **뉴스 제목:** \"{row['뉴스 헤드라인']}\"")
                    st.markdown("💬 **AI의 균형 분석 소견**")
                    st.info(row['AI 미디어 가이드의 분석 소견'])
                    st.markdown("🎯 **알고리즘 피드 치우침 위험 요약**")
                    st.warning(f"{row['추천 피드 오염 위험 요약']}")

    # 5층: 데이터 초기화
    st.markdown("---")
    st.markdown("### ⚙️ 시스템 관리")
    if st.button("🗑️ 모든 진단 기록 초기화", use_container_width=True):
        st.session_state.analytics_history = []
        st.session_state.feedback_dict = {}
        st.rerun()

else:
    # 🌟 첫 화면 안내판 문구도 대중적으로 전면 수정
    st.info("👋 **'뉴스 생각-중심 필터'에 오신 것을 환영합니다.**")
    
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        st.markdown("""
        ### 👓 뉴스 제목, 그냥 클릭하면 안 되는 이유
        * **"내 포털 피드를 망치는 주범"** : 치우치거나 자극적인 기사를 클릭하는 순간, 포털 시스템은 나와 비슷한 성향의 기사만 계속 추천하여 '생각의 방 안'에 갇히게 만듭니다.
        * **"세상을 보는 색안경 방지"** : 교묘하게 숨겨진 편견, 편가르기 시선을 AI가 한눈에 보이게 짚어내어 세상에 대한 균형 잡힌 시각을 유지하도록 돕습니다.
        * **"낚시성은 미끼일 뿐"** : 자극적인 어휘는 내 시선을 특정 방향으로 끌고 가기 위한 미끼입니다. 미끼 뒤에 숨은 진짜 '치우침(편향)'을 확인해 보세요.
        """)
    with col_u2:
        st.markdown("""
        ### 🛠️ 일상에서 필터 활용하기
        1. 인터넷 서핑 중, 지나치게 자극적이거나 의도가 의심되는 **뉴스 제목**을 복사합니다.
        2. 왼쪽 사이드바의 **[📝 뉴스 제목 입력]** 칸에 붙여넣습니다.
        3. 출처를 입력하고 **[⚡ 시선 왜곡도 측정 시작]**을 누르면 균형 잡힌 시각의 가이드를 받을 수 있습니다.
        """)