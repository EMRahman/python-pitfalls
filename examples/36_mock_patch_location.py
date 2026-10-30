"""mock.patch must target the name where it is looked up, not where it is defined."""

import sys
import types
from unittest import mock

# Two tiny modules: report.py does `from prices import fetch`.
prices = types.ModuleType("prices")
exec("def fetch():\n    return 'live'", prices.__dict__)
sys.modules["prices"] = prices

report = types.ModuleType("report")
exec("from prices import fetch\ndef run():\n    return fetch()", report.__dict__)
sys.modules["report"] = report

# The trap: patching the definition doesn't touch report's copy of the name.
with mock.patch("prices.fetch", return_value="mocked"):
    print(report.run())  # 'live' (the test just hit the real service)
    assert report.run() == "live"

# The fix: patch the module that uses the name.
with mock.patch("report.fetch", return_value="mocked"):
    assert report.run() == "mocked"
