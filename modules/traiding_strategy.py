from config import Config

# ====================== Торговая стратегия ======================
class TradingStrategy:
    def __init__(self, data_handler):
        self.data_handler = data_handler
    
    def check_entry_conditions(self, symbol, btc_dominance):
        """Проверка условий для входа в позицию"""
        if symbol not in self.data_handler.indicators:
            print(f"[Strategy] Нет индикаторов для {symbol}")
            return False
        ind = self.data_handler.indicators[symbol]
        funding_ok = self.data_handler.funding_rates.get(symbol, 0)

        # Получаем пороги для монеты
        spread_threshold, volume_ratio_threshold = self.data_handler.get_thresholds_for_symbol(symbol)

        # --- Новый блок: условия с динамическими порогами ---
        conditions = (
            ind['volume_ratio'] >= volume_ratio_threshold and
            ind['ob_spread'] <= spread_threshold and
            ind['atr'] >= ind['close'] * Config.ATR_THRESHOLD and
            ind['ema_short'] > ind['ema_long'] and
            btc_dominance < Config.BTC_DOM_THRESHOLD and
            funding_ok > Config.FUND_RATE_THRESHOLD and
            ind['ob_ratio'] >= 1.5 and
            len(ind['ob_large_bids']) > 0 and
            len(ind['ob_walls']) == 0
        )
        print(f"[Strategy] Условия для {symbol}: "
              f"funding_ok={funding_ok > Config.FUND_RATE_THRESHOLD}, "
              f"volume_ratio={ind['volume_ratio'] >= Config.VOLUME_RATIO}, "
              f"atr={ind['atr'] >= ind['close'] * Config.ATR_THRESHOLD}, "
              f"ema_long={ind['ema_short'] > ind['ema_long']} -> {'OK' if conditions else 'NO'}")
        print(f"[Strategy] Условия для {symbol}: funding_ok={funding_ok}, volume_ratio={ind['volume_ratio']}, atr={ind['atr']}, ema_short={ind['ema_short']}, ema_long={ind['ema_long']}, btc_dom={btc_dominance} -> {'OK' if conditions else 'NO'}")
        return conditions

