"""@lru_cache on a method caches `self`, so instances are never freed."""

import functools
import gc
import weakref


# The trap
class Portfolio:
    @functools.lru_cache(maxsize=None)
    def value(self):
        return 42


p = Portfolio()
p.value()
ref = weakref.ref(p)
del p
gc.collect()
print(f"instance still alive: {ref() is not None}")  # True (leaked)
assert ref() is not None
assert Portfolio.value.cache_info().currsize == 1


# The fix: cache per instance with cached_property (or a dict on the instance).
class PortfolioFixed:
    @functools.cached_property
    def value(self):
        return 42


p = PortfolioFixed()
assert p.value == 42
ref = weakref.ref(p)
del p
gc.collect()
assert ref() is None
