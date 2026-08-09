import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import re

# ページ設定
st.set_page_config(page_title="オタ活カレンダー(小山発)", layout="wide")

# --- CSSで見た目を調整 ---
st.markdown("""
    <style>
    .stApp { background-color: #fdfbfb; }
    .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

st.title("🌸 推し活アクセス・カレンダー")
st.caption("栃木県小山駅からイベント会場までの「時間」を色で表示します")

# --- サイドバー設定 ---
with st.sidebar:
    st.header("⚙️ 設定")
    keywords = st.text_input("検索ワード（カンマ区切り）", value="さくらみこ, ホロライブ")
    
    st.header("⏳ 移動時間フィルター")
    selected_times = st.multiselect(
        "表示する範囲",
        ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"],
        default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]
    )
    st.info("📍 出発：小山駅")

# --- データ取得・解析 ---
@st.cache_data(ttl=3600)
def get_event_data(keywords_str):
    all_events = []
    kw_list = [k.strip() for k in keywords_str.split(",")]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for kw in kw_list:
        url = f"https://collabo-cafe.com/?s={kw}"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.find_all('article')[:10]:
                title = art.find('h2').get_text().strip()
                link = art.find('a')['href']
                
                # エリアと時間の判定ロジック
                loc = "都内"
                if "大阪" in title: loc = "大阪"
                elif "名古屋" in title: loc = "名古屋"
                elif "横浜" in title: loc = "横浜"
                elif "宇都宮" in title: loc = "宇都宮"
                elif "大宮" in title: loc = "大宮"

                # 小山駅からのアクセス判定 (時間, ラベル, 色, 手段)
                access_map = {
                    "宇都宮": (30, "30分以内", "#28a745", "JR宇都宮線"), # 緑
                    "大宮": (50, "1時間以内", "#007bff", "宇都宮線 快速"), # 青
                    "都内": (80, "1時間半以内", "#f1c40f", "上野東京ライン"), # 黄
                    "横浜": (130, "2時間半以内", "#e67e22", "湘南新宿ライン"), # 橙
                    "大阪": (220, "それ以上", "#e74c3c", "新幹線"), # 赤
                    "名古屋": (180, "それ以上", "#e74c3c", "新幹線"), # 赤
                }
                mins, label, color, way = access_map.get(loc, (999, "不明", "#95a5a6", "要確認"))
                
                # 日付の抽出（デモ用にタイトルから推測、なければ今日から順に割り振り）
                date_match = re.search(r'(\d+)月(\d+)日', title)
                if date_match:
                    day = datetime(2024, int(date_match.group(1)), int(date_match.group(2)))
                else:
                    day = datetime.now() + timedelta(days=len(all_events) % 14)

                all_events.append({
                    "title": f"【{label}】{title}",
                    "start": day.strftime("%Y-%m-%d"),
                    "end": day.strftime("%Y-%m-%d"),
                    "color": color,
                    "url": link,
                    "cat": label,
                    "way": way,
                    "loc": loc
                })
        except: pass
    return all_events

# --- メイン表示 ---
event_list = get_event_data(keywords)
# フィルター適用
filtered_events = [e for e in event_list if e['cat'] in selected_times]

# カレンダーの表示形式を選択
view_mode = st.radio("表示モード", ["月間カレンダー", "週間スケジュール", "リスト形式"], horizontal=True)

if view_mode == "月間カレンダー":
    calendar_options = {
        "initialView": "dayGridMonth",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"},
        "selectable": True,
    }
    calendar(events=filtered_events, options=calendar_options)

elif view_mode == "週間スケジュール":
    calendar_options = {
        "initialView": "listWeek",
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
    }
    calendar(events=filtered_events, options=calendar_options)

else:
    for e in filtered_events:
        st.markdown(f"""
        <div style="border-left: 5px solid {e['color']}; padding: 10px; margin-bottom: 10px; background: white; border-radius: 5px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
            <small>{e['start']} | {e['cat']} ({e['way']})</small><br>
            <strong><a href="{e['url']}" target="_blank" style="color: #333; text-decoration: none;">{e['title']}</a></strong>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("💡 色の意味（小山駅からの所要時間）:")
st.markdown("🟢30分以内 | 🔵1時間以内 | 🟡1時間半以内 | 🟠2時間半以内 | 🔴それ以上")
