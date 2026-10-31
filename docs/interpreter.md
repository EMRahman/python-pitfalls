# Interpreter Pitfalls: Bytecode, Scoping and CPython Internals

[← Back to all pitfalls](../README.md)

Some Python behavior only makes sense once you know what the compiler and CPython do underneath: which statements survive optimization, how scopes are decided at compile time, and how memory is reused. Integer caching ([#13](../README.md#13-integer-caching-and-identity)) and `UnboundLocalError` ([#12](../README.md#12-unboundlocalerror-from-a-line-that-never-runs)) belong to this family too.

## Contents

| # | Pitfall | What you see | The fix |
|---|---------|--------------|---------|
| 38 | [`python -O` deletes `assert`](#38-python--o-deletes-your-assert-checks) | Validation vanishes in production | Raise explicitly |
| 39 | [Class-body comprehensions](#39-class-body-comprehensions-cant-see-class-variables) | `NameError`, or the wrong global | Use a plain loop |
| 40 | [Writing to `locals()`](#40-writing-to-locals-does-nothing) | Assignment ignored | Use an explicit dict |
| 41 | [`id()` values get reused](#41-id-values-get-reused) | Stale cache hits | Key on the value |
| 42 | [4300-digit `int`/`str` limit](#42-strint-fails-above-4300-digits) | `ValueError` on big numbers | `sys.set_int_max_str_digits()` |
| 71 | [Deferred annotations vs runtime checks](#71-deferred-annotations-break-naive-runtime-introspection) | `__annotations__` holds strings, not types | `typing.get_type_hints()` |

---

### 38. `python -O` Deletes Your `assert` Checks

Running Python with `-O` (or `PYTHONOPTIMIZE=1`) removes every `assert` statement at compile time. Any validation written as an `assert` silently disappears, typically in the production container that sets the flag.

```python
# The Trap
def withdraw(balance, amount):
    assert amount <= balance, "insufficient funds"
    return balance - amount

withdraw(100, 500)   # AssertionError normally; returns -400 under python -O.
```

**The fix:** Use `assert` only for internal invariants that indicate a programming error. Validate inputs with an explicit `if ...: raise ValueError(...)`. Ruff's `S101` flags `assert` outside tests.

[Example](../examples/38_assert_stripped_by_O.py)

### 39. Class-Body Comprehensions Can't See Class Variables

A class body is a scope, but it's not visible to functions nested inside it, and a comprehension behaves like a nested function. Inside the comprehension, a class variable is invisible: you get a `NameError`, or worse, a module-level variable with the same name.

```python
# The Trap
rate = 0.0

class Fees:
    rate = 0.01
    tiers = [rate * n for n in (1, 2, 3)]

print(Fees.tiers)   # [0.0, 0.0, 0.0] (it used the global rate)
```

**Why:** Name resolution skips class scopes for nested code. That's why methods must write `self.rate` instead of `rate`. Python 3.12 inlined comprehensions for speed ([PEP 709](https://peps.python.org/pep-0709/)) but deliberately kept this behavior. The one exception is the *first* iterable (`(1, 2, 3)` above), which is evaluated in the class scope.

**The fix:** Build the value with a plain `for` loop in the class body, or compute it at module level and assign it.

[Example](../examples/39_class_body_comprehension_scope.py)

### 40. Writing to `locals()` Does Nothing

Inside a function, `locals()` returns a dict *snapshot* of the local variables. Writing to it doesn't change the variables, and neither does `exec("x = ...")`.

```python
# The Trap
def configure():
    debug = False
    locals()["debug"] = True
    exec("debug = True")
    return debug

configure()   # False
```

**Why:** The compiler stores function locals in fixed slots in the frame, not in a dict. Python 3.13 ([PEP 667](https://peps.python.org/pep-0667/)) made the snapshot behavior official. Module-level and class-level `locals()` *are* real dicts, which is why this seems to work in the REPL.

**The fix:** When names are dynamic, use an explicit dict, and pass it to `exec(code, globals_dict, locals_dict)` if you need `exec`.

[Example](../examples/40_locals_writes_ignored.py)

### 41. `id()` Values Get Reused

`id(obj)` is unique only *while the object is alive*. In CPython it's the object's memory address, and freed memory is reused right away, so a new object can get the same `id` as one that just died. `id([]) == id([])` is `True`.

```python
# The Trap
cache = {}

def describe(obj):
    key = id(obj)
    if key not in cache:
        cache[key] = repr(obj)
    return cache[key]

describe([1, 2, 3])
describe([4, 5, 6])   # '[1, 2, 3]' (a stale entry for a different list)
```

**The fix:** Key caches on the value itself when it's hashable. When you must key on identity, keep the object alive (store it alongside the result) or use a `weakref.WeakKeyDictionary`, which drops entries when objects die.

[Example](../examples/41_id_reuse.py)

### 42. `str(int)` Fails Above 4300 Digits

Python integers have unlimited size, but converting between `int` and decimal `str` is capped at 4,300 digits. Beyond that, `str()`, `int()`, `print()` and `json.loads()` raise `ValueError`.

```python
# The Trap
big = 10 ** 5000          # Arithmetic is fine.
str(big)                  # ValueError: Exceeds the limit (4300 digits) for integer string conversion
json.loads("9" * 5000)    # ValueError too.
```

**Why:** Decimal conversion is quadratic time, so a few megabytes of digits in a JSON payload could tie up a CPU for minutes. The limit was added as a security fix ([CVE-2020-10735](https://docs.python.org/3/library/stdtypes.html#int-max-str-digits)) in Python 3.11 and backported to 3.10.7, 3.9.14, 3.8.14 and 3.7.14, so it surprised code that had worked for years.

**The fix:** Use `sys.set_int_max_str_digits(n)` (or `PYTHONINTMAXSTRDIGITS`), ideally only around code that handles trusted input. Hex, octal and binary conversions are unaffected.

[Example](../examples/42_int_str_digit_limit.py)

### 71. Deferred Annotations Break Naive Runtime Introspection

Adding `from __future__ import annotations` ([PEP 563](https://peps.python.org/pep-0563/)) stops Python from evaluating type hints at definition time and stores their source text as strings instead. Any decorator, CLI builder or validator that reads `fn.__annotations__` expecting real classes breaks at runtime, and `typing.get_type_hints()` fails with `NameError` if an annotation references a class defined inside a function.

```python
# The Trap
from __future__ import annotations

def parse_port(port: int) -> int:
    return port

parse_port.__annotations__["port"]              # 'int' (a str, not <class 'int'>)
isinstance(8080, parse_port.__annotations__["port"])  # TypeError!
```

**Why:** Static type checkers wanted forward references without runtime import cost, while runtime frameworks (FastAPI, Pydantic, `dataclasses`, dependency injectors) treat annotations as executable metadata. Python 3.14 introduced lazy annotation functions via `annotationlib` ([PEP 649](https://peps.python.org/pep-0649/)) to replace stringification when `__future__` is *not* imported, meaning libraries now encounter eager types, PEP 563 strings, and PEP 649 evaluators side by side.

**The fix:** Never read `__annotations__` directly for types; call `typing.get_type_hints(fn)` (or `annotationlib.get_annotations()` on 3.14+), and keep runtime-inspected types at module scope where `get_type_hints()` can resolve them (Ruff's `TC001`–`TC003` flag imports moved behind `if TYPE_CHECKING:` that runtime consumers still need).

[Example](../examples/71_stringified_annotations.py)
