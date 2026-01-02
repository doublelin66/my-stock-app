import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# 1. 頁面設定
st.set_page_config(page_title="台股技術分析", layout="wide")
st.title("📈 台股個股技術分析 (Yahoo Finance)")

# 2. 側邊欄
st.sidebar.header("設定參數")
ticker_input = st.sidebar.text_input("輸入股票代號", value="2330.TW")
start_date = st.sidebar.date_input("開始日期", datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("結束日期", datetime.now())
st.sidebar.markdown("---")
st.sidebar.info("資料來源：Yahoo Finance")

# 3. 抓取資料 (終極防呆版)
def load_data(ticker, start, end):
    try:
        # 使用 yf.download 抓取
        df = yf.download(ticker, start=start, end=end)
        
        # --- 資料清洗區 (修復 ValueError 的關鍵) ---
        
        # 1. 如果是多層索引 (MultiIndex)，強制攤平
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # 2. 移除重複的欄位 (Yahoo有時候會給兩個 Close，這是報錯主因)
        df = df.loc[:, ~df.columns.duplicated()]
        
        # 3. 確保索引時區移除
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        return df
    except Exception as e:
        return None

# 4. 主程式邏輯
if ticker_input:
    data = load_data(ticker_input, start_date, end_date)

    if data is not None and not data.empty:
        try:
            # 計算 MA (使用 try-except 保護計算過程)
            data['MA5'] = data['Close'].rolling(window=5).mean()
            data['MA20'] = data['Close'].rolling(window=20).mean()
            data['MA60'] = data['Close'].rolling(window=60).mean()

            # 取得最新資訊
            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            change = latest['Close'] - prev['Close']
            pct_change = (change / prev['Close']) * 100 if prev['Close'] != 0 else 0

            # 顯示指標
            col1, col2, col3 = st.columns(3)
            col1.metric("收盤價", f"{latest['Close']:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
            col2.metric("成交量", f"{int(latest['Volume']):,}")
            col3.metric("資料日期", str(latest.name.date()))

            # 繪圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                vertical_spacing=0.03, subplot_titles=('股價', '成交量'), 
                                row_width=[0.2, 0.7])
            
            fig.add_trace(go.Candlestick(x=data.index, open=data['Open'], high=data['High'],
                                         low=data['Low'], close=data['Close'], name="K線"), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], line=dict(color='orange', width=1), name='MA5'), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='green', width=1), name='MA20'), row=1, col=1)
            
            colors = ['red' if row['Open'] - row['Close'] >= 0 else 'green' for i, row in data.iterrows()]
            fig.add_trace(go.Bar(x=data.index, y=data['Volume'], marker_color=colors, name="成交量"), row=2, col=1)
            
            fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"資料處理發生錯誤，請稍後再試: {e}")
    else:
        st.warning("找不到資料，請確認代號是否正確 (例如 2330.TW)")
