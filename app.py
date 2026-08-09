import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定と超ポップなCSS ---
st.set_page_config(page_title="推しイベ・図鑑", page_icon="🎡", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    
    /* 全体背景 */
    html, body, [class*="css"] {
        font-family: 'M PLUS Rounded 1c', sans-serif;
        background-color: #FFCC00; /* ピカチュウイエロー */
    }
    .stApp { background: #FFCC00; }

    /* 図鑑の外枠デザイン */
    .pokedex-frame {
        background: #CC0000; /* レッド */
        border: 10px solid #8B0000;
        border-radius: 30px;
        padding: 20px;
        box-shadow: 0 15px 0 #8B0000;
        margin-bottom: 30px;
    }

    /* カレンダー（モニター画面） */
    .fc { 
        background: #E0E0E0 !important; /* 液晶風グレー */
        border-radius: 10px; 
        border: 8px solid #333 !important;
        padding: 5px;
    }
    .fc-toolbar-title { color: #333 !important; font-weight: 800 !important; }
    .fc-daygrid-day-number { color: #333 !important; font-weight: bold; }
    
    /* イベントバーのスタイル */
    .fc-event {
        border-radius: 20px !important;
        border: 2px solid rgba(0,0,0,0.2) !important;
        padding: 2px 5px !important;
        box-shadow: 2px 2px 0px rgba(0,0,0,0.1);
    }

    /* ポケモン図鑑風カード */
    .detail-card {
        background: #FFFFFF;
        border: 5px solid #3B4CCA; /* ブルー */
        border-radius: 25px;
        padding: 20px;
        margin-top: 20px;
        position: relative;
    }
    .detail-card::before {
        content: "■■■";
        position: absolute; top: 10px; right: 20px; color: #3B4CCA; letter-spacing: 5px;
    }

    /* タイプバッジ */
    .type-pill {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 13px;
        color: white;
        text-shadow: 1px 1px 0px #000;
        margin: 5px 2px;
    }

    /* ボタン */
    .stButton>button {
        background: #3B4CCA;
        color: white;
        border-radius: 15px;
        border: 4px solid #2A3693;
        font-weight: 800;
        box-shadow: 0 4px 0 #2A3693;
    }
    .stButton>button:active { transform: translateY(4px); box-shadow: none; }
    </style>
    """, unsafe_allow_html=True)

# --- カテゴリー定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "さくらみこ", "にじさんじ"], "color": "#FF66CC"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ピカチュウ"], "color": "#3B4CCA"},
    "ジャニーズ": {"emoji": "🎤", "words": ["timelesz", "Hey! Say! JUMP", "King & Prince", "Snow Man"], "color": "#FF9900"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#FF3300"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#9966FF"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "ピューロランド", "USJ", "ディズニー", "ナンジャタウン"], "color": "#00CC99"},
    "その他": {"emoji": "🎁", "words": ["コラボカフェ", "アニメ展示"], "color": "#666666"}
}

TIMES = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

# --- 交通アクセス(小山駅発) ---
def get_access_v2(loc):
    if loc == "30分以内":
        return "🚃 JR宇都宮線 (25分) | 🚗 車 (40分)"
    elif loc == "1時間以内":
        return "🚄 新幹線なすの (15分) | 🚃 JR快速 (45分)"
    elif loc == "1時間半以内":
        return "🚄 新幹線 (40分) | 🚃 上野東京ライン (80分)"
    elif loc == "2時間半以内":
        return "🚃 湘南新宿ライン (130分) | 🚄 新幹線+JR"
    else:
        return "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"

# --- 検索＆解析 ---
@st.cache_data(ttl=3600)
def fetch_all_events():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    year = datetime.now().year
    
    for gen, info in GENRES.items():
        for kw in info["words"][:3]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                for art in soup.select('article')[:5]:
                    title = art.select_one('.entry-title').get_text().strip()
                    link = art.find('a')['href']
                    
                    # 日付期間の抽出
                    start_dt = end_dt = None
                    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?[〜~ー\-](\d{1,2})[./月](\d{1,2})', title)
                    if m:
                        start_dt = datetime(year, int(m.group(1)), int(m.group(2)))
                        end_dt = datetime(year, int(m.group(3)), int(m.group(4)))
                    else:
                        m = re.search(r'(\d{1,2})[./月](\d{1,2})', title)
                        if m:
                            start_dt = end_dt = datetime(year, int(m.group(1)), int(m.group(2)))
                    
                    # エリア判定
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急", "ピューロランド"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "福岡", "USJ"]): loc = "それ以上"

                    if start_dt:
                        all_events.append({
                            "id": f"{kw}-{title[:10]}",
                            "title": f"{info['emoji']} {kw}",
                            "full_title": title,
                            "start": start_dt.strftime("%Y-%m-%d"),
                            "end": (end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "genre": gen, "time": loc, "url": link, "color": info["color"]
                        })
            except: pass
    return all_events

# --- メイン画面 ---
st.title("🐾 推しイベ・図鑑 Ver.2")
st.write("栃木県小山駅からの冒険がはじまる！")

# フィルター
col1, col2 = st.columns(2)
with col1:
    selected_gen = st.multiselect("タイプを選択", list(GENRES.keys()), default=list(GENRES.keys()))
with col2:
    selected_time = st.multiselect("距離を選択", TIMES, default=["30分以内", "1時間以内", "1時間半以内"])

# データ準備
data = fetch_all_events()
filtered = [e for e in data if e['genre'] in selected_gen and e['time'] in selected_time]

# カレンダー表示（図鑑フレーム内）
st.markdown('<div class="pokedex-frame">', unsafe_allow_html=True)
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], "start": e['start'], "end": e['end'],
        "backgroundColor": e['color'], "borderColor": "rgba(0,0,0,0.1)",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "500px"})
st.markdown('</div>', unsafe_allow_html=True)

# 図鑑詳細
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    access = get_access_v2(p['time'])
    st.markdown(f"""
        <div class="detail-card">
            <h3 style='color:#3B4CCA;'>📕 イベント詳細データ</h3>
            <p style='font-size:1.1em; font-weight:bold;'>{p['full_title']}</p>
            <div style='margin:10px 0;'>
                <span class="type-pill" style="background:{GENRES[p['gen']]['color']}">{p['gen']}</span>
                <span class="type-pill" style="background:#3B4CCA">📍 小山から{p['time']}</span>
            </div>
            <p style='background:#f0f0f0; padding:10px; border-radius:10px; font-size:0.9em;'>
                <b>👣 アクセスルート:</b><br>{access}
            </p>
            <a href="{p['url']}" target="_blank" style="text-decoration:none;">
                <button style="width:100%; padding:12px; margin-top:10px; cursor:pointer;">
                    この場所へ GO！ ➔
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("💡 カレンダーの中のイベントをタップして、データを表示しよう！")

# 週間リスト
st.subheader("📋 今週のイベント")
today = datetime.now().date()
for e in sorted(filtered, key=lambda x: x['start']):
    evt_start = datetime.strptime(e['start'], "%Y-%m-%d").date()
    if today <= evt_start <= today + timedelta(days=7):
        st.markdown(f"""
        <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:10px solid {e['color']};">
            <small>{e['start']} | {e['genre']}</small><br>
            <b>{e['full_title']}</b><br>
            <small style='color:#666;'>🚃 {get_access_v2(e['time'])}</small>
        </div>
        """, unsafe_allow_html=True)
