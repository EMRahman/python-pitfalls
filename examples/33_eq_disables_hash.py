"""Defining __eq__ without __hash__ makes a class unhashable."""

from dataclasses import dataclass


# The trap
class Symbol:
    def __init__(self, ticker):
        self.ticker = ticker

    def __eq__(self, other):
        return self.ticker == other.ticker


print(Symbol.__hash__)  # None
assert Symbol.__hash__ is None
try:
    {Symbol("AAPL")}
except TypeError as e:
    print(e)  # unhashable type: 'Symbol'
else:
    raise AssertionError("expected TypeError")


# A plain @dataclass does the same: eq=True sets __hash__ to None.
@dataclass
class SymbolData:
    ticker: str


assert SymbolData.__hash__ is None


# The fix: define a matching __hash__, or use a frozen dataclass.
@dataclass(frozen=True)
class SymbolFixed:
    ticker: str


assert {SymbolFixed("AAPL"), SymbolFixed("AAPL")} == {SymbolFixed("AAPL")}
