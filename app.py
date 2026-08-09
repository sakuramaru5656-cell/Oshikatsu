import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とポップなデザイン ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; box-shadow: 0 8px 20px rgba(0,0,0,0.05); }
    .fc-event { border-radius: 8px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    
    /* 更新ボタン専用スタイル */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        font-weight: 800;
        border: 2px solid #3B82F6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 検索キーワード設定 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "ぶいすぽ", "さくらみこ", "宝鐘マリン", "星街すいせい"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ポケカ", "ポケモン カフェ"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["Snow Man", "なにわ男子", "King & Prince", "SixTONES", "Hey! Say! JUMP", "timelesz", "WEST.", "ライブツアー"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ", "ESストア", "スタライ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO", "ジャンプショップ"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "サンリオピューロランド", "USJ", "ユニバ コラボ", "ディズニー コラボ", "ナンジャタウン", "西武園ゆうえんち"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ", "ポップアップストア", "原画展", "一番くじ"], "color": "#94A3B8"}
}

TIME_OPTIONS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 JR宇都宮線 (約25分) / 🚗 車 (約40分)",
        "1時間以内": "🚄 新幹線なすの (約15分) / 🚃 JR快速 (約45分)",
        "1時間半以内": "🚄 新幹線 (約40分) / 🚃 上野東京ライン (約80分)",
        "2時間半以内": "🚃 湘南新宿ライン (約130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return guides.get(loc, "交通機関を確認してください")

def extract_dates_v3(text):
    year = datetime.now().year
    sep = r'[〜~ー\-\s－]+'
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
def fetch_huge_data():
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"}
    
    for gen, info in GENRES.items():
        for kw in info["words"][:4]:
            url = f"https://collabo-cafe.com/?s={kw}"
            try:
                res = requests.get(url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                articles = soup.select('article')
                for art in articles[:8]:
                    title_tag = art.find('h2') or art.select_one('.entry-title')
                    if not title_tag: continue
                    title = title_tag.get_text().strip()
                    link = art.find('a')['href']
                    start, end = extract_dates_v3(title)
                    
                    loc = "1時間半以内"
                    if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                    elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                    elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ", "富士急"]): loc = "2時間半以内"
                    elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                    if start:
                        all_events.append({
                            "id": f"{kw}-{title[:15]}", "title": f"{info['emoji']} {kw}",
                            "full_title": title, "start": start, "end": end,
                            "genre": gen, "time": loc, "url": link, "color": info["color"]
                        })
            except: pass
    df = pd.DataFrame(all_events).drop_duplicates(subset=['full_title'])
    return df.to_dict('records')

# --- メイン画面 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 スケジュール図鑑")

# 1. 更新ボタンの配置
if st.button("🔄 最新の情報に更新する"):
    st.cache_data.clear()  # キャッシュを削除
    st.success("キャッシュをクリアしました。最新情報を再取得します...")
    # st.rerun() は自動で行われます

# 2. フィルター
c1, c2 = st.columns(2)
with c1:
    sel_gen = st.multiselect("🌈 ジャンル選択", list(GENRES.keys()), default=list(GENRES.keys()))
with c2:
    sel_time = st.multiselect("⏳ 小山からの時間", TIME_OPTIONS, default=TIME_OPTIONS)

# 3. データ取得
with st.spinner("イベント情報をスキャン中..."):
    data = fetch_huge_data()
    filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

# 4. カレンダー表示
st.subheader("📅 推しカレンダー")
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], 
        "start": e['start'].strftime("%Y-%m-%d"), 
        "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto", "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}})

# 5. 詳細表示
if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""
        <div class="pop-card">
            <h3 style='color:#1E40AF; margin-top:0;'>✨ イベント詳細</h3>
            <b>{p['full_title']}</b><br><br>
            <span class="badge" style="background:{GENRES[p['gen']]['color']}">{p['gen']}</span>
            <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
            <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
            <a href="{p['url']}" target="_blank"><button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトへ GO!</button></a>
        </div>
    """, unsafe_allow_html=True)

# 6. 週間リスト
st.subheader("📋 今後のピックアップ")
today = datetime.now().date()
sorted_events = sorted(filtered, key=lambda x: x['start'])
for e in sorted_events:
    if e['start'].date() >= today:
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 10px rgba(0,0,0,0.05);">
                <small>{e['start'].strftime('%m/%d')} 〜 {e['end'].strftime('%m/%d')} | {e['genre']}</small><br>
                <b>{e['full_title']}</b><br>
                <small style="color:#3B82F6;">🚃 {get_access_info(e['time'])}</small>
            </div>
        """, unsafe_allow_html=True)
