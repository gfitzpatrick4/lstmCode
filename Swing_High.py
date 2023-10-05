"""
this script tests the momentum stragety with lumnibot
"""

# importing the trader class
from lumibot.traders import Trader
# importing the alpaca broker class
from lumibot.brokers import Alpaca

from datetime import datetime

from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader

ALPACA_CONFIG = {
    # Put your own Alpaca key here:
    "API_KEY": "PK3Q7LTBDWU9EB4WEBGD",
    # Put your own Alpaca secret here:
    "API_SECRET": "6Nwfkq65pFAGrykYO841EkeYdwavHIbFam3ObQMk",
    # If you want to go live, you must change this. It is currently set for paper trading
    "ENDPOINT": "https://paper-api.alpaca.markets"
}

class SwingHigh(Strategy):
    data = []
    order_number = 0

    def initialize(self):
        self.sleeptime = "5S"
        self.entry_price = None  # Initialize entry_price as None

    def on_trading_iteration(self):
        symbol = "RIVN"

        self.log_message(f"Position: {self.get_position(symbol)}")
        self.data.append(self.get_last_price(symbol))

        if len(self.data) > 3:
            temp = self.data[-3:]
            print(self.get_position(symbol))
            print(self.data[-1])
            if temp[-1] > temp[1] > temp[0]:
                self.log_message(f"Last 3 prints: {temp}")
                order = self.create_order(symbol, quantity=5000, side="buy")
                self.submit_order(order)
                self.entry_price = temp[-1]  # Set entry_price when a buy order is placed
                self.order_number += 1
                if self.order_number == 1:
                    self.log_message(f"Entry price: {temp[-1]}")
                    self.initial_position_value = self.entry_price * 100  # Assuming quantity is 100

        position = self.get_position(symbol)
        if position is not None:
            current_price = self.get_last_price(symbol)

            # Check if entry_price is not None before calculating profit_percentage
            if self.entry_price is not None:
                profit_percentage = (current_price - self.entry_price) / self.entry_price * 100
                print((self.entry_price - current_price) * 100)
                print((self.initial_position_value * 0.10))

                # Check for the stop-loss condition (loss of more than 5%)
                if profit_percentage < -0.5:
                    loss_amount = (self.entry_price - current_price) * position.quantity
                    print(f"Stop Loss Triggered! Loss Amount: {loss_amount}")
                    order = self.create_order(symbol, quantity=position.quantity, side="sell")
                    self.submit_order(order)
                    self.sell_all()
                    self.order_number = 0

                # Check for the 15% profit-taking condition based on initial position value
            elif (self.entry_price)*1.15 < current_price:
                    profit_amount = (current_price - self.entry_price) * position.quantity
                    print(f"Profit Taking Triggered! Profit Amount: {profit_amount}")
                    order = self.create_order(symbol, quantity=position.quantity, side="sell")
                    self.submit_order(order)
                    self.sell_all()
                    self.order_number = 0

    def before_market_closes(self):
        self.sell_all()

if __name__ == "__main__":
    broker = Alpaca(ALPACA_CONFIG)
    strategy = SwingHigh(broker=broker)
    trader = Trader()
    trader.add_strategy(strategy)
    trader.run_all()
