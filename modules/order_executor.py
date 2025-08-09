# ====================== Исполнение ордеров ======================
class OrderExecutor:
    def __init__(self, exchange):
        self.exchange = exchange
    
    def place_order(self, symbol, side, amount, price, order_type='limit'):
        """Размещение ордера"""
        print(f"[OrderExecutor] Размещение ордера: {side} {amount} {symbol} по цене {price} (тип: {order_type})")
        try:
            order = self.exchange.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params={'timeInForce': 'GTC'}
            )
            print(f"[OrderExecutor] Ордер размещён: {order}")
            return order
        except Exception as e:
            print(f"[OrderExecutor] Ошибка размещения ордера: {e}")
            return None

    def close_position(self, position):
        """Закрытие позиции"""
        print(f"[OrderExecutor] Закрытие позиции: {position}")
        # Реализация закрытия
        pass