from modules.exchange import Exchange
from modules.traiding_strategy import TradingStrategy
from modules.data_handler import DataHandler
from modules.risk_manager import RiskManager
from modules.order_executor import OrderExecutor
from modules.position_monitor import PositionMonitor
from config import Config
import time
import requests
# ====================== Основной класс бота ======================
class ScalpingBot:
    def __init__(self):
        self.data_handler = DataHandler()
        self.exchange = Exchange(self.data_handler)
        self.strategy = TradingStrategy(self.data_handler)
        self.risk_manager = RiskManager(self.exchange)
        self.order_executor = OrderExecutor(self.exchange)
        self.position_monitor = PositionMonitor(self.exchange, self.order_executor)
        self.btc_dominance = 60.0  # Начальное значение (будет обновляться)
        
    def run(self):
        """Основной цикл работы бота"""
        print("[ScalpingBot] Ожидание инициализации данных (15 секунд)...")
        time.sleep(15)  # Дать время на запуск WebSocket и получение первых данных
        while True:
            try:
                print("=== Обновление данных ===")
                self.update_data()
                
                print("=== Проверка активных позиций ===")
                self.check_active_positions()
                
                print("=== Поиск новых торговых возможностей ===")
                self.find_trading_opportunities()
                
                print("=== Ожидание следующей итерации ===\n")
                time.sleep(5)  # Пауза между итерациями
                
            except Exception as e:
                print(f"Critical error: {e}")
                time.sleep(30)

    def fetch_btc_dominance(self):
        """Получение доминирования BTC с CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/global"
            response = requests.get(url, timeout=10)
            data = response.json()
            dominance = data['data']['market_cap_percentage']['btc']
            print(f"[ScalpingBot] BTC dominance обновлено: {dominance}")
            return dominance
        except Exception as e:
            print(f"[ScalpingBot] Ошибка получения BTC dominance: {e}")
            return self.btc_dominance  # оставить старое значение

    def update_data(self):
        """Обновление рыночных данных"""
        print("Обновление BTC доминирования...")
        self.btc_dominance = self.fetch_btc_dominance()
        print("Обновление ставок фандинга...")
        self.data_handler.update_funding_rates(self.exchange)
        for symbol in Config.SYMBOLS:
            print(f"Обновление OHLCV для {symbol}...")
            self.data_handler.update_ohlcv(self.exchange, symbol)
            time.sleep(0.5)  # Короткая пауза между запросами (опционально)

    def check_active_positions(self):
        """Проверка активных позиций"""
        for position_id in list(self.position_monitor.active_positions.keys()):
            print(f"Проверка позиции {position_id}...")
            status = self.position_monitor.check_position(position_id)
            if status != 'active':
                print(f"Position {position_id} closed: {status}")
                del self.position_monitor.active_positions[position_id]

    def find_trading_opportunities(self):
        """Поиск новых торговых возможностей"""
        for symbol in Config.SYMBOLS:
            ind = self.data_handler.indicators.get(symbol)
            required_keys = ['ema_short', 'ema_long', 'atr', 'volume_ratio', 'close',
                             'ob_ratio', 'ob_bid_volume', 'ob_ask_volume', 'ob_spread', 'ob_mid_price']
            if not ind or not all(k in ind and ind[k] is not None for k in required_keys):
                print(f"[ScalpingBot] Данные для анализа {symbol} ещё не готовы, пропуск.")
                continue
            print(f"Проверка условий входа для {symbol}...")
            if self.strategy.check_entry_conditions(symbol, self.btc_dominance):
                print(f"Условия входа выполнены для {symbol}, открытие позиции...")
                self.create_position(symbol)
            else:
                print(f"Условия входа не выполнены для {symbol}")

    def create_position(self, symbol):
        """Создание новой позиции"""
        print(f"Создание позиции для {symbol}...")
        current_price = self.position_monitor.get_current_price(symbol)
        stop_loss_price = self.risk_manager.get_stop_loss_price(current_price)
        take_profit_price = self.risk_manager.get_take_profit_price(current_price)
        position_size = self.risk_manager.calculate_position_size(
            current_price, 
            stop_loss_price
        )
        print(f"Параметры позиции: цена входа={current_price}, SL={stop_loss_price}, TP={take_profit_price}, размер={position_size}")
        order = self.order_executor.place_order(
            symbol=symbol,
            side='buy',
            amount=position_size,
            price=current_price * 1.0005
        )
        if order:
            position = {
                'symbol': symbol,
                'entry_price': current_price,
                'stop_loss': stop_loss_price,
                'take_profit': take_profit_price,
                'size': position_size,
                'entry_time': time.time()
            }
            self.position_monitor.add_position(position)
            print(f"New position opened for {symbol} at {current_price}")
        else:
            print(f"Не удалось открыть позицию для {symbol}")