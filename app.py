import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# 1. 網頁基本設定
st.set_page_config(page_title="台股即時分析儀表板", layout="wide")

st.title("📈 台股個股技術分析 (Yahoo Finance)")

# 2. 側邊欄設定 (Sidebar)
st.sidebar.header("設定參數")
ticker_input = st.sidebar.text_input("輸入股票代號 (請加 .TW 或 .TWO)", value="2330.TW")
start_date = st.sidebar.date_input("開始日期", datetime.now() - timedelta(days=180))
end_date = st.sidebar.date_input("結束日期", datetime.now())

st.sidebar.markdown("---")
st.sidebar.info("資料來源：Yahoo Finance (延遲報價)")

# 3. 抓取資料函數 (修復版)
def load_data(ticker, start, end):
    try:
        # 改用 Ticker.history，這會回傳更乾淨的單層索引資料
        stock = yf.Ticker(ticker)
        df = stock.history(start=start, end=end)
        # 確保時區移除，避免繪圖錯誤
        df.index = df.index.tz_localize(None)
        return df
    except Exception as e:
        st.error(f"資料抓取失敗: {e}")
        return None

# 執行邏輯
if ticker_input:
    data = load_data(ticker_input, start_date, end_date)

    if data is not None and not data.empty:
        # 再次確保沒有多層索引 (Double Check)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # 計算移動平均線 (MA)
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA60'] = data['Close'].rolling(window=60).mean()

        # 取得最新一筆資料
        latest = data.iloc[-1]
        # 如果資料不足兩筆，避免報錯
        if len(data) > 1:
            prev = data.iloc[-2]
            change = latest['Close'] - prev['Close']
            pct_change = (change / prev['Close']) * 100
        else:
            change = 0
            pct_change = 0

        # 4. 顯示即時指標
        col1, col2, col3 = st.columns(3)
        col1.metric("收盤價", f"{latest['Close']:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
        col2.metric("成交量", f"{int(latest['Volume']):,}")
        col3.metric("資料日期", str(latest.name.date()))

        # 5. 繪製互動圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.03, subplot_titles=('股價走勢', '成交量'), 
                            row_width=[0.2, 0.7])

        # K 線圖
        fig.add_trace(go.Candlestick(x=data.index,
                                     open=data['Open'], high=data['High'],
                                     low=data['Low'], close=data['Close'], name="K線"), 
                                     row=1, col=1)

        # MA 線
        fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], line=dict(color='orange', width=1), name='MA5'), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='green', width=1), name='MA20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA60'], line=dict(color='purple', width=1), name='MA60'), row=1, col=1)

        # 成交量
        colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for index, row in data.iterrows()]
        fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name="成交量"), row=2, col=1)

        fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning(f"查無資料，請確認股票代號是否正確 (例如 2330.TW)。")
