from config import Config
import pandas as pd
import talib
import math
import time
import numpy as np
import threading  # <--- добавлено

# ====================== Обработка данных ======================
class DataHandler:
    def __init__(self):
        self.lock = threading.Lock()
        self.ohlcv = {}         # Исторические данные OHLCV
        self.order_books = {}   # Стаканы ордеров
        self.indicators = {}    # Рассчитанные индикаторы
        self.funding_rates = {}  # Текущие ставки финансирования
        self.last_funding_update = 0  # Время последнего обновления ставок финансирования
    def update_order_book(self, symbol, bids, asks):
        """Обновление стакана ордеров (вызывается из WebSocket)"""
        with self.lock:
            self.order_books[symbol] = {
                'bids': sorted(bids, key=lambda x: x[0], reverse=True),
                'asks': sorted(asks, key=lambda x: x[0])
        }
        self.calculate_order_book_metrics(symbol)
        self.calculate_dynamic_order_book_settings(symbol)  # <--- добавлено
    def calculate_order_book_metrics(self, symbol):
        """Расчет метрик стакана ордеров"""
        if symbol not in self.order_books:
            return

        ob = self.order_books[symbol]
        bids = ob['bids']
        asks = ob['asks']
        if not bids or not asks:
            return

        # Используем динамические параметры, если они есть
        if hasattr(self, 'dynamic_order_book_settings') and symbol in self.dynamic_order_book_settings:
            settings = self.dynamic_order_book_settings[symbol]
        else:
            settings = {
                'CLUSTER_THRESHOLD': 50000,
                'WALL_THRESHOLD': 100000,
                'ZONE_PCT': 0.005,
                'RATIO_MIN': 1.5,
            }

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        mid_price = (best_bid + best_ask) / 2

        bid_volume = sum(price * amount for price, amount in bids if price >= mid_price * (1 - settings['ZONE_PCT']))
        ask_volume = sum(price * amount for price, amount in asks if price <= mid_price * (1 + settings['ZONE_PCT']))

        large_bids = [(price, price * amount) for price, amount in bids if price * amount > settings['CLUSTER_THRESHOLD']]
        large_asks = [(price, price * amount) for price, amount in asks if price * amount > settings['CLUSTER_THRESHOLD']]
        walls = []
        for price, amount in bids:
            value = price * amount
            if value > settings['WALL_THRESHOLD']:
                walls.append(('bid', price, value))
        for price, amount in asks:
            value = price * amount
            if value > settings['WALL_THRESHOLD']:
                walls.append(('ask', price, value))

        if symbol not in self.indicators:
            self.indicators[symbol] = {}

        self.indicators[symbol].update({
            'ob_bid_volume': bid_volume,
            'ob_ask_volume': ask_volume,
            'ob_ratio': bid_volume / ask_volume if ask_volume > 0 else 0,
            'ob_large_bids': large_bids,
            'ob_large_asks': large_asks,
            'ob_walls': walls,
            'ob_mid_price': mid_price,
            'ob_spread': best_ask - best_bid
        })  
    def update_ohlcv(self, exchange, symbol):
        """Обновление исторических данных"""
        try:
            print(f"[DataHandler] Запрос OHLCV для {symbol}...")
            new_data = exchange.exchange.fetch_ohlcv(
                symbol, 
                Config.TIMEFRAME, 
                limit=100
            )
            print(f"[DataHandler] Получено {len(new_data)} свечей для {symbol}")
            df = pd.DataFrame(
                new_data, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            self.ohlcv[symbol] = df
            print(f"[DataHandler] OHLCV сохранён для {symbol}")
            self.calculate_indicators(symbol)
        except Exception as e:
            print(f"[DataHandler] Ошибка обновления OHLCV для {symbol}: {e}")
    def update_funding_rates(self, exchange):
        """Обновление ставок финансирования каждые 30 минут"""
        if time.time() - self.last_funding_update < 1800:  # 30 минут
            return

        self.funding_rates = {}
        for symbol in Config.SYMBOLS:
            try:
                # Для фьючерсов
                perp_symbol = f"{symbol.split('/')[0]}/USDT:USDT"
                rate = exchange.exchange.fetch_funding_rate(perp_symbol)
                print(f"полученный фандинг {symbol}: {rate['fundingRate']}")
                self.funding_rates[symbol] = rate['fundingRate']
            except Exception as e:
                print(f"Funding rate error for {symbol}: {e}")
                self.funding_rates[symbol] = 0  # Нейтральное значение

        self.last_funding_update = time.time()           
    def calculate_indicators(self, symbol):
        """Расчет технических индикаторов"""
        if symbol not in self.ohlcv:
            print(f"[DataHandler] Нет данных OHLCV для {symbol}, индикаторы не рассчитываются")
            return
        print(f"[DataHandler] Расчёт индикаторов для {symbol}...")
        df = self.ohlcv[symbol]
        
        # Рассчет индикаторов
        df['ema_short'] = talib.EMA(df['close'], Config.EMA_SHORT)
        df['ema_long'] = talib.EMA(df['close'], Config.EMA_LONG)
        df['atr'] = talib.ATR(
            df['high'], 
            df['low'], 
            df['close'], 
            Config.ATR_PERIOD
        )
        
        # Volume SMA
        df['volume_sma'] = talib.SMA(df['volume'], 20)
        
        # Сохранение последних значений
        last_row = df.iloc[-1]
        volume_sma = last_row['volume_sma']
        if not volume_sma or math.isnan(volume_sma):
            volume_ratio = 0
        else:
            volume_ratio = last_row['volume'] / volume_sma

        self.indicators[symbol] = {
            'ema_short': last_row['ema_short'],
            'ema_long': last_row['ema_long'],
            'atr': last_row['atr'],
            'volume': last_row['volume'],
            'volume_sma': volume_sma,
            'volume_ratio': volume_ratio,
            'close': last_row['close']
        }
        print(f"[DataHandler] Индикаторы рассчитаны для {symbol}: EMA_short={df['ema_short'].iloc[-1]}, EMA_long={df['ema_long'].iloc[-1]}, ATR={df['atr'].iloc[-1]}")
    def calculate_dynamic_order_book_settings(self, symbol, history=100):
        """Автоматический расчет параметров стакана по истории"""
        # Сохраняем последние N снимков стакана
        if not hasattr(self, 'order_book_history'):
            self.order_book_history = {}
        if symbol not in self.order_book_history:
            self.order_book_history[symbol] = []
        self.order_book_history[symbol].append(self.order_books[symbol])
        if len(self.order_book_history[symbol]) > history:
            self.order_book_history[symbol] = self.order_book_history[symbol][-history:]

        # Собираем статистику по объёмам
        bid_volumes = []
        ask_volumes = []
        all_bid_orders = []
        all_ask_orders = []
        for ob in self.order_book_history[symbol]:
            bids = ob['bids']
            asks = ob['asks']
            bid_volumes.append(sum([price * amount for price, amount in bids]))
            ask_volumes.append(sum([price * amount for price, amount in asks]))
            all_bid_orders += [price * amount for price, amount in bids]
            all_ask_orders += [price * amount for price, amount in asks]

        # Расчет порогов
        cluster_threshold = np.percentile(all_bid_orders + all_ask_orders, 90)
        wall_threshold = np.percentile(all_bid_orders + all_ask_orders, 99)
        ratio_min = np.percentile(
            [b/a for b, a in zip(bid_volumes, ask_volumes) if a > 0], 50
        )
        zone_pct = 0.005  # Можно тоже рассчитать динамически

        # Сохраняем в отдельный словарь
        if not hasattr(self, 'dynamic_order_book_settings'):
            self.dynamic_order_book_settings = {}
        self.dynamic_order_book_settings[symbol] = {
            'CLUSTER_THRESHOLD': cluster_threshold,
            'WALL_THRESHOLD': wall_threshold,
            'ZONE_PCT': zone_pct,
            'RATIO_MIN': ratio_min,
        }
    def calculate_atr(self, symbol, period=5):
        ohlcv = self.exchange.exchange.fetch_ohlcv(symbol, '5m', limit=period+1)
        highs = [x[2] for x in ohlcv]
        lows = [x[3] for x in ohlcv]
        closes = [x[4] for x in ohlcv]
        return talib.ATR(np.array(highs), np.array(lows), np.array(closes), period)[-1]

    def volume_analysis(self, symbol):
        """Улучшенный анализ объема с адаптивным окном"""
        current_volume = self.get_current_volume(symbol)
        historical_volumes = self.get_historical_volumes(symbol, period=30)
        
        # Адаптивное окно на основе волатильности
        volatility_factor = self.get_normalized_atr(symbol) / 3.0
        period = max(15, min(30, int(25 - volatility_factor * 5)))
        
        if len(historical_volumes) < period:
            return False
            
        avg_volume = talib.SMA(np.array(historical_volumes[-period:]), period)[-1]
        ratio = current_volume / avg_volume if avg_volume > 0 else 0
        
        return ratio > self.calculate_dynamic_volume_threshold(symbol)

    def liquidity_monitor(self, symbol):
        order_book = self.exchange.fetch_order_book(symbol)
    
        # Динамический расчет спреда
        best_bid = order_book['bids'][0][0]
        best_ask = order_book['asks'][0][0]
        spread = (best_ask - best_bid) / best_bid
        
        # Адаптивная глубина стакана
        daily_volume = self.get_24h_volume(symbol)
        depth_threshold = max(500000, daily_volume * 0.0005)  # 0.05% от дневного объема
        
        # Расчет реальной ликвидности
        def calculate_depth(side, depth_percent=0.005):
            depth_price = best_bid * (1 - depth_percent) if side == 'bid' else best_ask * (1 + depth_percent)
            return sum(
                qty * price
                for price, qty in order_book['bids' if side == 'bid' else 'asks']
                if (price >= depth_price if side == 'bid' else price <= depth_price)
            )
        
        bid_depth = calculate_depth('bid')
        ask_depth = calculate_depth('ask')
        
        return {
            'spread': spread,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'liquidity_ok': min(bid_depth, ask_depth) > depth_threshold
        }

    def order_book_analysis(self, symbol):
        ob = self.exchange.fetch_order_book(symbol)
        current_price = (ob['bids'][0][0] + ob['asks'][0][0]) / 2
        
        # Адаптивные пороги
        daily_volume = self.get_24h_volume(symbol)
        levels = 10 if daily_volume > 1_000_000 else 5  # Для ликвидных пар больше уровней
        wall_threshold = max(100000, daily_volume * 0.0002)  # 0.02% от объема
        cluster_threshold = wall_threshold * 0.5
        
        # Поиск стен
        def detect_walls(side, levels=levels):
            for i in range(levels):
                price, qty = ob[side][i]
                value = qty * price
                if value > wall_threshold:
                    distance = abs(price - current_price) / current_price
                    if distance < 0.005:  # 0.5%
                        return True
            return False
        
        # Поиск кластеров
        def detect_clusters(side, levels=levels):
            cluster_found = False
            for i in range(levels):
                price, qty = ob[side][i]
                value = qty * price
                if value > cluster_threshold:
                    cluster_found = True
            return cluster_found
        
        # Соотношение сил
        bid_value = sum(qty * price for price, qty in ob['bids'][:5])
        ask_value = sum(qty * price for price, qty in ob['asks'][:5])
        ratio = bid_value / ask_value if ask_value > 0 else 1
        
        return {
            'has_bid_walls': detect_walls('bids'),
            'has_ask_walls': detect_walls('asks'),
            'has_bid_clusters': detect_clusters('bids'),
            'has_ask_clusters': detect_clusters('asks'),
            'bid_ask_ratio': ratio,
            'safe_to_trade': not (detect_walls('bids') or detect_walls('asks')) and 
                            ratio > 1.5 and 
                            detect_clusters('bids')
        }

    def get_thresholds_for_symbol(self, symbol):
        if symbol in ['BTC/USDT', 'ETH/USDT']:
            return 0.08 / 100, 1.5
        else:
            return 0.15 / 100, 2.2

    def get_current_volume(self, symbol):
        """Получить текущий объем из последних OHLCV"""
        if symbol in self.ohlcv:
            return self.ohlcv[symbol]['volume'].iloc[-1]
        return 0

    def get_historical_volumes(self, symbol, period=20):
        """Получить исторические объемы для расчета SMA"""
        if symbol in self.ohlcv:
            return self.ohlcv[symbol]['volume'].iloc[-period:].values
        return np.zeros(period)

    def get_24h_volume(self, symbol):
        """Получить 24-часовой объем через биржу"""
        try:
            ticker = self.exchange.exchange.fetch_ticker(symbol)
            return ticker.get('quoteVolume', 0)
        except Exception:
            return 0

    def calculate_dynamic_atr_threshold(self, symbol):
        """Рассчитывает динамический порог ATR на основе исторической волатильности"""
        if symbol not in self.ohlcv or len(self.ohlcv[symbol]) < 50:
            return 0.03  # Значение по умолчанию
        
        df = self.ohlcv[symbol]
        
        # Расчет исторической волатильности
        atr_values = df['atr'].dropna()
        if len(atr_values) < 20:
            return 0.03
            
        mean_atr = atr_values.mean()
        std_atr = atr_values.std()
        
        # Адаптивный порог (базовое значение + поправка на волатильность)
        base_threshold = 0.025 if 'USDT' in symbol else 0.04
        volatility_factor = (std_atr / mean_atr) if mean_atr > 0 else 1.0
        return min(max(base_threshold, base_threshold * volatility_factor * 1.2), 0.06)
    
    def get_normalized_atr(self, symbol):
        """Возвращает ATR в % от текущей цены"""
        if symbol in self.indicators:
            ind = self.indicators[symbol]
            return (ind['atr'] / ind['close']) * 100
        return 0
    
    def calculate_dynamic_volume_threshold(self, symbol):
        """Рассчитывает динамический порог для объема"""
        normalized_atr = self.get_normalized_atr(symbol)
        
        # Базовый порог в зависимости от типа монеты
        base_threshold = 1.8 if symbol in ['BTC/USDT', 'ETH/USDT'] else 2.2
        
        # Корректировка на волатильность
        volatility_factor = normalized_atr / 3.0  # Нормализация к 3%
        return base_threshold * max(0.8, min(1.5, 1.0 + (volatility_factor - 1) * 0.2))
    
    def auto_calibrate_parameters(self):
        """Автоматическая калибровка параметров стратегии"""
        total_atr = 0
        count = 0
        
        for symbol in self.ohlcv:
            if len(self.ohlcv[symbol]) > 100:
                total_atr += self.get_normalized_atr(symbol)
                count += 1
                
        if count > 0:
            market_volatility = total_atr / count
            
            # Динамическое обновление параметров
            Config.ATR_THRESHOLD = max(0.025, min(0.045, market_volatility * 0.75 / 100))
            Config.VOLUME_RATIO = max(1.8, min(2.3, 2.0 - (market_volatility - 3) * 0.05))
            
            print(f"[Calibration] Updated params: "
                f"ATR_THRESHOLD={Config.ATR_THRESHOLD:.4f}, "
                f"VOLUME_RATIO={Config.VOLUME_RATIO:.2f}")

    def optimize_parameters(self):
        """Оптимизация порогов анализа на основе истории (пример)"""
        historical_data = self.load_last_week_trades()  # реализуйте этот метод
        # Здесь можно использовать ML, например, sklearn
        # from sklearn.ensemble import RandomForestRegressor
        # model = RandomForestRegressor()
        # model.fit(historical_data[features], historical_data['profit'])
        # predicted_thresholds = model.predict(current_market_conditions)
        # Config.VOLUME_RATIO = predicted_thresholds[0]
        # Config.SPREAD_THRESHOLD = predicted_thresholds[1]
        pass