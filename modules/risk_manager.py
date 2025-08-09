from config import Config

# ====================== Управление рисками ======================
class RiskManager:
    def __init__(self, exchange):
        self.exchange = exchange
        self.balance = self.get_balance()
    
    def get_balance(self):
        """Получение текущего баланса"""
        print("[RiskManager] Запрос баланса...")
        balance = self.exchange.exchange.fetch_balance()
        usdt_balance = 0
        if 'total' in balance and 'USDT' in balance['total']:
            usdt_balance = balance['total']['USDT']
        elif 'USDT' in balance:
            # Иногда ccxt кладёт баланс прямо в верхний уровень
            usdt_balance = balance['USDT']
        print(f"[RiskManager] Баланс USDT: {usdt_balance}")
        return usdt_balance

    def calculate_position_size(self, entry_price, stop_loss_price):
        """Расчет размера позиции"""
        risk_amount = self.balance * Config.RISK_PER_TRADE
        price_difference = abs(entry_price - stop_loss_price)
        if price_difference == 0:
            print("[RiskManager] Ошибка: разница между ценой входа и стоп-лоссом равна 0!")
            return 0
        size = risk_amount / price_difference
        print(f"[RiskManager] Размер позиции: {size} (risk_amount={risk_amount}, price_diff={price_difference})")
        return size
    
    def get_stop_loss_price(self, entry_price, is_long=True):
        """Расчет цены стоп-лосса"""
        return entry_price * (0.992 if is_long else 1.008)
    
    def get_take_profit_price(self, entry_price, is_long=True):
        """Расчет цены тейк-профита"""
        return entry_price * (1.016 if is_long else 0.984)