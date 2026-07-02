"""Signal system — generate trading signals from strategies."""
from .generator import SignalGenerator
from .notifier import SignalNotifier

__all__ = ["SignalGenerator", "SignalNotifier"]
