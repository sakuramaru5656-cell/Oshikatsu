import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# --- ページ設定とデザイン ---
st.set_page_config(page_title="推しイベ", page_icon="✨", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@700;800&display=swap');
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    
    /* カレンダーデザイン */
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; }
    .fc-event { border-radius: 8px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    .fc-toolbar-title { color: #1E40AF !important; font-size: 1.2em !important; background: #DBEAFE; padding: 5px 15px; border-radius: 50px; }
    
    /* カードデザイン */
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 定数定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "さくらみこ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["Snow Man", "King & Prince", "なにわ男子", "Hey! Say! JUMP"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんスタ", "あんさんぶるスターズ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "ピューロランド", "USJ", "ディズニー", "ナンジャタウン"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ", "カフェ"], "color": "#94A3B8"}
}

TIME_OPTIONS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 宇都宮線 (25分) / 🚗 車 (40分)",
        "1時間以内": "🚄 新幹線 (15分) / 🚃 快速 (45分)",
        "1時間半以内": "🚄 新幹線 (40分) / 🚃 在来線 (80分)",
        "2時間半以内": "🚃 湘南新宿ライン (130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機"
    }
    return guides.get(loc, "交通機関を確認してください")

# --- 日付抽出エンジン ---
def parse_dates_robust(text):
    # 2026年8月時点のコンテキストに合わせて解析
    curr_year = 2026 
    sep = r'[〜~ー\-\s－]+'
    # 期間形式: 8/1〜8/30
    m = re.search(r'(\d{1,2})[./月](\d{1,2})[日]?{sep}(\d{1,2})[./月](\d{1,2})[日]?'.format(sep=sep), text)
    if m:
        try:
            start = datetime(curr_year, int(m.group(1)), int(m.group(2)))
            end = datetime(curr_year, int(m.group(3)), int(m.group(4)))
            if end < start: end = datetime(curr_year + 1, int(m.group(3)), int(m.group(4)))
            return start, end
        except: pass
    # 単発: 8/1
    m = re.search(r'(\d{1,2})[./月](\d{1,2})', text)
    if m:
        try:
            dt = datetime(curr_year, int(m.group(1)), int(m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_all_data(selected_genres):
    all_events = []
    # 偽装ブラウザヘッダー
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    
    search_words = []
    for g in selected_genres:
        search_words.extend(GENRES[g]["words"])

    for kw in list(set(search_words))[:15]:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200: continue
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.select('article')
            for art in articles[:5]:
                title_el = art.find('h2') or art.select_one('.entry-title')
                if not title_el: continue
                title = title_el.get_text().strip()
                link = art.find('a')['href']
                
                start_dt, end_dt = parse_dates_robust(title)
                
                # エリア判定
                loc = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                elif any(x in title for x in ["大宮", "さいたま"]): loc = "1時間以内"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ", "富士急"]): loc = "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ"]): loc = "それ以上"

                if start_dt:
                    emoji, color = "🎁", "#94A3B8"
                    for g_name, info in GENRES.items():
                        if any(w in title or w in kw for w in info["words"]):
                            emoji, color = info["emoji"], info["color"]
                            found_gen = g_name
                            break

                    all_events.append({
                        "id": f"{kw}-{title[:10]}", "title": f"{emoji} {kw}",
                        "full_title": title, "start": start_dt.strftime("%Y-%m-%d"),
                        "end": (end_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "color": color, "url": link, "time_cat": loc, "gen": found_gen if 'found_gen' in locals() else "その他"
                    })
        except: pass
    return all_events

# --- メイン画面 ---
st.title("✨ 推しイベ")
st.write("栃木県小山駅発 🚃 冒険スケジュール（2026年版）")

# カレンダーの上のフィルター
c1, c2 = st.columns(2)
with c1:
    selected_genres = st.multiselect("🌈 ジャンル選択", list(GENRES.keys()), default=list(GENRES.keys()))
with c2:
    selected_times = st.multiselect("⏳ 小山からの時間", TIME_OPTIONS, default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内"])

# データの取得
with st.spinner("最新情報をロード中..."):
    data = fetch_all_data(selected_genres)
    filtered = [e for e in data if e['time_cat'] in selected_times]

# 3. カレンダー表示
if not filtered:
    st.info("現在、条件に合うイベントが見つかりません。ジャンルをすべて選択して試してみてください。")
else:
    cal_events = []
    for e in filtered:
        cal_events.append({
            "id": e['id'], "title": e['title'], "start": e['start'], "end": e['end'],
            "backgroundColor": e['color'], "borderColor": "white",
            "extendedProps": {"full_title": e['full_title'], "url": e['url'], "time": e['time_cat'], "gen": e['gen']}
        })

    state = calendar(events=cal_events, options={
        "initialView": "dayGridMonth",
        "locale": "ja",
        "height": "auto",
        "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}
    })

    # 詳細表示（カレンダーの下）
    if state.get("eventClick"):
        p = state["eventClick"]["event"]["extendedProps"]
        st.markdown(f"""
            <div class="pop-card">
                <h3 style='color:#1E40AF; margin-top:0;'>✨ イベント詳細</h3>
                <b>{p['full_title']}</b><br><br>
                <span class="badge" style="background:{GENRES.get(p['gen'], {'color':'#94A3B8'})['color']}">{p['gen']}</span>
                <span class="badge" style="background:#3B82F6">📍 小山から{p['time']}</span><br><br>
                <small>🚃 経路目安: {get_access_info(p['time'])}</small><br><br>
                <a href="{p['url']}" target="_blank">
                    <button style="width:100%; background:#3B82F6; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">公式サイトへ GO!</button>
                </a>
            </div>
        """, unsafe_allow_html=True)

# 週間リスト
st.subheader("📋 直近の予定")
today = datetime.now().date()
upcoming = [e for e in filtered if today <= datetime.strptime(e['start'], "%Y-%m-%d").date() <= today + timedelta(days=14)]

if not upcoming:
    st.write("2週間以内の予定はありません。")
else:
    for e in sorted(upcoming, key=lambda x: x['start']):
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['color']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
                <small>{e['start']} | {e['gen']}</small><br>
                <b>{e['full_title']}</b><br>
                <small style="color:#3B82F6;">🚃 {get_access_info(e['time_cat'])}</small>
            </div>
        """, unsafe_allow_html=True)
