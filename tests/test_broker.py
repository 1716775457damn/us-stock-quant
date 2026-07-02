"""Test broker simulation."""
import pytest
from broker.simulated import SimulatedBroker
from broker.base import OrderSide, OrderStatus


def test_initial_state():
    broker = SimulatedBroker(initial_cash=50000)
    assert broker.get_cash() == 50000
    assert broker.get_portfolio_value() == 50000
    assert len(broker.get_positions()) == 0


def test_buy_order():
    broker = SimulatedBroker(initial_cash=100000)
    order = broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    assert order.status == OrderStatus.FILLED
    assert broker.get_cash() == 100000 - 1500
    pos = broker.get_position("AAPL")
    assert pos is not None
    assert pos.qty == 10
    assert pos.avg_price == 150.0


def test_sell_order():
    broker = SimulatedBroker(initial_cash=100000)
    broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    order = broker.place_order("AAPL", OrderSide.SELL, 5, 160.0)
    assert order.status == OrderStatus.FILLED
    assert broker.get_cash() == 100000 - 1500 + 800
    pos = broker.get_position("AAPL")
    assert pos.qty == 5


def test_insufficient_cash():
    broker = SimulatedBroker(initial_cash=100)
    order = broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    assert order.status == OrderStatus.REJECTED


def test_sell_without_position():
    broker = SimulatedBroker(initial_cash=100000)
    order = broker.place_order("AAPL", OrderSide.SELL, 10, 150.0)
    assert order.status == OrderStatus.REJECTED


def test_portfolio_value():
    broker = SimulatedBroker(initial_cash=100000)
    broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    broker.update_price("AAPL", 160.0)
    # 100000 - 1500 + (10 * 160) = 100100
    assert broker.get_portfolio_value() == 100100


def test_full_sell_removes_position():
    broker = SimulatedBroker(initial_cash=100000)
    broker.place_order("AAPL", OrderSide.BUY, 10, 150.0)
    broker.place_order("AAPL", OrderSide.SELL, 10, 160.0)
    assert broker.get_position("AAPL") is None
