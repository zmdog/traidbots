import time

# ====================== Мониторинг позиций ======================
class PositionMonitor:
    def __init__(self, exchange, order_executor):
        self.exchange = exchange
        self.order_executor = order_executor
        self.active_positions = {}
    
    def add_position(self, position):
        """Добавление новой позиции"""
        position_id = f"{position['symbol']}-{time.time()}"
        self.active_positions[position_id] = position
        print(f"[PositionMonitor] Позиция добавлена: {position_id} -> {position}")
        return position_id
    
    def check_position(self, position_id):
        """Проверка состояния позиции"""
        position = self.active_positions[position_id]
        current_price = self.get_current_price(position['symbol'])
        print(f"[PositionMonitor] Проверка позиции {position_id}: текущая цена {current_price}, SL={position['stop_loss']}, TP={position['take_profit']}")
        
        # Проверка стоп-лосса и тейк-профита
        if current_price <= position['stop_loss']:
            self.order_executor.close_position(position)
            return 'stop_loss'
        
        if current_price >= position['take_profit']:
            self.order_executor.close_position(position)
            return 'take_profit'
        
        # Проверка времени удержания
        if time.time() - position['entry_time'] > 900:  # 15 минут
            self.order_executor.close_position(position)
            return 'timeout'
        
        return 'active'
    
    def get_current_price(self, symbol):
        """Получение текущей цены"""
        ticker = self.exchange.exchange.fetch_ticker(symbol)
        return ticker['last']