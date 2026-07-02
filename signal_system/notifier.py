"""Signal notifier — push trading signals to messaging platforms."""
import subprocess
import json
from datetime import datetime


class SignalNotifier:
    """Push trading signals via Hermes gateway (WeChat/Feishu) or webhook."""

    def __init__(self, platform: str = "wechat", webhook_url: str = None):
        self.platform = platform
        self.webhook_url = webhook_url

    def format_signal_message(self, summary: dict) -> str:
        """Format a signal summary into a readable message."""
        symbol = summary["symbol"]
        overall = summary["overall_signal"]
        price = summary.get("price", "N/A")
        buy = summary["buy_signals"]
        sell = summary["sell_signals"]
        hold = summary["hold_signals"]
        date = summary["date"]

        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
        icon = emoji.get(overall, "⚪")

        lines = [
            f"{icon} {symbol} 信号报告 {date}",
            f"综合信号: {overall}",
            f"当前价格: ${price}",
            f"买入信号: {buy}  卖出信号: {sell}  观望: {hold}",
            "",
            "--- 细分指标 ---",
        ]

        for d in summary.get("details", []):
            if "error" in d:
                lines.append(f"  {d['signal']}: ERROR - {d['error']}")
                continue
            sig_name = d.get("signal", "?")
            action = d.get("action", "?")
            parts = [f"  {sig_name}: {action}"]
            for k, v in d.items():
                if k not in ("signal", "action", "date"):
                    parts.append(f"{k}={v}")
            lines.append(" | ".join(parts))

        return "\n".join(lines)

    def send_via_hermes(self, message: str) -> bool:
        """Send via hermes CLI (if available)."""
        try:
            result = subprocess.run(
                ["hermes", "send", "--message", message],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[NOTIFIER] Hermes send failed: {e}")
            return False

    def send_via_webhook(self, message: str) -> bool:
        """Send via HTTP webhook (e.g. WeCom bot, Feishu bot)."""
        if not self.webhook_url:
            print("[NOTIFIER] No webhook URL configured")
            return False
        import requests
        try:
            resp = requests.post(
                self.webhook_url,
                json={"text": message},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception as e:
            print(f"[NOTIFIER] Webhook send failed: {e}")
            return False

    def notify(self, summary: dict) -> bool:
        """Format and send a signal notification."""
        message = self.format_signal_message(summary)
        print(f"\n[NOTIFIER] Signal message:\n{message}\n")

        # Try webhook first, then hermes
        if self.webhook_url:
            return self.send_via_webhook(message)
        return self.send_via_hermes(message)

    def notify_batch(self, summaries: list[dict]) -> list[bool]:
        """Send notifications for multiple symbols. Combines into one message if possible."""
        results = []
        for s in summaries:
            ok = self.notify(s)
            results.append(ok)
        return results
