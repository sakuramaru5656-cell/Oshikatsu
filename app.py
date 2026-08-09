import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定 ---
st.set_page_config(page_title="小山発・推し活ナビPRO", layout="wide")

# スタイル改善
st.markdown("""
    <style>
    .event-card {
        background: white; padding: 15px; border-radius: 10px;
        border-left: 10px solid; margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .date-badge { font-weight: bold; color: #444; background: #eee; padding: 2px 8px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
CATEGORIES = {
    "アイドル(J系)": ["timelesz", "Hey! Say! JUMP", "King & Prince", "なにわ男子"],
    "ポケモン": ["ポケモン", "ピカチュウ", "ポケモンセンター"],
    "ジャンプ": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO", "呪術廻戦"],
    "VTuber": ["ホロライブ", "さくらみこ", "にじさんじ"],
    "その他": ["アニメ", "コラボカフェ"]
}

# --- 日付・期間解析エンジン (AI的アプローチ) ---
def parse_event_dates(text):
    """
    タイトルや本文から開催期間(開始日・終了日)をAI的に推測する
    """
    now = datetime.now()
    year = now.year
    
    # パターン1: 8.10(土)〜9.1(日) のような形式
    range_match = re.search(r'(\d{1,2})[./月](\d{1,2}).*?[〜~ー\-](\d{1,2})[./月](\d{1,2})', text)
    if range_match:
        m1, d1, m2, d2 = map(int, range_match.groups())
        # 年をまたぐ判定（12月〜1月など）
        start_year = year
        end_year = year if m2 >= m1 else year + 1
        return datetime(start_year, m1, d1), datetime(end_year, m2, d2)

    # パターン2: 8月10日(土) のような単発形式
    single_match = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if single_match:
        m, d = map(int, single_match.groups())
        dt = datetime(year, m, d)
        # すでに過ぎた日付で、かつ11月や12月に1月の日付を見つけた場合は来年とみなす
        if dt < now - timedelta(days=60):
            dt = datetime(year + 1, m, d)
        return dt, dt + timedelta(days=1) # 期間がない場合は1日だけ

    return None, None

# --- データ取得 ---
@st.cache_data(ttl=3600)
def get_all_events(selected_categories, extra_kw):
    search_keywords = []
    for cat in selected_categories:
        search_keywords.extend(CATEGORIES[cat])
    if extra_kw:
        search_keywords.append(extra_kw)
        
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 検索効率化のため重複削除
    search_keywords = list(set(search_keywords))

    for kw in search_keywords[:10]:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.select('article')[:8]:
                title = art.select_one('.entry-title').get_text().strip()
                link = art.find('a')['href']
                
                # アクセス判定ロジック (小山駅起点)
                loc_label = "都内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc_label = "宇都宮"
                elif any(x in title for x in ["大宮", "さいたま", "レイクタウン"]): loc_label = "大宮"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ", "ぴあアリーナ"]): loc_label = "横浜・千葉"
                elif any(x in title for x in ["大阪", "名古屋", "ドーム", "富士急"]): loc_label = "遠方"

                access_map = {
                    "宇都宮": (30, "30分以内", "#28a745", "JR宇都宮線"),
                    "大宮": (50, "1時間以内", "#007bff", "宇都宮線 快速"),
                    "都内": (85, "1時間半以内", "#f1c40f", "上野東京ライン"),
                    "横浜・千葉": (135, "2時間半以内", "#e67e22", "湘南新宿ライン等"),
                    "遠方": (240, "それ以上", "#e74c3c", "新幹線・特急"),
                }
                mins, label, color, way = access_map.get(loc_label, (90, "1時間半以内", "#f1c40f", "JR線"))

                # 日付解析の実行
                start_dt, end_dt = parse_event_dates(title)
                
                # 日付が取れなかった場合は「日付未定」としてカレンダーには出さない
                if not start_dt:
                    is_valid_date = False
                    start_dt = datetime.now() # リスト表示用
                    end_dt = datetime.now()
                else:
                    is_valid_date = True

                all_events.append({
                    "title": f"【{kw}】{title}",
                    "start": start_dt.strftime("%Y-%m-%d"),
                    "end": end_dt.strftime("%Y-%m-%d"),
                    "color": color,
                    "url": link,
                    "cat": label,
                    "way": way,
                    "genre": kw,
                    "is_valid": is_valid_date
                })
        except: pass
    return all_events

# --- UI構築 ---
with st.sidebar:
    st.title("📍 小山駅起点設定")
    selected_cats = [cat for cat in CATEGORIES.keys() if st.checkbox(cat, value=True)]
    time_limit = st.multiselect("行ける範囲", ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"], default=["30分以内", "1時間以内", "1時間半以内"])
    custom_kw = st.text_input("追加ワード(例: アイナナ)")

st.title("🌸 推し活アクセスカレンダー")

all_data = get_all_events(selected_cats, custom_kw)
# フィルター適用
filtered_events = [e for e in all_data if e['cat'] in time_limit]

tab1, tab2 = st.tabs(["📅 カレンダー (期間表示)", "📋 イベント一覧"])

with tab1:
    # 日付が判明しているものだけカレンダーに表示
    calendar_data = [e for e in filtered_events if e['is_valid']]
    if not calendar_data:
        st.warning("カレンダーに表示できる日付確定イベントが見つかりませんでした。")
    else:
        calendar_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
            "locale": "ja",
            "height": "600px",
        }
        calendar(events=calendar_data, options=calendar_options)

with tab2:
    if not filtered_events:
        st.write("イベントがありません")
    else:
        # 日付順に並び替え（日付不明は下に）
        for e in sorted(filtered_events, key=lambda x: (not x['is_valid'], x['start'])):
            date_str = f"{e['start']} 〜 {e['end']}" if e['is_valid'] else "日付情報なし(サイトを確認)"
            st.markdown(f"""
            <div class="event-card" style="border-color: {e['color']};">
                <span class="date-badge">{date_str}</span> 
                <span style="color: {e['color']}; font-weight: bold; margin-left: 10px;">⏱{e['cat']}</span>
                <div style="margin-top:10px;">
                    <a href="{e['url']}" target="_blank" style="text-decoration: none; color: #333; font-size: 1.1em; font-weight: bold;">{e['title']}</a>
                    <br><small>🚃 最寄り経路目安: {e['way']} (小山駅発)</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
