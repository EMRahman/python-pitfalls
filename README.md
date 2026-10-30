# Python Pitfalls: Discovering Shallow Interfaces the Hard Way

[![Verify examples](https://github.com/EMRahman/python-pitfalls/actions/workflows/verify.yml/badge.svg)](https://github.com/EMRahman/python-pitfalls/actions/workflows/verify.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A catalog of Python gotchas, traps and surprising behaviors, each with a minimal reproduction, an explanation of *why* it happens, and the fix.

Python's syntax prioritizes readability, but a readable surface can hide complex, leaky internal state. John Ousterhout's *A Philosophy of Software Design* calls the worst symptom of complexity *unknown unknowns*: behavior you cannot predict from the interface in front of you. When the language's mechanics don't match its readable syntax, developers are forced to hold a mental model of the interpreter's state, and usually discover the truth through runtime bugs.

Here is a log of the design traps developers learn the hard way.

> Every snippet below has a runnable, self-checking twin in [`examples/`](examples/). CI runs them on CPython 3.10 to 3.14, so the outputs shown here are verified, not remembered.

## Contents

| # | Pitfall | What you see | The fix |
|---|---------|--------------|---------|
| | **Iterators & laziness** | | |
| 1 | [Iterator exhaustion](#1-iterator-exhaustion-the-observer-effect) | Second `list(it)` is `[]` | Materialize once with `list()` |
| 2 | [`zip()` drops data](#2-zip-silently-truncates-and-swallows-an-element) | Missing rows, a lost element | `zip(..., strict=True)` |
| 3 | [Generators delay errors](#3-generators-delay-their-errors) | Exception far from the bug | Validate in a normal function |
| | **Mutability & aliasing** | | |
| 4 | [Mutable default arguments](#4-mutable-default-arguments) | Data bleeds across calls | `None` sentinel |
| 5 | [List multiplication aliasing](#5-list-multiplication-aliasing) | Edit one row, all rows change | List comprehension |
| 6 | [Shared class attributes](#6-shared-mutable-class-attributes) | Instances share state | Assign in `__init__` |
| 7 | [Modifying a list while iterating](#7-modifying-a-list-during-iteration) | Elements skipped | Build a new list |
| 8 | [The tuple `+=` anomaly](#8-the-tuple--anomaly) | Crash *and* mutation | Call `.extend()` |
| | **Scope & binding** | | |
| 9 | [Late binding in closures](#9-late-binding-in-closures) | Every lambda returns `2` | `lambda i=i: ...` |
| 10 | [Loop variables leak](#10-loop-variables-leak) | Outer variable overwritten | Distinct names |
| 11 | [`except ... as e` deletes `e`](#11-except--as-e-deletes-e) | `NameError` after the block | Copy to another name |
| 12 | [`UnboundLocalError`](#12-unboundlocalerror-from-a-line-that-never-runs) | Error on a read of a global | Pass arguments in |
| | **Identity & equality** | | |
| 13 | [Integer caching and `is`](#13-integer-caching-and-identity) | `is` flips at 257 | Use `==` |
| 14 | [`True` is `1`](#14-true-is-1-and-they-collide-as-dict-keys) | Dict keys collapse | Put the type in the key |
| | **Syntax traps** | | |
| 15 | [Implicit string concatenation](#15-implicit-string-concatenation) | Two items become one | Trailing commas + linter |
| 16 | [Trailing comma makes a tuple](#16-a-trailing-comma-makes-a-tuple) | `(30,)` instead of `30` | Delete the comma |
| | **Standard library surprises** | | |
| 17 | [`strip()` takes a character set](#17-strip-takes-a-set-of-characters-not-a-substring) | `"report.txt"` becomes `"repor"` | `removesuffix()` |
| 18 | [Banker's rounding](#18-round-uses-bankers-rounding) | `round(2.5) == 2` | `Decimal` + `ROUND_HALF_UP` |
| 19 | [`return` in `finally`](#19-return-in-finally-swallows-exceptions) | Exception vanishes | Never return from `finally` |

---

## Iterators & laziness

### 1. Iterator Exhaustion (The Observer Effect)

Functions like `reversed()`, `zip()`, `map()` and `filter()`, generator expressions, and file objects return single-use iterators rather than persistent data structures. Passing an iterator to `list()`, or inspecting it with `print(list(...))`, consumes it entirely.

Subsequent reads find an empty sequence, with no warning. Simply inspecting your data destroys it.

```python
# The Trap
my_string = "hello"
reversed_iter = reversed(my_string)

print(list(reversed_iter)) # Output: ['o', 'l', 'l', 'e', 'h']
print(list(reversed_iter)) # Output: [] (Silently empty!)
```

It gets worse. A membership test consumes everything up to the match, and an exhausted iterator is still truthy, so `if it:` can't tell you it's empty:

```python
squares = (n * n for n in range(6))
print(9 in squares)   # Output: True
print(list(squares))  # Output: [16, 25] (0, 1, 4 and 9 are gone)

empty = (n for n in [])
print(bool(empty))    # Output: True
```

**Why:** An iterator is a cursor, not a container. It only knows how to produce the *next* item, and once it raises `StopIteration` it stays exhausted.

**The fix:** If you need the data more than once, materialize it once with `list(...)` or `tuple(...)` and reuse that. For large or infinite streams, use `itertools.tee()` or restructure the code to make one pass.

[Example](examples/01_iterator_exhaustion.py)

### 2. `zip()` Silently Truncates (and Swallows an Element)

`zip()` stops at the shortest input without complaint, so mismatched data simply disappears. When one input is an iterator, `zip()` also pulls one extra item from it before noticing that a later input is empty, and that item is thrown away.

```python
# The Trap
names = ["Ada", "Grace", "Linus"]
scores = [95, 88]
print(list(zip(names, scores))) # Output: [('Ada', 95), ('Grace', 88)] (Linus vanished)

numbers = iter([1, 2, 3, 4])
print(list(zip(numbers, ["a", "b"]))) # Output: [(1, 'a'), (2, 'b')]
print(list(numbers))                  # Output: [4] (Where did 3 go?)
```

**Why:** On each step `zip()` calls `next()` on its inputs left to right. On the third step it takes `3` from `numbers`, then finds the list exhausted, and has nowhere to put the `3`.

**The fix:** Pass `strict=True` (Python 3.10+) to raise `ValueError` on a length mismatch. Use `itertools.zip_longest()` if you want to pad instead. If you must zip an iterator with something shorter, put the shorter input first.

[Example](examples/02_zip_truncation.py)

### 3. Generators Delay Their Errors

Calling a generator function doesn't run any of its body, not even the argument checks at the top. The error surfaces later, wherever the generator is first iterated, which may be in a different module.

```python
# The Trap
def chunks(data, size):
    if size <= 0:
        raise ValueError("size must be positive")
    for i in range(0, len(data), size):
        yield data[i : i + size]

batches = chunks([1, 2, 3], 0)  # No error here...
list(batches)                   # ...ValueError is raised here instead.
```

**Why:** A `yield` anywhere in a function body turns the whole function into a generator factory. Calling it only creates a paused generator object.

**The fix:** Validate in a regular function, then return the generator:

```python
def chunks(data, size):
    if size <= 0:
        raise ValueError("size must be positive")  # Raised at the call site
    return _chunks(data, size)

def _chunks(data, size):
    for i in range(0, len(data), size):
        yield data[i : i + size]
```

[Example](examples/03_lazy_generator_errors.py)

---

## Mutability & aliasing

### 4. Mutable Default Arguments

A default value is evaluated once, when the `def` statement runs, not on every call. With a mutable default like a list or dict, every call that omits the argument modifies the same object, so data silently bleeds across independent calls.

```python
# The Trap
def add_item(item, target=[]):
    target.append(item)
    return target

print(add_item("Apple"))  # Output: ['Apple']
print(add_item("Banana")) # Output: ['Apple', 'Banana'] (Apple leaked!)
print(add_item.__defaults__) # Output: (['Apple', 'Banana'],)
```

The same rule bites with non-mutable defaults that you expected to be fresh, such as `def log(msg, when=datetime.now())`, which stamps every message with the time the module was imported.

**The fix:** Use `None` as a sentinel and create the object inside the function.

```python
def add_item(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```

[Example](examples/04_mutable_default_arguments.py)

### 5. List Multiplication Aliasing

`[[0] * 3] * 3` looks like a 3x3 grid, but it's one inner list referenced three times. Changing one "row" changes them all.

```python
# The Trap
grid = [[0] * 3] * 3
grid[0][0] = 1
print(grid) # Output: [[1, 0, 0], [1, 0, 0], [1, 0, 0]]
```

`dict.fromkeys(keys, [])` has the same problem: every key shares one list.

**Why:** Sequence multiplication copies *references*. That's harmless for immutable items like `0`, but for a list it means three pointers to the same object.

**The fix:** Use a comprehension, which evaluates the inner expression once per row: `[[0] * 3 for _ in range(3)]`, or `{key: [] for key in keys}`.

[Example](examples/05_list_multiplication_aliasing.py)

### 6. Shared Mutable Class Attributes

An attribute assigned in the class body belongs to the class, not to each instance. If it's mutable, every instance mutates the same object.

```python
# The Trap
class Cart:
    items = []

    def add(self, item):
        self.items.append(item)

alice, bob = Cart(), Cart()
alice.add("apple")
print(bob.items) # Output: ['apple'] (Bob never added anything!)
```

**Why:** `self.items` finds no instance attribute, falls back to the class attribute, and `.append()` mutates it in place. (Assignment such as `self.items = [...]` *would* create an instance attribute, which is why this trap is easy to miss.)

**The fix:** Create per-instance state in `__init__`, or use a dataclass with `field(default_factory=list)`. Dataclasses refuse a bare `items: list = []` default for exactly this reason.

[Example](examples/06_shared_class_attributes.py)

### 7. Modifying a List During Iteration

A `for` loop over a list tracks its position with a hidden index that moves forward on every step. Deleting an item shifts the remaining elements left to fill the gap, but the index still moves forward, so the loop silently skips the element after each deletion.

```python
# The Trap
numbers = [2, 4, 6, 8]
for n in numbers:
    if n % 2 == 0:
        numbers.remove(n)

print(numbers) # Output: [4, 8]
# ("Remove every even number" left half of them behind!)
```

Dicts and sets at least fail loudly with `RuntimeError: dictionary changed size during iteration`. Lists give you no such warning.

**The fix:** Build a new list, `numbers = [n for n in numbers if n % 2 != 0]`, or loop over a copy with `for n in numbers[:]`.

[Example](examples/07_modifying_list_during_iteration.py)

### 8. The Tuple `+=` Anomaly

Tuples are immutable, but they can contain mutable objects like lists. Using `+=` on a list inside a tuple raises a `TypeError` because the tuple slot cannot be reassigned. However, the list is modified *before* the exception is raised, so the data changes even though the operation formally failed.

```python
# The Trap
t = (1, 2, [3, 4])

try:
    t[2] += [5, 6]
except TypeError as e:
    print(f"Error caught: {e}")

# The list mutated anyway despite the crash!
print(t) # Output: (1, 2, [3, 4, 5, 6])
```

**Why:** `t[2] += x` runs as two steps: `tmp = t[2].__iadd__(x)` (which extends the list in place and succeeds), then `t[2] = tmp` (which fails).

**The fix:** Mutate the inner object directly with `t[2].extend([5, 6])`. There's no reassignment, so there's no error.

[Example](examples/08_tuple_augmented_assignment.py)

---

## Scope & binding

### 9. Late Binding in Closures

Functions created in a loop don't capture the loop variable's value at that iteration. Python closures bind to the *variable*, not its value, so when they run later they all read its current value, which is whatever the loop left behind.

```python
# The Trap
funcs = [lambda: i for i in range(3)]

# You expect 0, 1, 2. But you get:
for f in funcs:
    print(f()) # Output: 2, 2, 2
```

**The fix:** Bind the value at definition time with a default argument, `lambda i=i: i`, or use `functools.partial(func, i)`.

[Example](examples/09_late_binding_closures.py)

### 10. Loop Variables Leak

Unlike C-family languages, Python has no block scope. A variable assigned by a `for` loop lives in the enclosing function or module and keeps its final value after the loop ends, silently overwriting any earlier variable with the same name.

```python
# The Trap
i = "Safe string"
for i in range(5):
    pass

print(i) # Output: 4 (The original string was silently overwritten)
```

The reverse also bites: if the loop body never runs, the name keeps its *old* value, so code after the loop can act on a stale item from a previous loop. List, dict and set comprehensions have their own scope in Python 3 and do **not** leak.

**The fix:** Use distinct names for loop variables, and keep loops inside small functions so names can't collide with module-level state.

[Example](examples/10_loop_variable_leak.py)

### 11. `except ... as e` Deletes `e`

Loop variables outlive their loop (see #10), but an exception name does the opposite. When the `except` block ends, Python *deletes* the name, including any unrelated variable that happened to have the same name before the `try`.

```python
# The Trap
e = "important data"
try:
    1 / 0
except ZeroDivisionError as e:
    pass

print(e) # NameError: name 'e' is not defined
```

**Why:** The exception holds a traceback, which references the current stack frame, which references the exception. Python runs `del e` at the end of the block to break that cycle.

**The fix:** If you need the exception after the block, copy it to a different name inside the block: `error = e`.

[Example](examples/11_exception_variable_deleted.py)

### 12. `UnboundLocalError` From a Line That Never Runs

If a function assigns to a name *anywhere* in its body, that name is local for the *whole* body. Reading it before the assignment raises `UnboundLocalError`, even when the assignment is unreachable.

```python
# The Trap
total = 10

def report():
    print(total)    # UnboundLocalError is raised HERE...
    if False:
        total = 0   # ...because of this line, which never even runs.

report()
```

The everyday version is `counter += 1` inside a function, with `counter` defined at module level.

**Why:** Scope is decided when the function is compiled, not as it runs. The compiler sees an assignment to `total`, marks it local, and the global is never consulted.

**The fix:** Pass the value in as an argument and return the result. Use `global` or `nonlocal` only when you really mean to rebind the outer variable.

[Example](examples/12_unbound_local_error.py)

---

## Identity & equality

### 13. Integer Caching and Identity

CPython pre-allocates a single object for each integer from -5 to 256, so every `256` is the same object. Above that range, each new integer is usually a new object, and `is` starts returning `False` for equal values.

```python
# The Trap
a = int("256")
b = int("256")
print(a is b) # Output: True

c = int("257")
d = int("257")
print(c is d) # Output: False (Identity breaks!)
```

It's even less predictable with literals. The compiler merges identical constants that are compiled together, so this prints `True` in a script but `False` when typed line by line into the REPL:

```python
x = 257
y = 257
print(x is y) # Output: True in a .py file, False in the REPL
```

The same code giving different answers depending on *how you run it* is about as leaky as an abstraction gets. Strings have a similar mechanism, called interning.

**The fix:** Use `==` to compare values. Reserve `is` for singletons such as `None`, `True`, `False` and sentinel objects. Since Python 3.8, `x is 257` with a literal triggers a `SyntaxWarning` for this reason.

[Example](examples/13_integer_caching.py)

### 14. `True` Is `1` (and They Collide as Dict Keys)

`bool` is a subclass of `int`. `True == 1`, `False == 0`, and their hashes match too, so as dict keys or set members they are the *same key*. So is `1.0`.

```python
# The Trap
d = {1: "one", True: "yes", 1.0: "float one"}
print(d) # Output: {1: 'float one'} (Three keys collapsed into one)

print({0, False})           # Output: {0}
print(True + True)          # Output: 2
```

Note the result keeps the *first* key (`1`) but the *last* value. This matters when you mix flags and counts in one mapping, `Counter`, or JSON-like structure.

**The fix:** Don't mix `bool` and numeric keys. If the type genuinely matters, include it in the key: `(type(k), k)`.

[Example](examples/14_bool_is_int.py)

---

## Syntax traps

### 15. Implicit String Concatenation

Adjacent string literals are joined at compile time. That's handy for long strings, but in a list it means one missing comma silently merges two items, and the list is one element short.

```python
# The Trap
fruits = [
    "apple",
    "banana"   # <- missing comma
    "cherry",
]
print(fruits) # Output: ['apple', 'bananacherry']
```

**The fix:** Put a trailing comma on every line of a multi-line collection, and enable pylint's `implicit-str-concat` check with `check-str-concat-over-line-jumps=yes`.

[Example](examples/15_implicit_string_concatenation.py)

### 16. A Trailing Comma Makes a Tuple

The comma creates a tuple, not the parentheses. A stray comma at the end of an assignment, often left over from copying a dict entry or function argument, silently changes the type.

```python
# The Trap
timeout = 30,
print(timeout)     # Output: (30,)
print(timeout + 5) # TypeError: can only concatenate tuple (not "int") to tuple
```

Meanwhile `(30)` is just `30`. You need `(30,)` for a one-element tuple.

**The fix:** Delete the comma. Ruff's `COM818` (trailing comma on bare tuple) catches this automatically.

[Example](examples/16_trailing_comma_tuple.py)

---

## Standard library surprises

### 17. `strip()` Takes a Set of Characters, Not a Substring

`str.strip()`, `lstrip()` and `rstrip()` treat their argument as a set of characters to remove, not as a prefix or suffix. They keep stripping until they hit a character outside that set.

```python
# The Trap
print("report.txt".rstrip(".txt"))            # Output: 'repor'
print("https://python.org".lstrip("https://")) # Output: 'ython.org'
```

**The fix:** Use `removesuffix()` and `removeprefix()` (Python 3.9+), which remove an exact substring once.

[Example](examples/17_strip_character_set.py)

### 18. `round()` Uses Banker's Rounding

`round()` rounds exact halves to the nearest *even* number, not always up, so `round(2.5)` is `2`. On top of that, many decimal values can't be stored exactly as floats, so a "half" may not really be a half.

```python
# The Trap
print(round(0.5), round(1.5), round(2.5)) # Output: 0 2 2
print(round(2.675, 2))                     # Output: 2.67 (2.675 is stored as 2.67499999...)
```

**Why:** Round-half-to-even (IEEE 754's default) avoids the upward bias of always rounding halves up, which matters when summing many rounded values.

**The fix:** For money and other human-facing decimals, use `decimal.Decimal` with an explicit mode: `Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` gives `Decimal('2.68')`.

[Example](examples/18_bankers_rounding.py)

### 19. `return` in `finally` Swallows Exceptions

A `return`, `break` or `continue` inside a `finally` block overrides whatever was in flight, including an exception. The error disappears without a trace.

```python
# The Trap
def save():
    try:
        raise OSError("disk full")
    finally:
        return "saved"  # The OSError vanishes.

print(save()) # Output: saved
```

**Why:** `finally` always runs last, and a `return` there replaces the pending outcome, whether that was a return value or an exception.

**The fix:** Keep `finally` for cleanup only and put the `return` after the block. Python 3.14 now emits a `SyntaxWarning` for this pattern ([PEP 765](https://peps.python.org/pep-0765/)).

[Example](examples/19_return_in_finally.py)

---

## Running the examples

Each file in [`examples/`](examples/) prints the surprising output and `assert`s it, so a script that runs without error confirms the behavior described above.

```sh
for f in examples/*.py; do python "$f" || echo "FAILED: $f"; done
```

## Contributing

Been bitten by something that isn't here? See [CONTRIBUTING.md](CONTRIBUTING.md). Good pitfalls are surprising, reproducible in a few lines, and have a clear fix.

## License

[MIT](LICENSE)
