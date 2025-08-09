import ccxt
from config import Config
import threading
from websocket import create_connection
import json
import time

# ====================== Подключение к бирже ======================
class Exchange:
    def __init__(self, data_handler):
        self.data_handler = data_handler
        self.exchange = self.connect()
        self.ws_connections = {}
        self.start_websockets()
        
    def connect(self):
        exchange_class = getattr(ccxt, Config.EXCHANGE)
        return exchange_class({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
    
    def start_websockets(self):
        """Запуск WebSocket соединений для каждой пары"""
        for symbol in Config.SYMBOLS:
            self.start_ws_thread(symbol)
    
    def start_ws_thread(self, symbol):
        """Запуск потока для WebSocket"""
        thread = threading.Thread(target=self.websocket_listener, args=(symbol,))
        thread.daemon = True
        thread.start()
    
    def websocket_listener(self, symbol):
        """Прослушивание данных через WebSocket"""
        ws_url = self.get_ws_url(symbol)
        print(f"[Exchange] WebSocket подключение для {symbol}: {ws_url}")
        ws = create_connection(ws_url)
        while True:
            try:
                data = json.loads(ws.recv())
                self.process_ws_data(symbol, data)
            except Exception as e:
                print(f"[Exchange] WebSocket error for {symbol}: {e}")
                time.sleep(5)
                ws = create_connection(ws_url)
    
    def get_ws_url(self, symbol):
        """Генерация URL для WebSocket (фьючерсы Binance USDM)"""
        stream_name = f"{symbol.replace('/', '').lower()}@depth@100ms"
        if Config.EXCHANGE == 'binanceusdm':
            return f"wss://fstream.binance.com/ws/{stream_name}"
        else:
            return f"wss://stream.binance.com:9443/ws/{stream_name}"
    
    def process_ws_data(self, symbol, data):
        bids = data.get('bids') or data.get('b') or []
        asks = data.get('asks') or data.get('a') or []
        # Если оба массива пустые — это просто "пустое" обновление, не надо спамить
        if not bids and not asks:
            return
        # Если хотя бы один массив не пустой — обновляем стакан
        if bids and asks:
            bids = [[float(b[0]), float(b[1])] for b in bids]
            asks = [[float(a[0]), float(a[1])] for a in asks]
            self.data_handler.update_order_book(
                symbol,
                bids=bids,
                asks=asks
            )
