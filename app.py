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

    /* カレンダー自体のデザイン */
    .fc { 
        background: #FFFFFF !important; 
        border-radius: 20px !important; 
        border: 4px solid #3B82F6 !important;
        padding: 10px;
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
    }
    
    .fc-toolbar-title { 
        color: #1E40AF !important; 
        font-size: 1.3em !important;
        background: #DBEAFE;
        padding: 5px 20px;
        border-radius: 50px;
    }

    /* イベントバー（一本線）の見た目 */
    .fc-event {
        border-radius: 6px !important;
        border: none !important;
        padding: 2px 4px !important;
        font-weight: 800 !important;
        font-size: 0.85em !important;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1) !important;
    }

    /* 詳細カード */
    .pop-detail-card {
        background: white;
        border-radius: 25px;
        padding: 25px;
        margin-top: 20px;
        border: 4px solid #3B82F6;
        box-shadow: 6px 6px 0px #BFDBFE;
    }

    .transport-tag {
        display: inline-block;
        background: #F1F5F9;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.85em;
        margin-top: 5px;
        color: #475569;
        border: 1px solid #E2E8F0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "にじさんじ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"], "color": "#3B82F6"},
    "ジャニーズ": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "Snow Man"], "color": "#FB923C"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急", "ピューロランド", "USJ", "ディズニー", "ナンジャタウン"], "color": "#34D399"},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "アニメイベント"], "color": "#94A3B8"}
}

TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- 交通アクセス(小山駅発) ---
def get_access_info(loc):
    guides = {
        "30分以内": "🚃 JR宇都宮線 (約25分) / 🚗 車 (約40分)",
        "1時間以内": "🚄 新幹線なすの (約15分) / 🚃 JR快速 (約45分)",
        "1時間半以内": "🚄 新幹線 (約40分) / 🚃 上野東京ライン (約80分)",
        "2時間半以内": "🚃 湘南新宿ライン (約130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return guides.get(loc, "交通機関を確認してください")

# --- 日付・期間抽出エンジン ---
def extract_dates(text):
    year = datetime.now().year
    # 期間: 8/1〜8/30
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?[〜~ー\-](\d{1,2})[./月](\d{1,2})', text)
    if m:
        start = datetime(year, int(m.group(1)), int(m.group(2)))
        end = datetime(year, int(m.group(3)), int(m.group(4)))
        return start, end
    # 単発: 8/1
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        dt = datetime(year, int(m.group(1)), int(m.group(2)))
        return dt, dt
    return None, None

@st.cache_data(ttl=3600)
def fetch_data():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    curr_year = datetime.now().year
    
    for gen, info in GENRES.items():
        for kw in info["words"][:3]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                for art in soup.select('article')[:5]:
                    title = art.select_one('.entry-title').get_text().strip()
                    link = art.find('a')['href']
                    
                    start_dt, end_dt = extract_dates(title)
                    
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "福岡", "USJ"]): loc = "それ以上"

                    if start_dt:
                        all_events.append({
                            "id": f"{kw}-{title[:10]}",
                            "title": f"{info['emoji']} {kw}",
                            "full_title": title,
                            "start": start_dt.strftime("%Y-%m-%d"),
                            # カレンダーのバーを最終日まで引くために+1日
                            "end": (end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "genre": gen, "time": loc, "url": link, "color": info["color"]
                        })
            except: pass
    return all_events

# --- メイン画面 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 冒険スケジュール")

# フィルター
c1, c2 = st.columns(2)
with c1:
    sel_gen = st.multiselect("ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
with c2:
    sel_time = st.multiselect("距離(時間)", TIMES, default=["30分以内", "1時間以内", "1時間半以内"])

# データ取得
data = fetch_data()
filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

# カレンダー表示
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], "start": e['start'], "end": e['end'],
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

# height='auto' でスクロールをなくす
state = calendar(events=cal_events, options={
    "initialView": "dayGridMonth",
    "locale": "ja",
    "height": "auto",
    "headerToolbar": {"left": "prev,next", "center": "title", "right": ""},
})

# 詳細表示
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pop-detail-card">
            <h3 style='color:#1E40AF; margin-top:0;'>✨ イベント詳細</h3>
            <p style='font-size:1.1em; font-weight:800;'>{p['full_title']}</p>
            <div style='margin-bottom:10px;'>
                <span style='background:{GENRES[p['gen']]['color']}; color:white; padding:4px 12px; border-radius:50px; font-size:12px; font-weight:bold;'>{p['gen']}</span>
                <span style='background:#3B82F6; color:white; padding:4px 12px; border-radius:50px; font-size:12px; font-weight:bold; margin-left:5px;'>📍 小山から{p['time']}</span>
            </div>
            <div class="transport-tag">🚃 行きかた目安: {get_access_info(p['time'])}</div>
            <br><br>
            <a href="{p['url']}" target="_blank" style="text-decoration:none;">
                <button style="width:100%; background:#3B82F6; color:white; border:none; padding:15px; border-radius:15px; font-weight:bold; cursor:pointer;">
                    公式サイトへ GO! ➔
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("💡 カレンダーのイベントをタップして詳細を表示しよう！")

# 週間予定
st.subheader("📋 今週のピックアップ")
today = datetime.now().date()
week_later = today + timedelta(days=7)
for e in sorted(filtered, key=lambda x: x['start']):
    evt_start = datetime.strptime(e['start'], "%Y-%m-%d").date()
    if today <= evt_start <= week_later:
        st.markdown(f"""
        <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']};">
            <small>{e['start']} | {e['genre']}</small><br>
            <b>{e['full_title']}</b><br>
            <small style='color:#3B82F6;'>🚃 {get_access_info(e['time'])}</small>
        </div>
        """, unsafe_allow_html=True)
