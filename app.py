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
    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', sans-serif; background-color: #FFFDF0; }
    .stApp { background: #FFFDF0; }
    
    /* カレンダーデザイン */
    .fc { background: white !important; border-radius: 20px !important; border: 4px solid #3B82F6 !important; padding: 10px; }
    .fc-event { border-radius: 8px !important; border: none !important; padding: 4px 6px !important; font-weight: 800 !important; cursor: pointer; }
    
    /* ポップなカード */
    .pop-card { background: white; border-radius: 20px; padding: 20px; margin-top: 15px; border: 4px solid #3B82F6; box-shadow: 6px 6px 0px #BFDBFE; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: bold; color: white; margin-right: 5px; }
    
    /* ヘッダー */
    .main-header { color: #1E40AF; text-align: center; font-size: 2.5em; margin-bottom: 0px; }
    </style>
    """, unsafe_allow_html=True)

# --- 定数定義 ---
GENRES = {
    "VTuber": {"emoji": "🌈", "words": ["ホロライブ", "にじさんじ", "ぶいすぽ", "さくらみこ"], "color": "#F472B6"},
    "ポケモン": {"emoji": "🐾", "words": ["ポケモンセンター", "ポケモン", "ポケカ"], "color": "#3B82F6"},
    "アイドル": {"emoji": "🎤", "words": ["Snow Man", "なにわ男子", "King & Prince", "timelesz", "Hey! Say! JUMP"], "color": "#FB923C"},
    "あんスタ": {"emoji": "✨", "words": ["あんさんぶるスターズ", "あんスタ"], "color": "#A78BFA"},
    "ジャンプ": {"emoji": "👒", "words": ["ワンピース", "ONE PIECE", "ナルト", "NARUTO"], "color": "#F87171"},
    "テーマパーク": {"emoji": "🎡", "words": ["富士急ハイランド", "サンリオピューロランド", "USJ", "ディズニー", "ナンジャタウン", "ジョイポリス"], "color": "#10B981"},
    "その他": {"emoji": "🎁", "words": ["アニメ コラボ", "イベント", "フェア"], "color": "#94A3B8"}
}

TIME_OPTIONS = ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]

def get_access_info(loc):
    guides = {
        "30分以内": "🚃 宇都宮線 (25分) / 🚗 車 (40分)",
        "1時間以内": "🚄 新幹線 (15分) / 🚃 快速 (45分)",
        "1時間半以内": "🚄 新幹線 (40分) / 🚃 在来線 (80分)",
        "2時間半以内": "🚃 湘南新宿ライン (130分) / 🚄 新幹線+JR",
        "それ以上": "🚄 新幹線 / ✈️ 飛行機 / 🚌 高速バス"
    }
    return guides.get(loc, "交通機関を確認してください")

# --- 日付抽出ロジック ---
def parse_dates_2026(text):
    year = 2026 # 現在の時刻設定に合わせる
    sep = r'[〜~ー\-\s－]+'
    # 期間形式
    range_m = re.search(r'(\d{1,2})[./月](\d{1,2})[日]?{sep}(\d{1,2})[./月](\d{1,2})[日]?'.format(sep=sep), text)
    if range_m:
        try:
            start = datetime(year, int(range_m.group(1)), int(range_m.group(2)))
            end = datetime(year, int(range_m.group(3)), int(range_m.group(4)))
            if end < start: end = datetime(year + 1, int(range_m.group(3)), int(range_m.group(4)))
            return start, end
        except: pass
    # 単発
    single_m = re.search(r'(\d{1,2})[./月](\d{1,2})[日]?', text)
    if single_m:
        try:
            dt = datetime(year, int(single_m.group(1)), int(single_m.group(2)))
            return dt, dt
        except: pass
    return None, None

@st.cache_data(ttl=1800)
def fetch_event_data(selected_genres):
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # ジャンルに紐づくワードで検索
    search_keywords = []
    for g in selected_genres:
        search_keywords.extend(GENRES[g]["words"])

    # 検索ヒット率を上げるためのループ
    for kw in list(set(search_keywords))[:15]:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.select('article')
            for art in articles[:6]:
                title_el = art.find('h2') or art.select_one('.entry-title')
                if not title_el: continue
                title = title_el.get_text().strip()
                link = art.find('a')['href']
                
                start, end = parse_dates_2026(title)
                
                # 開催場所の判定（小山駅起点）
                loc = "1時間半以内"
                if any(x in title for x in ["宇都宮", "ベルモール"]): loc = "30分以内"
                elif any(x in title for x in ["大宮", "さいたま", "スーパーアリーナ"]): loc = "1時間以内"
                elif any(x in title for x in ["横浜", "幕張", "千葉", "Kアリーナ", "ぴあアリーナ", "富士急"]): loc = "2時間半以内"
                elif any(x in title for x in ["大阪", "名古屋", "USJ", "福岡"]): loc = "それ以上"

                if start:
                    # 絵文字決定
                    emoji, color = "🎁", "#94A3B8"
                    for g_name, info in GENRES.items():
                        if any(w in title or w in kw for w in info["words"]):
                            emoji, color = info["emoji"], info["color"]
                            current_gen = g_name
                            break

                    all_events.append({
                        "id": f"{kw}-{title[:10]}",
                        "display_title": f"{emoji} {kw}",
                        "full_title": title,
                        "start": start.strftime("%Y-%m-%d"),
                        "end": (end + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "backgroundColor": color,
                        "url": link,
                        "time_cat": loc,
                        "genre_name": current_gen if 'current_gen' in locals() else "その他"
                    })
        except: pass
    return all_events

# --- メイン画面 ---
st.markdown('<h1 class="main-header">✨ 推しイベ</h1>', unsafe_allow_html=True)
st.write("<div style='text-align:center; color:#666;'>栃木県小山駅発 🚃 冒険スケジュール図鑑</div>", unsafe_allow_html=True)

# 1. フィルター（カレンダーの上のボタン形式）
st.markdown("### 🔍 フィルター")
c1, c2 = st.columns(2)
with c1:
    selected_genres = st.multiselect("🌈 ジャンル選択", list(GENRES.keys()), default=list(GENRES.keys()))
with c2:
    selected_times = st.multiselect("⏳ 小山からの時間", TIME_OPTIONS, default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内"])

# 2. データ取得と反映
with st.spinner("最新情報をスキャン中..."):
    data = fetch_event_data(selected_genres)
    # 選択された時間で絞り込み
    filtered = [e for e in data if e['time_cat'] in selected_times]

# 3. カレンダー表示（一本線対応）
st.subheader("📅 推しカレンダー")
if not filtered:
    st.info("条件に合うイベントが現在見つかりませんでした。ジャンルの選択を増やしてみてください。")
else:
    # カレンダー用データ作成
    cal_events = []
    for e in filtered:
        cal_events.append({
            "id": e['id'],
            "title": e['display_title'],
            "start": e['start'],
            "end": e['end'],
            "backgroundColor": e['backgroundColor'],
            "borderColor": "white",
            "extendedProps": {
                "full_title": e['full_title'],
                "url": e['url'],
                "time": e['time_cat'],
                "gen": e['genre_name']
            }
        })

    state = calendar(events=cal_events, options={
        "initialView": "dayGridMonth",
        "locale": "ja",
        "height": "auto",
        "headerToolbar": {"left": "prev,next", "center": "title", "right": ""}
    })

    # 4. クリック詳細表示（カレンダーの下）
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

# 5. 週間表示
st.subheader("📋 今週のピックアップ")
today = datetime.now().date()
week_later = today + timedelta(days=7)
upcoming = [e for e in filtered if today <= datetime.strptime(e['start'], "%Y-%m-%d").date() <= week_later]

if not upcoming:
    st.write("直近1週間の予定はありません。")
else:
    for e in sorted(upcoming, key=lambda x: x['start']):
        st.markdown(f"""
            <div style="background:white; border-radius:15px; padding:15px; margin-bottom:10px; border-left:8px solid {e['backgroundColor']}; box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
                <small>{e['start']} | {e['genre_name']}</small><br>
                <b>{e['full_title']}</b><br>
                <small style="color:#3B82F6;">🚃 {get_access_info(e['time_cat'])}</small>
            </div>
        """, unsafe_allow_html=True)
