import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とデザイン ---
st.set_page_config(page_title="小山発・推し活ナビ", layout="wide", initial_sidebar_state="expanded")

# カスタムCSSでUIを劇的に改善
st.markdown("""
    <style>
    .main { background-color: #f7f9fc; }
    .stMetric { background-color: white; padding: 10px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .event-card {
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        border-left: 8px solid;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .event-card:hover { transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    .time-badge {
        padding: 4px 12px;
        border-radius: 20px;
        color: white;
        font-size: 0.8em;
        font-weight: bold;
    }
    .cate-badge {
        background-color: #eee;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.7em;
        color: #666;
    }
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

# --- サイドバー設定 ---
with st.sidebar:
    st.title("📍 小山駅起点")
    st.markdown("---")
    
    st.header("1. ジャンル選択")
    selected_cats = [cat for cat in CATEGORIES.keys() if st.checkbox(cat, value=True)]
    
    st.header("2. 移動時間")
    time_limit = st.multiselect(
        "許容できる範囲",
        ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"],
        default=["30分以内", "1時間以内", "1時間半以内"]
    )
    
    st.header("3. カスタム検索")
    custom_kw = st.text_input("追加したいキーワード")
    
    st.divider()
    st.caption("小山駅からイベント会場までの「交通手段」と「所要時間」を考慮して表示します。")

# --- データ取得・処理 ---
@st.cache_data(ttl=1800)
def get_all_events(selected_categories, extra_kw):
    # 検索キーワードの組み立て
    search_keywords = []
    for cat in selected_categories:
        search_keywords.extend(CATEGORIES[cat])
    if extra_kw:
        search_keywords.append(extra_kw)
        
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for kw in search_keywords[:15]: # 負荷軽減のため上位15語
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.select('article')[:6]:
                title = art.select_one('.entry-title').get_text().strip()
                link = art.find('a')['href']
                
                # エリア・アクセス判定
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

                # 日付抽出
                date_found = datetime.now()
                match = re.search(r'(\d+)月(\d+)日', title)
                if match:
                    try: date_found = datetime(2024, int(match.group(1)), int(match.group(2)))
                    except: pass

                all_events.append({
                    "title": title,
                    "start": date_found.strftime("%Y-%m-%d"),
                    "color": color,
                    "url": link,
                    "cat": label,
                    "way": way,
                    "genre": kw
                })
        except: pass
    return all_events

# --- メイン画面 ---
st.title("🌸 推し活アクセスカレンダー")

events = get_all_events(selected_cats, custom_kw)
# フィルター適用
filtered_events = [e for e in events if e['cat'] in time_limit]

if not filtered_events:
    st.info("条件に合うイベントが見つかりませんでした。左のメニューからジャンルや時間を増やしてみてください。")
else:
    # 統計
    c1, c2, c3 = st.columns(3)
    c1.metric("見つかったイベント", f"{len(filtered_events)}件")
    c2.metric("起点", "小山駅")
    c3.metric("最速", "約25分")

    tab1, tab2 = st.tabs(["📅 カレンダー表示", "📋 リスト表示"])

    with tab1:
        calendar_options = {
            "initialView": "dayGridMonth",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
            "locale": "ja"
        }
        calendar(events=filtered_events, options=calendar_options)

    with tab2:
        for e in sorted(filtered_events, key=lambda x: x['start']):
            st.markdown(f"""
            <div class="event-card" style="border-color: {e['color']};">
                <span class="time-badge" style="background-color: {e['color']};">{e['cat']}</span>
                <span class="cate-badge">{e['genre']}</span>
                <div style="margin-top:10px;">
                    <small>📅 {e['start']} | 🚃 {e['way']}</small><br>
                    <a href="{e['url']}" target="_blank" style="text-decoration: none; color: #333; font-size: 1.1em; font-weight: bold;">{e['title']}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.divider()
st.caption("※日付が取得できないイベントは便宜上今日の日付付近に表示されています。")
