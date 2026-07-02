"""Base broker interface."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    qty: float
    price: float | None = None  # None = market order
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    order_id: str | None = None


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0

    def update_price(self, price: float):
        self.current_price = price
        self.market_value = self.qty * price
        self.unrealized_pnl = (price - self.avg_price) * self.qty


class BrokerBase(ABC):
    """Abstract broker interface. Implement this to add a real broker."""

    @abstractmethod
    def place_order(self, symbol: str, side: OrderSide, qty: float, price: float | None = None) -> Order:
        """Place an order."""
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Position | None:
        """Get current position for a symbol."""
        pass

    @abstractmethod
    def get_positions(self) -> list[Position]:
        """Get all open positions."""
        pass

    @abstractmethod
    def get_cash(self) -> float:
        """Get available cash."""
        pass

    @abstractmethod
    def get_portfolio_value(self) -> float:
        """Get total portfolio value (cash + positions)."""
        pass
