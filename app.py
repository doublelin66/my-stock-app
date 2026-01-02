import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# 1. 頁面設定
st.set_page_config(page_title="台股智慧分析", layout="wide")
st.title("📈 台股個股智慧分析 (自動偵測上市櫃)")

# 2. 側邊欄
st.sidebar.header("設定參數")
# 這裡提示使用者只需要輸入數字
ticker_input = st.sidebar.text_input("輸入股票代號 (直接輸入數字，例如 8069)", value="2330")
start_date = st.sidebar.date_input("開始日期", datetime.now() - timedelta(days=365))
end_date = st.sidebar.date_input("結束日期", datetime.now())
st.sidebar.markdown("---")
st.sidebar.info("資料來源：Yahoo Finance")

# 3. 智慧抓取函數 (自動切換 .TW / .TWO)
def load_data(ticker, start, end):
    # 如果使用者沒有輸入後綴，自動嘗試補上
    tickers_to_try = []
    if "." not in ticker:
        tickers_to_try = [f"{ticker}.TW", f"{ticker}.TWO"] # 先試上市，再試上櫃
    else:
        tickers_to_try = [ticker] # 如果使用者自己有打 .TW/.TWO 就照舊

    for t in tickers_to_try:
        try:
            df = yf.download(t, start=start, end=end)
            
            # --- 資料清洗區 ---
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.loc[:, ~df.columns.duplicated()]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            # 如果抓到的資料不是空的，就代表猜對了！回傳資料與正確的代號
            if not df.empty:
                return df, t 
        except Exception:
            continue
            
    return None, None # 都找不到

# 4. 主程式邏輯
if ticker_input:
    # 呼叫上面的智慧函數
    data, valid_ticker = load_data(ticker_input, start_date, end_date)

    if data is not None and not data.empty:
        # 顯示目前抓到的是哪個代號
        st.success(f"成功找到：{valid_ticker}")
        
        try:
            data['MA5'] = data['Close'].rolling(window=5).mean()
            data['MA20'] = data['Close'].rolling(window=20).mean()
            data['MA60'] = data['Close'].rolling(window=60).mean()

            latest = data.iloc[-1]
            prev = data.iloc[-2] if len(data) > 1 else latest
            change = latest['Close'] - prev['Close']
            pct_change = (change / prev['Close']) * 100 if prev['Close'] != 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("收盤價", f"{latest['Close']:.2f}", f"{change:.2f} ({pct_change:.2f}%)")
            col2.metric("成交量", f"{int(latest['Volume']):,}")
            col3.metric("資料日期", str(latest.name.date()))

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
            st.error(f"繪圖錯誤: {e}")
    else:
        st.warning(f"找不到代號 {ticker_input}，請確認是否為有效台股代號。")
