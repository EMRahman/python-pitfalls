# Object Model and Import Pitfalls

[← Back to all pitfalls](../README.md)

Python's attribute lookup, descriptors and import system are a stack of indirections: `obj.x` may run a property, fall back to `__getattr__`, or build a new bound method, and `from mod import f` copies a name rather than linking to it. These pitfalls come from forgetting which layer you're standing on.

## Contents

| # | Pitfall | What you see | The fix |
|---|---------|--------------|---------|
| 31 | [Property errors fall through to `__getattr__`](#31-a-propertys-attributeerror-falls-through-to-__getattr__) | Error names the wrong attribute | Re-raise as another type |
| 32 | [`@lru_cache` on methods](#32-lru_cache-on-methods-leaks-instances) | Memory leak | `cached_property` |
| 33 | [`__eq__` removes `__hash__`](#33-defining-__eq__-removes-__hash__) | `unhashable type` | `@dataclass(frozen=True)` |
| 34 | [`__exit__` returning `True`](#34-__exit__-returning-true-swallows-exceptions) | Exceptions disappear | Return `None` |
| 35 | [Weak refs to bound methods](#35-weak-references-to-bound-methods-die-instantly) | Callbacks never fire | `weakref.WeakMethod` |
| 36 | [`mock.patch` in the wrong place](#36-mockpatch-in-the-wrong-place) | Test hits the real service | Patch where it's used |
| 37 | [A script imported twice](#37-a-script-can-be-imported-twice) | `isinstance` fails on your own class | Thin entry point |
| 68 | [Built-in subclasses skip overrides](#68-built-in-subclasses-bypass-overridden-methods) | `.get()` and `.update()` ignore hooks | `collections.UserDict` |
| 69 | [`__slots__` lost in subclasses](#69-subclassing-a-__slots__-class-silently-restores-__dict__) | Subclass silently regains `__dict__` | Declare `__slots__` on child |
| 70 | [`__len__` makes empty objects falsy](#70-defining-__len__-makes-empty-objects-falsy) | `if node:` skips valid leaf nodes | Test `is not None` / `__bool__` |

---

### 31. A Property's `AttributeError` Falls Through to `__getattr__`

`__getattr__` is called whenever normal attribute lookup raises `AttributeError`, and that includes an `AttributeError` raised *inside a property*. A typo in a property body is silently reported as the property itself being missing, often blamed on a completely different object.

```python
# The Trap
class SensorProxy:
    def __init__(self, device):
        self._device = device

    @property
    def temperature(self):
        return self._raw_reading * 0.1   # Bug: no such attribute.

    def __getattr__(self, name):
        return getattr(self._device, name)

SensorProxy(Device()).temperature
# AttributeError: 'Device' object has no attribute 'temperature'
```

The error points at `Device.temperature`, and `_raw_reading` appears nowhere in the message.

**Why:** Python can't tell "this attribute doesn't exist" from "this attribute's getter failed with `AttributeError`". Both trigger the `__getattr__` fallback.

**The fix:** Avoid `__getattr__` where you can. Where you can't, keep property bodies from leaking `AttributeError`: catch it and re-raise as a different type, such as `raise RuntimeError(...) from e`.

[Example](../examples/31_property_getattr_masking.py)

### 32. `@lru_cache` on Methods Leaks Instances

`functools.lru_cache` keys its cache on all arguments, and for a method that includes `self`. The cache lives on the class, so it holds a strong reference to every instance that ever called the method, and those instances are never freed.

```python
# The Trap
class Portfolio:
    @functools.lru_cache(maxsize=None)
    def value(self):
        return expensive_valuation(self.positions)
# Every Portfolio ever created stays in memory.
```

**The fix:** Use `functools.cached_property` for per-instance caching. It stores the result in the instance's `__dict__`, so it's freed with the instance. If you need arguments, cache in a module-level function keyed on plain values instead of `self`. Flake8-bugbear and ruff flag this as `B019`.

[Example](../examples/32_lru_cache_method_leak.py)

### 33. Defining `__eq__` Removes `__hash__`

When a class defines `__eq__` but not `__hash__`, Python sets `__hash__ = None`, so instances can no longer go in a set or be used as dict keys. A plain `@dataclass` does the same, because it generates `__eq__`.

```python
# The Trap
class Symbol:
    def __init__(self, ticker):
        self.ticker = ticker

    def __eq__(self, other):
        return self.ticker == other.ticker

{Symbol("AAPL")}   # TypeError: unhashable type: 'Symbol'
```

**Why:** Objects that are equal must have equal hashes. The inherited identity-based `__hash__` would break that rule, so Python removes it rather than let dicts and sets misbehave.

**The fix:** Define a `__hash__` from the same fields as `__eq__`, and don't mutate those fields afterwards. A `@dataclass(frozen=True)` generates both and enforces immutability.

[Example](../examples/33_eq_disables_hash.py)

### 34. `__exit__` Returning `True` Swallows Exceptions

If a context manager's `__exit__` returns a truthy value, Python treats the exception as handled and continues after the `with` block. That's easy to trigger by accident by returning the result of a helper.

```python
# The Trap
class Transaction:
    def __exit__(self, exc_type, exc, tb):
        return self.rollback() if exc_type else self.commit()
        # rollback() returns True on success... which also suppresses the error.

with Transaction():
    raise ValueError("invalid order")
print("carried on")   # Runs.
```

**The fix:** Return `None` (or `False`) from `__exit__` unless suppressing exceptions is the explicit purpose. Writing context managers with `@contextlib.contextmanager` avoids the trap entirely.

[Example](../examples/34_exit_swallows_exceptions.py)

### 35. Weak References to Bound Methods Die Instantly

Observer and event-bus code often stores callbacks as weak references so that listeners can be garbage-collected. But `obj.method` creates a new bound-method object on every access, and nothing else refers to it, so a `weakref.ref` to it is dead immediately, even though `obj` is still alive.

```python
# The Trap
listener = Listener()
callback = weakref.ref(listener.on_tick)
print(callback())    # None. The callback never fires.
```

**The fix:** Use `weakref.WeakMethod(listener.on_tick)`, which weakly references the instance and the function separately and rebuilds the bound method on demand. A `weakref.WeakSet` of listeners with a known method name also works.

[Example](../examples/35_weakref_bound_method.py)

### 36. `mock.patch` in the Wrong Place

`from prices import fetch` creates a new name `fetch` in the importing module, bound to the same function. Patching `prices.fetch` replaces the name in `prices` but not the copy in your module, so the test calls the real function.

```python
# report.py
from prices import fetch

def run():
    return fetch()

# test_report.py — The Trap
with mock.patch("prices.fetch", return_value="mocked"):
    report.run()   # Still calls the real prices.fetch.
```

**The fix:** Patch the name where it's *looked up*: `mock.patch("report.fetch")`. The unittest.mock docs have a whole section on this: [Where to patch](https://docs.python.org/3/library/unittest.mock.html#where-to-patch). Alternatively, `import prices` and call `prices.fetch()`, so there's only one name to patch.

[Example](../examples/36_mock_patch_location.py)

### 37. A Script Can Be Imported Twice

When you run `python app.py`, the file is loaded as the module `__main__`. If anything later does `import app`, Python doesn't find a module called `app`, so it loads the file *again*. You get two copies of every class, global and singleton, and objects from one copy fail `isinstance` checks against the other.

```python
# app.py
class Config: ...

if __name__ == "__main__":
    import app   # Or indirectly: a module that imports app.
    print(isinstance(Config(), app.Config))   # False
```

**The fix:** Keep the entry-point file thin. Put the real code in modules, and have the entry point import them and call `main()`. Running a package with `python -m package` (with a `__main__.py`) follows the same idea.

[Example](../examples/37_main_module_imported_twice.py)

### 68. Built-in Subclasses Bypass Overridden Methods

Subclassing `dict`, `list` or `set` and overriding `__getitem__` or `__setitem__` looks like normal object-oriented Python. `d[k]` calls your override, while `d.__init__()`, `d.get()`, `d.update()`, `d.setdefault()` and `{**d}` completely ignore it.

```python
# The Trap
class LowerKeyDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower())

d = LowerKeyDict(Accept="text/html")
d["X-Token"] = "secret"
d.update({"Cache-Control": "no-store"})
print(list(d.keys()))    # ['Accept', 'x-token', 'Cache-Control']
print(d.get("X-TOKEN"))  # None (d["X-TOKEN"] is 'secret'!)
```

**Why:** CPython's built-in types are written in C for speed, and their C methods access internal `PyDict` storage directly rather than dispatching back through Python's method table. C-level performance optimization leaks right through the inheritance model.

**The fix:** Subclass `collections.UserDict`, `collections.UserList`, or `collections.abc.MutableMapping`, whose methods are written in Python on top of `__getitem__` and `__setitem__`.

[Example](../examples/68_builtin_subclass_bypass.py)

### 69. Subclassing a `__slots__` Class Silently Restores `__dict__`

`__slots__` replaces per-instance `__dict__` storage with fixed C-struct slots, saving memory and catching misspelled attributes. But `__slots__` is not inherited in the way most developers expect: if a subclass omits `__slots__`, Python silently creates a `__dict__` and `__weakref__` on every subclass instance anyway.

```python
# The Trap
class Point:
    __slots__ = ("x", "y")

class LabeledPoint(Point):
    pass   # Forgot __slots__!

p = LabeledPoint()
p.typo_attr = 99   # Succeeds silently, stored in p.__dict__.
```

**Why:** Each class body independently controls whether its instances get a `__dict__` descriptor unless `__slots__` suppresses it on *that* class too.

**The fix:** Declare `__slots__ = ()` on subclasses that add no new attributes (or list only the *new* slot names—repeating parent slot names wastes space). With `@dataclass(slots=True)`, put `slots=True` on every subclass as well.

[Example](../examples/69_slots_inheritance_dict.py)

### 70. Defining `__len__` Makes Empty Objects Falsy

When `bool(obj)` (or `if obj:`) evaluates an instance that doesn't define `__bool__`, Python falls back to `len(obj) != 0`. Any domain object that defines `__len__`—a tree node counting its children, a batch wrapper, a response page—becomes falsy whenever its count happens to be zero, so `if obj:` conflates "empty" with `None`.

```python
# The Trap
class Node:
    def __init__(self, name, children=()):
        self.name = name
        self.children = list(children)

    def __len__(self):
        return len(self.children)

root = Node("root")
if root:
    process(root)   # Skipped! len(root) == 0 makes bool(root) False.
```

**In the wild:** `xml.etree.ElementTree.Element` hit this so often—`if elem:` evaluated to `False` for valid leaf tags like `<status>ok</status>` because an element's `len()` is its child-tag count—that Python added a multi-release warning urging callers to write `if elem is not None:` instead.

**The fix:** Always check `if obj is not None:` when testing for optional objects (Ruff's `SIM108` / explicit `None` checks help), and define `def __bool__(self): return True` on entity classes where zero length doesn't mean "absent".

[Example](../examples/70_bool_falls_back_to_len.py)
