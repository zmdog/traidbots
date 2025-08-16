# ====================== Конфигурация ======================
class Config:
    EXCHANGE = 'binance'  # binance, kucoin, bybit
    SYMBOLS = ['SOL/USDT', 'ARB/USDT', 'HBAR/USDT']  # Торгуемые пары
    TIMEFRAME = '5m'     # Таймфрейм для свечей
    RISK_PER_TRADE = 0.005  # Риск на сделку (0.5%)
    MAX_POSITIONS = 5     # Макс. одновременных позиций
    
    # Параметры стратегии
    VOLUME_RATIO = 2.0    # Минимальное отношение объема к среднему
    ATR_PERIOD = 5        # Период ATR
    ATR_THRESHOLD = 0.03  # Минимальная волатильность (3%)
    EMA_SHORT = 8         # Короткая EMA
    EMA_LONG = 20         # Длинная EMA
    BTC_DOM_THRESHOLD = 65 # Макс. доминирование BTC
    FUND_RATE_THRESHOLD = -0.0001  # Минимальный фандинг для входа

    


















































    




