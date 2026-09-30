"""Cấu hình SignalBot (paper trading). Sửa TRƯỚC khi chạy lần đầu."""
import os

EXCHANGE = os.getenv("EXCHANGE", "kraken")   # sàn lấy giá (chỉ đọc dữ liệu công khai)
SYMBOLS = ["BTC/USDT", "ETH/USDT"]
TIMEFRAME = "1h"                             # giữ 1h (code tính theo giờ)
DB_PATH = os.getenv("DB_PATH", "paper.db")

START_EQUITY = 1000.0      # vốn ảo (USDT)
FEE = 0.001                # phí 0.1% mỗi chiều
SLIPPAGE = 0.0005          # trượt giá 0.05%
RISK_PER_TRADE = 0.01      # rủi ro tối đa 1% vốn mỗi lệnh
MIN_NOTIONAL = 10.0        # lệnh nhỏ hơn 10 USDT thì bỏ
ATR_SL = 2.0               # stop-loss = entry - 2*ATR
ATR_TP = 3.0               # take-profit = entry + 3*ATR
BUY_SCORE = 2              # điểm >= 2 -> BUY
SELL_SCORE = -2            # điểm <= -2 -> SELL (đóng vị thế)
NEWS_BLOCK = -0.5          # tin xấu mạnh (<= -0.5) chặn BUY

NEWS_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
]
COIN_WORDS = {"BTC": ["bitcoin", "btc"], "ETH": ["ethereum", "eth", "ether"]}

# Tiêu chí đánh giá: ĐẶT TRƯỚC, bị "đóng băng" vào DB ở lần chạy đầu.
CRITERIA = {
    "min_uptime": 0.95,        # >= 95% số giờ có lần chạy thành công
    "sl_coverage": 1.0,        # 100% lệnh có stop-loss hợp lệ
    "max_underperf_pct": 2.0,  # không kém mua-và-giữ quá 2 điểm %
    "max_drawdown_pct": 10.0,  # sụt giảm tối đa <= 10%
    "min_trades": 30,          # tối thiểu 30 lệnh đã đóng mới đủ mẫu
}
