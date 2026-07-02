"""Simulated broker — paper trading for testing."""
from datetime import datetime
from .base import BrokerBase, Order, OrderSide, OrderStatus, Position


class SimulatedBroker(BrokerBase):
    """In-memory simulated broker for paper trading."""

    def __init__(self, initial_cash: float = 100_000):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions: dict[str, Position] = {}
        self.orders: list[Order] = []
        self.order_counter = 0

    def place_order(self, symbol: str, side: OrderSide, qty: float, price: float | None = None) -> Order:
        self.order_counter += 1
        order_id = f"SIM-{self.order_counter:06d}"

        # Use current position price as fill price for market orders
        if price is None:
            pos = self.positions.get(symbol)
            if pos:
                price = pos.current_price
            else:
                price = 0.0  # Would need a price feed

        order = Order(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            filled_price=price,
            status=OrderStatus.FILLED,
            order_id=order_id,
        )
        self.orders.append(order)

        # Update positions and cash
        if side == OrderSide.BUY:
            cost = qty * price
            if cost > self.cash:
                order.status = OrderStatus.REJECTED
                return order
            self.cash -= cost
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_qty = pos.qty + qty
                pos.avg_price = (pos.avg_price * pos.qty + price * qty) / total_qty
                pos.qty = total_qty
                pos.update_price(price)
            else:
                self.positions[symbol] = Position(symbol=symbol, qty=qty, avg_price=price)
                self.positions[symbol].update_price(price)
        elif side == OrderSide.SELL:
            pos = self.positions.get(symbol)
            if not pos or pos.qty < qty:
                order.status = OrderStatus.REJECTED
                return order
            self.cash += qty * price
            pos.qty -= qty
            pos.update_price(price)
            if pos.qty == 0:
                del self.positions[symbol]

        return order

    def update_price(self, symbol: str, current_price: float):
        """Update current price for a position."""
        if symbol in self.positions:
            self.positions[symbol].update_price(current_price)

    def get_position(self, symbol: str) -> Position | None:
        return self.positions.get(symbol)

    def get_positions(self) -> list[Position]:
        return list(self.positions.values())

    def get_cash(self) -> float:
        return self.cash

    def get_portfolio_value(self) -> float:
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value

    def get_summary(self) -> dict:
        return {
            "initial_cash": self.initial_cash,
            "cash": round(self.cash, 2),
            "positions_value": round(sum(p.market_value for p in self.positions.values()), 2),
            "total_value": round(self.get_portfolio_value(), 2),
            "total_pnl": round(self.get_portfolio_value() - self.initial_cash, 2),
            "position_count": len(self.positions),
            "total_orders": len(self.orders),
        }
