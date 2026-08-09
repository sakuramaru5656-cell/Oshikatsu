import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とデザインCSS ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #FFFDF0;
    }
    .stApp { background: #FFFDF0; }

    /* カレンダー自体のポップなデザイン */
    .fc { 
        background: #FFFFFF !important; 
        border-radius: 20px !important; 
        border: 4px solid #3B82F6 !important;
        padding: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
    }
    .fc-toolbar-title { 
        color: #1E40AF !important; 
        font-size: 1.2em !important;
        background: #DBEAFE;
        padding: 5px 15px;
        border-radius: 50px;
    }

    /* イベントバー（一本線） */
    .fc-event {
        border-radius: 6px !important;
        border: none !important;
        padding: 4px 6px !important;
        font-weight: 800 !important;
        cursor: pointer;
    }

    /* ポケモン風詳細カード */
    .pop-card {
        background: white; border-radius: 20px; padding: 20px;
        margin-top: 15px; border: 4px solid #3B82F6;
        box-shadow: 6px 6px 0px #BFDBFE;
    }
    .badge {
        display: inline-block; padding: 4px 12px; border-radius: 50px;
        font-size: 11px; font-weight: bold; color: white; margin-right: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 設定データ ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "Snow Man"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんスタ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ナルト"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ディズニー"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ"], "color": "#94A3B8"}
}

AREAS = ["栃木", "埼玉", "東京", "神奈川", "千葉", "遠方(大阪・名古屋等)"]
TIME_LABELS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(base_station, loc):
    guides = {
        "30分以内": "🚃 宇都宮線等 (約25分) / 🚗 約40分",
        "1時間以内": "🚄 新幹線等 (約15分) / 🚃 快速 (約45分)",
        "1時間半以内": "🚄 新幹線 (約40分) / 🚃 在来線 (約80分)",
        "2時間半以内": "🚃 湘南新宿ライン等 (約130分)",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return f"{base_station}駅から " + guides.get(loc, "交通機関を確認")

# --- 日付抽出ロジック ---
def parse_dates(text):
    year = datetime.now().year
    sep = r'[〜~ー\-\s]+'
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?{sep}(\d{1,2})[./月](\d{1,2})'.format(sep=sep), text)
    if m:
        try:
            start = datetime(year, int(m.group(1)), int(m.group(2)))
            end = datetime(year, int(m.group(3)), int(m.group(4)))
            if end < start: end = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return start, end
        except: pass
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_data(selected_genres, custom_keywords):
    all_events = []
    keywords = []
    for g in selected_genres: keywords.extend(GENRES[g]["words"])
    if custom_keywords: keywords.extend([k.strip() for k in custom_keywords.split(",")])

    headers = {"User-Agent": "Mozilla/5.0"}
    for kw in list(set(keywords))[:15]:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.find_all('article')[:5]:
                title = (art.find('h2') or art.select_one('.entry-title')).get_text().strip()
                link = art.find('a')['href']
                start, end = parse_dates(title)
                
                # エリア・時間判定
                loc_name = "東京"
                dist = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール", "栃木"]): 
                    loc_name, dist = "栃木", "30分以内"
                elif any(x in title for x in ["大宮", "さいたま", "浦和"]): 
                    loc_name, dist = "埼玉", "1時間以内"
                elif any(x in title for x in ["横浜", "ぴあアリーナ", "Kアリーナ"]): 
                    loc_name, dist = "神奈川", "2時間半以内"
                elif any(x in title for x in ["幕張", "千葉", "舞浜"]): 
                    loc_name, dist = "千葉", "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ", "福岡"]): 
                    loc_name, dist = "遠方(大阪・名古屋等)", "それ以上"

                emoji = "🔍"
                color = "#94A3B8"
                for g, info in GENRES.items():
                    if any(w in title or w in kw for w in info["words"]):
                        emoji, color = info["emoji"], info["color"]
                        break

                if start:
                    all_events.append({
                        "id": f"{kw}-{title[:10]}", "title": f"{emoji} {kw}",
                        "full_title": title, "start": start, "end": end,
                        "time": dist, "area": loc_name, "url": link, "color": color
                    })
        except: pass
    return all_events

# --- メイン画面 ---
st.title("✨ 推しイベ")

# 1. 検索設定（サイドバー）
with st.sidebar:
    st.header("🚉 出発地点の設定")
    departure_station = st.text_input("出発駅を入力", value="小山")
    
    st.header("🔍 イベントを探す")
    sel_gen = st.multiselect("ジャンル", list(GENRES.keys()), default=["VTuber", "ポケモン", "テーマパーク"])
    custom_input = st.text_input("自由な検索ワード", help="カンマ区切りで入力")
    
    st.header("📍 エリアで絞り込む")
    sel_areas = st.multiselect("開催場所", AREAS, default=AREAS)
    
    st.header("⏳ 距離で絞り込む")
    sel_time = st.multiselect("所要時間", TIME_LABELS, default=["30分以内", "1時間以内", "1時間半以内"])

# 2. データ取得とフィルタリング
raw_data = fetch_data(sel_gen, custom_input)
filtered = [e for e in raw_data if e['time'] in sel_time and e['area'] in sel_areas]

# 3. カレンダー表示
st.subheader("📅 月間カレンダー")
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], 
        "start": e['start'].strftime("%Y-%m-%d"), 
        "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "area": e['area']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto"})

# 4. クリック詳細表示
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pop-card">
            <h3>✨ イベント詳細</h3>
            <b>{p['full_title']}</b><br><br>
            <span class="badge" style="background:#3B82F6">📍 エリア: {p['area']}</span>
            <span class="badge" style="background:#10B981">⏱ {p['time']}</span><br><br>
            <small>🚃 経路案内: {get_access_info(departure_station, p['time'])}</small><br><br>
            <a href="{p['url']}" target="_blank">
                <button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトへ GO!</button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# 5. 週間ピックアップ
st.subheader(f"📋 今週の{departure_station}発クエスト")
today = datetime.now().date()
week_later = today + timedelta(days=7)
for e in sorted(filtered, key=lambda x: x['start']):
    if today <= e['start'].date() <= week_later:
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
                <small>{e['start'].strftime('%m/%d')} | {e['area']} ({e['time']})</small><br>
                <b>{e['full_title']}</b><br>
                <small style="color:#3B82F6;">🚃 {get_access_info(departure_station, e['time'])}</small>
            </div>
        """, unsafe_allow_html=True)
