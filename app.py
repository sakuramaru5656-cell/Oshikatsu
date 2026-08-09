import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta

# ページ設定
st.set_page_config(page_title="オタ活アクセス検索(小山発)", layout="wide")

st.title("🌸 アニレコ！- 小山発イベント検索")
st.caption("栃木県小山市から「推し事」への最短ルートを判定します")

# --- 設定（サイドバー） ---
with st.sidebar:
    st.header("🔍 検索設定")
    keyword_input = st.text_input("検索キーワード（カンマ区切り）", value="さくらみこ, ホロライブ")
    
    st.header("⏳ 移動時間フィルター")
    time_filter = st.multiselect(
        "許容できる移動時間",
        ["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"],
        default=["30分以内", "1時間以内", "1時間半以内", "2時間半以内", "それ以上"]
    )
    
    departure = "小山駅"
    st.info(f"出発地点: {departure}")

# --- データ取得ロジック ---
def fetch_events(keywords):
    all_events = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for kw in keywords:
        url = f"https://collabo-cafe.com/?s={kw.strip()}"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for art in soup.find_all('article')[:8]:
                title = art.find('h2').get_text().strip()
                link = art.find('a')['href']
                
                # エリア判定ロジック
                loc = "都内"
                if "大阪" in title: loc = "大阪"
                elif "名古屋" in title: loc = "名古屋"
                elif "横浜" in title: loc = "横浜"
                elif "宇都宮" in title: loc = "宇都宮"
                elif "大宮" in title: loc = "大宮"
                
                # 仮の日付（本来は詳細ページから取得）
                date = datetime.now() + timedelta(days=len(all_events) * 2)
                all_events.append({"date": date, "name": title, "loc": loc, "url": link})
        except: pass
    return pd.DataFrame(all_events)

def get_access(loc):
    rules = {
        "宇都宮": (30, "30分以内", "JR宇都宮線", "🟢"),
        "大宮": (50, "1時間以内", "宇都宮線 快速", "🔵"),
        "都内": (80, "1時間半以内", "上野東京ライン", "🟡"),
        "横浜": (130, "2時間半以内", "湘南新宿ライン", "🟠"),
        "大阪": (220, "それ以上", "新幹線", "🔴"),
        "名古屋": (180, "それ以上", "新幹線", "🔴"),
    }
    return rules.get(loc, (999, "不明", "要確認", "⚪"))

# --- メイン処理 ---
keywords = keyword_input.split(",")
df = fetch_events(keywords)

if not df.empty:
    # アクセス情報適用
    df['access'] = df['loc'].apply(get_access)
    df['min'] = df['access'].apply(lambda x: x[0])
    df['cat'] = df['access'].apply(lambda x: x[1])
    df['way'] = df['access'].apply(lambda x: x[2])
    df['icon'] = df['access'].apply(lambda x: x[3])
    df = df.sort_values('min')

    # フィルター適用
    df = df[df['cat'].isin(time_filter)]

    # タブ表示
    tab1, tab2 = st.tabs(["📅 今月（全件）", "🗓 週間表示"])

    with tab1:
        for _, row in df.iterrows():
            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.write(f"### {row['icon']}")
                    st.caption(row['cat'])
                with col2:
                    st.markdown(f"**[{row['name']}]({row['url']})**")
                    st.caption(f"📅 {row['date'].strftime('%m/%d')} | 📍 {row['loc']} | 🚃 {row['way']}")
                st.divider()

    with tab2:
        next_week = datetime.now() + timedelta(days=7)
        weekly_df = df[df['date'] <= next_week]
        if weekly_df.empty:
            st.write("今週の予定はありません")
        else:
            st.dataframe(weekly_df[['date', 'cat', 'name']], hide_index=True)

else:
    st.warning("イベントが見つかりませんでした。キーワードを変えてみてください。")
