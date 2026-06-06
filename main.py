import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from openai import OpenAI
import json
import requests
from datetime import datetime
import io

# --- 0. 스타일 및 디자인 세팅 (한글/이모지 경고 원천 차단) ---
import matplotlib as mpl
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['axes.unicode_minus'] = False
sns.set_theme(style="whitegrid")

# --- 🛠️ 깃허브 저장소의 CSV 파일에 실시간 누적 저장하는 함수 ---
def save_data_to_github(headline, source, bias_risk, clickbait_risk, feedback):
    """유저 피드백 발생 시 깃허브 레포지토리의 data.csv 파일을 갱신하는 함수"""
    try:
        GITHUB_TOKEN = st.secrets["github"]["token"]
        REPO_NAME = st.secrets["github"]["repo"]
        FILE_PATH = "data.csv"
        
        url = f"https://api.github.com/repos/{REPO_NAME}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        res = requests.get(url, headers=headers)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_row = pd.DataFrame([{
            "날짜": current_time, "뉴스 제목": headline, "신문사": source, 
            "시선 편향도": bias_risk, "제목 자극성": clickbait_risk, "유저 피드백": feedback
        }])
        
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
        
        put_data = {
            "message": "🔥 시스템 실시간 뉴스 데이터 누적 피드백 기록",
            "content": content_encoded
        }
        if sha:
            put_data["sha"] = sha
            
        requests.put(url, headers=headers, json=put_data)
        return True
    except Exception as e:
        print(f"[GitHub Sync Error] {str(e)}")
        return False

# --- 1. 미디어 균형 분석 및 오타 자동 정제 GPT 엔진 ---
class AdvancedEthicsAnalyzer:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def analyze_with_gpt(self, headline, source):
        prompt = f"""
        당신은 사용자가 미디어의 홍수 속에서 '생각의 중심'을 잡도록 돕는 독창적이고 날카로운 미디어 밸런스 가이드이자, 한국어 뉴스 텍스트 정제 전문가입니다.
        
        [임무 1: 신문사 및 뉴스 헤드라인 오타 자동 정제]
        1. 사용자가 입력한 [언론사/출처] 문구에 오타, 탈자, 조사, 혹은 파편화된 자모음(예: 한겨ㅈ래, 한결레, 네이바, 조선 일보 등)이 있다면 대한민국 표준 언론사 명칭(예: 한겨레신문, 네이버, 조선일보)으로 알아서 교정하세요.
        2. 사용자가 입력한 [뉴스 헤드라인] 문구에 오타, 띄어쓰기 오류, 오타성 자모음(예: 백신ㄴ, 대툥령 등)이 있다면 문맥을 고려하여 올바른 한국어 표준 문장 및 단어로 깔끔하게 교정하세요.

        [임무 2: 미디어 프레임 분석]
        정제된 뉴스 헤드라인이 사용자의 '시선'을 특정 방향으로 편향되게 만들거나, 포털 알고리즘을 한쪽으로 치우치게 만들 위험이 있는지 분석하여 JSON 형식으로 응답하세요.
        
        [뉴스 헤드라인 (오타 포함 가능)]: "{headline}"
        [언론사/출처 (오타 포함 가능)]: "{source}"
        
        [응답 형식 (JSON)]:
        {{
            "cleaned_source": "오타와 띄어쓰기가 완벽히 교정된 표준 언론사 명칭 (예: 한겨레신문, 조선일보, 네이버)",
            "cleaned_headline": "오타 및 맞춤법이 완벽히 교정된 깨끗한 뉴스 제목",
            "sentiment_score": -1.0에서 1.0 사이의 실수,
            "bias_risk": 1에서 10 사이의 정수 (시선 편향도),
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
                temperature=0.3
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {
                "cleaned_source": source, "cleaned_headline": headline,
                "sentiment_score": 0.0, "bias_risk": 1, "clickbait_risk": 1, 
                "detailed_reason": f"분석 중 오류 발생: {str(e)}", "one_line_summary": "⚠️ 분석 실패"
            }

# --- 2. 웹 화면 구성 및 세션 상태 초기화 ---
st.set_page_config(layout="wide", page_title="뉴스 생각-중심 필터", page_icon="⚖️")
st.title("⚖️ 뉴스 편향도 분석기 (News Balance Filter)")

# 📢 첫 화면 안내 및 데이터 전송 경고문 보강 구역 ⭐
st.warning("""
🎯 **이 서비스가 왜 필요할까요?** 뉴스를 읽다 보면 나도 모르게 세상에 대한 '색안경'이 끼워지곤 합니다. 한쪽으로 치우친 뉴스를 자꾸 클릭하면, 포털 알고리즘마저 내 피드를 편향된 정보로만 가득 채우게 됩니다.

---
🚨 **[이용자 필수 안내 및 데이터 수집 경고]**
1. 본 서비스는 AI를 활용한 뉴스 데이터 편향 연구 및 분석 과제의 일환으로 운영됩니다.
2. 분석 결과 하단의 **[🕵️‍♂️ AI의 정밀 진단 소견]** 탭에서 **`👍 공감해요`** 또는 **`👎 글쎄요`** 버튼을 반드시 눌러주세요. 
3. **버튼을 누르시는 순간, 입력하신 [뉴스 제목, 신문사, AI 분석 결과, 피드백 종류] 데이터가 개발자의 데이터베이스(GitHub 저장소)로 안전하게 실시간 전송 및 적재됩니다.** 
4. 수집된 데이터는 통계 분석 목적 이외에는 절대 사용되지 않으며, 개인정보는 수집하지 않습니다. 신중하고 성실한 피드백 참여를 부탁드립니다!
""")
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
        submit_button = st.form_submit_button(label="⚡ 시선 편향도 측정 시작")
    
    st.markdown("---")
    st.header("📊 진단 지표 평가 기준")
    metrics_data = {
        "점수 범위": ["1 ~ 3점", "4 ~ 7점", "8 ~ 10점"],
        "시선 편향도 상태": ["🟢 객관적 / 중립적", "🟡 부분 프레임 작동", "🔴 특정 시각 편중"],
        "제목 자극성 상태": ["🟢 담백한 사실 전달", "🟡 호기심 유도", "🔴 어그로성 선동"]
    }
    metrics_df = pd.DataFrame(metrics_data)
    st.table(metrics_df)
    st.caption("※ 본 지표는 GPT-4o 분석 엔진 기반의 미디어 언어 프레임 검구 결과치입니다.")

if submit_button:
    if not input_headline or not input_source:
        st.sidebar.warning("뉴스 제목 and 신문사를 모두 입력해 주세요!")
    else:
        analyzer = AdvancedEthicsAnalyzer(api_key=api_key)
        with st.spinner("⚖️ AI가 뉴스를 진단 중입니다..."):
            gpt_res = analyzer.analyze_with_gpt(input_headline, input_source)
            
            ai_cleaned_source = gpt_res.get('cleaned_source', input_source)
            ai_cleaned_headline = gpt_res.get('cleaned_headline', input_headline)
            
            new_record = {
                '뉴스 헤드라인': ai_cleaned_headline, '언론사/출처': ai_cleaned_source,
                '감성 점수': gpt_res['sentiment_score'], '시선 편향도': gpt_res['bias_risk'], 
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
    with col_m1: st.metric(label="📊 분석한 뉴스", value=f"{len(result_df)} 건")
    with col_m2: st.metric(label="👓 평균 시선 편향도", value=f"{result_df['시선 편향도'].mean():.1f} / 10.0")
    with col_m3: st.metric(label="🎣 평균 제목 자극성", value=f"{result_df['제목 자극성'].mean():.1f} / 10.0")

    st.markdown("---")

    # 2층: 데이터 테이블
    st.subheader("📋 뉴스 진단 기록")
    result_df['유저 피드백'] = result_df['뉴스 헤드라인'].apply(lambda x: st.session_state.feedback_dict.get(x, '⏳ 확인 대기'))
    st.dataframe(
        result_df[['언론사/출처', '뉴스 헤드라인', '시선 편향도', '제목 자극성', '감성 판정', '유저 피드백']], 
        width='stretch', 
        hide_index=True
    )

    st.markdown("---")

    # 3층: 통계 그래프
    st.subheader("📊 매체별 시선 편향 및 자극성 성향")
    
    import os
    import matplotlib.font_manager as fm
    
    font_path = "./NanumGothic.ttf"
    if not os.path.exists(font_path):
        font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
        res = requests.get(font_url)
        with open(font_path, "wb") as f:
            f.write(res.content)
            
    k_font = fm.FontProperties(fname=font_path)
    fig, axes = plt.subplots(1, 2, figsize=(15, 5)) 
    
    # --- 왼쪽 그래프: 편향도 ---
    media_bias = result_df.groupby('언론사/출처')['시선 편향도'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='시선 편향도', data=media_bias, ax=axes[0], palette="Oranges_r", hue='언론사/출처', legend=False)
    
    axes[0].set_title('신문사별 평균 시선 편향도 (1-10)', fontproperties=k_font, fontsize=14, fontweight='bold')
    axes[0].set_ylabel('편향 점수 (1~10)', fontproperties=k_font, fontsize=11)
    axes[0].set_xlabel('신문사', fontproperties=k_font, fontsize=11)
    axes[0].set_ylim(0, 10)
    for tick in axes[0].get_xticklabels():
        tick.set_fontproperties(k_font)
        tick.set_fontsize(10)

    # --- 오른쪽 그래프: 자극성 ---
    media_bait = result_df.groupby('언론사/출처')['제목 자극성'].mean().reset_index()
    sns.barplot(x='언론사/출처', y='제목 자극성', data=media_bait, ax=axes[1], palette="Purples_r", hue='언론사/출처', legend=False)
    
    axes[1].set_title('신문사별 평균 제목 자극성 (1-10)', fontproperties=k_font, fontsize=14, fontweight='bold')
    axes[1].set_ylabel('자극 점수 (1~10)', fontproperties=k_font, fontsize=11)
    axes[1].set_xlabel('신문사', fontproperties=k_font, fontsize=11)
    axes[1].set_ylim(0, 10)
    for tick in axes[1].get_xticklabels():
        tick.set_fontproperties(k_font)
        tick.set_fontsize(10)
    
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("---")

    # 4층: 정밀 보고서 및 깃허브 실시간 푸시 트리거
    st.subheader("🕵️‍♂️ AI의 정밀 진단 소견")
    recent_records = result_df.tail(3).iloc[::-1]
    tabs = st.tabs([f"⏱️ {i+1}번째 전 뉴스" for i in range(len(recent_records))])
    
    for idx, (original_idx, row) in enumerate(recent_records.iterrows()):
        headline_key = row['뉴스 헤드라인']
        with tabs[idx]:
            col_b1, col_b2 = st.columns([1, 4])
            with col_b1:
                st.markdown(f"**🏢 신문사:** {row['언론사/출처']}")
                st.markdown(f"**시선 편향도:** `{row['시선 편향도']}/10`  \n**제목 자극성:** `{row['제목 자극성']}/10`")
                st.markdown("---")
                st.markdown("**🤖 분석에 동의하시나요?**")
                
                current_feedback = st.session_state.feedback_dict.get(headline_key, None)
                if current_feedback is None:
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        if st.button("👍 공감해요", key=f"like_{original_idx}"):
                            st.session_state.feedback_dict[headline_key] = "👍 공감함"
                            with st.spinner("데이터 동기화 중..."):
                                success = save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "👍 공감함")
                                if success:
                                    st.success("✅ 저장 완료!")
                                    import time
                                    time.sleep(1)
                            st.rerun()
                    with col_f2:
                        if st.button("👎 글쎄요", key=f"dislike_{original_idx}"):
                            st.session_state.feedback_dict[headline_key] = "👎 동의 안 함"
                            with st.spinner("데이터 동기화 중..."):
                                success = save_data_to_github(row['뉴스 헤드라인'], row['언론사/출처'], row['시선 편향도'], row['제목 자극성'], "👎 동의 안 함")
                                if success:
                                    st.success("✅ 저장 완료!")
                                    import time
                                    time.sleep(1)
                            st.rerun()
                else:
                    st.success(f"참여 완료: {current_feedback}")
            with col_b2:
                st.markdown(f"📝 **뉴스 제목:** \"{row['뉴스 헤드라인']}\"")
                st.info(row['AI 미디어 가이드의 분석 소견'])
                st.warning(f"🎯 {row['추천 피드 오염 위험 요약']}")
else:
    st.info("👋 뉴스 제목을 왼쪽 사이드바에 입력하여 뉴스 편향도 분석기를 작동시켜 보세요!")
