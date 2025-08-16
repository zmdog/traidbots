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

        # Динамические пороги
        dyn_atr_threshold = self.data_handler.calculate_dynamic_atr_threshold(symbol)
        normalized_atr = self.data_handler.get_normalized_atr(symbol)
        dyn_volume_threshold = self.data_handler.calculate_dynamic_volume_threshold(symbol)

        # --- Новый блок: условия с динамическими порогами ---
        conditions = (
            ind['volume_ratio'] >= volume_ratio_threshold and
            normalized_atr >= dyn_atr_threshold * 100 and  # Умножаем на 100 для перевода в %
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
              f"volume_ratio={ind['volume_ratio'] >= ind['volume_ratio']}, "
              f"atr={ind['atr'] >= ind['close'] * Config.ATR_THRESHOLD}, "
              f"ema_long={ind['ema_short'] > ind['ema_long']} -> {'OK' if conditions else 'NO'}")
        print(f"[Dynamic Check] {symbol}: "
          f"VolRatio={ind['volume_ratio']:.2f}/{dyn_volume_threshold:.2f}, "
          f"ATR={normalized_atr:.2f}%/{dyn_atr_threshold*100:.2f}%")
        print(f"[Strategy] Условия для {symbol}: funding_ok={funding_ok}, volume_ratio={ind['volume_ratio']}, atr={ind['atr']}, ema_short={ind['ema_short']}, ema_long={ind['ema_long']}, btc_dom={btc_dominance} -> {'OK' if conditions else 'NO'}")
        return conditions

