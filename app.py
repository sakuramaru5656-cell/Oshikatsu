import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re
from concurrent.futures import ThreadPoolExecutor

# --- ページ設定とデザイン ---
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
    .stButton>button { width: 100%; border-radius: 20px; font-weight: 800; border: 2px solid #3B82F6; }
    </style>
    """, unsafe_allow_html=True)

# --- キーワード設定 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "ぶいすぽ", "さくらみこ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ポケカ"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["Snow Man", "なにわ男子", "King & Prince", "timelesz", "SixTONES"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "ピューロランド", "USJ", "ディズニー"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ", "ポップアップストア"], "color": "#94A3B8"}
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

def extract_dates(text):
    year = datetime.now().year
    sep = r'[〜~ー\-\s－]+'
    m = re.search(r'(\d{1,2})[./月](\d{1,2}).*?{sep}(\d{1,2})[./月](\d{1,2})'.format(sep=sep), text)
    if m:
        try:
            s, e = datetime(year, int(m.group(1)), int(m.group(2))), datetime(year, int(m.group(3)), int(m.group(4)))
            if e < s: e = datetime(year + 1, int(m.group(3)), int(m.group(4)))
            return s, e
        except: pass
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

# --- 並列データ取得関数 ---
def fetch_single_keyword(kw, genre_name, emoji, color):
    """1つのキーワードを検索する（スレッド用）"""
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://collabo-cafe.com/?s={kw}"
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        for art in soup.select('article')[:5]:
            title = (art.find('h2') or art.select_one('.entry-title')).get_text().strip()
            link = art.find('a')['href']
            start, end = extract_dates(title)
            
            if start:
                loc = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "富士急"]): loc = "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                results.append({
                    "id": f"{kw}-{title[:15]}", "title": f"{emoji} {kw}",
                    "full_title": title, "start": start, "end": end,
                    "genre": genre_name, "time": loc, "url": link, "color": color
                })
    except: pass
    return results

@st.cache_data(ttl=1800)
def fetch_all_data_fast():
    tasks = []
    for gen, info in GENRES.items():
        for kw in info["words"]:
            tasks.append((kw, gen, info["emoji"], info["color"]))

    # ThreadPoolExecutorで並列実行 (最大10スレッド)
    all_results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_single_keyword, *t) for t in tasks]
        for f in futures:
            all_results.extend(f.result())
            
    if not all_results: return []
    df = pd.DataFrame(all_results).drop_duplicates(subset=['full_title'])
    return df.to_dict('records')

# --- メイン画面 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 高速スキャン版")

if st.button("🔄 最新の情報に更新する"):
    st.cache_data.clear()
    st.success("最新情報を取得し直します！")

c1, c2 = st.columns(2)
with c1: sel_gen = st.multiselect("🌈 ジャンル", list(GENRES.keys()), default=list(GENRES.keys()))
with c2: sel_time = st.multiselect("⏳ 時間", TIME_OPTIONS, default=TIME_OPTIONS)

with st.spinner("🚀 推し情報を並列スキャン中..."):
    data = fetch_all_data_fast()
    filtered = [e for e in data if e['genre'] in sel_gen and e['time'] in sel_time]

# --- カレンダー ---
cal_events = []
for e in filtered:
    cal_events.append({
        "id": e['id'], "title": e['title'], "start": e['start'].strftime("%Y-%m-%d"), 
        "end": (e['end'] + timedelta(days=1)).strftime("%Y-%m-%d"),
        "backgroundColor": e['color'], "borderColor": "white",
        "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time'], "gen": e['genre']}
    })

state = calendar(events=cal_events, options={"initialView": "dayGridMonth", "locale": "ja", "height": "auto", "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}})

if state.get("eventClick"):
    p = state["eventClick"]["event"]["extendedProps"]
    st.markdown(f"""<div class="pop-card"><h3>✨ 詳細</h3><b>{p['full_title']}</b><br><br>
        <span class="badge" style="background:{GENRES[p['gen']]['color']}">{p['gen']}</span>
        <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
        <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
        <a href="{p['url']}" target="_blank"><button style="background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer;">公式サイトへ GO!</button></a></div>""", unsafe_allow_html=True)

# 週間リスト
st.subheader("📋 今後のピックアップ")
today = datetime.now().date()
for e in sorted(filtered, key=lambda x: x['start']):
    if e['start'].date() >= today:
        st.markdown(f"""<div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
            <small>{e['start'].strftime('%m/%d')} 〜 {e['end'].strftime('%m/%d')} | {e['genre']}</small><br>
            <b>{e['full_title']}</b><br><small style="color:#3B82F6;">🚃 {get_access_info(e['time'])}</small></div>""", unsafe_allow_html=True)
