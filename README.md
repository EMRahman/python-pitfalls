# Python Gotchas: Discovering Shallow Interfaces the Hard Way

Python’s syntax prioritizes readability, which often creates "shallow interfaces" that hide complex, leaky internal states—a concept discussed by John Ousterhout in *A Philosophy of Software Design*. When language mechanics do not match the readable syntax, developers are forced to hold complex mental models of the interpreter's state, usually discovering the truth through runtime bugs.

Here is a log of the most common design traps developers learn the hard way.

## 1. Iterator Exhaustion (The Observer Effect)
Functions like `reversed()`, `zip()`, and `map()` return single-use iterators rather than persistent data structures. Passing an iterator to `list()` or inspecting it via `print(list(...))` consumes the iterator entirely.

Subsequent calls to that iterator encounter an empty sequence with no warnings. In this scenario, simply inspecting your data actively destroys it.

```python
# The Trap
my_string = "hello"
reversed_iter = reversed(my_string)

print(list(reversed_iter)) # Output: ['o', 'l', 'l', 'e', 'h']
print(list(reversed_iter)) # Output: [] (Silently empty!)
```

## 2. Mutable Default Arguments
Defining a function with a default mutable argument (like a list or dictionary) binds the default object to the function at definition time, not at execution time. Every subsequent call that omits the argument modifies the exact same list in memory, causing data to silently bleed across independent function calls.

```python
# The Trap
def add_item(item, target=[]):
    target.append(item)
    return target

print(add_item("Apple"))  # Output: ['Apple']
print(add_item("Banana")) # Output: ['Apple', 'Banana'] (Apple leaked!)
```

## 3. Late Binding in Closures
Creating functions inside a loop does not capture the value of the loop variable at that specific iteration. Python closures bind to the variable reference, not its value. When the functions are executed later, they all look up the current value of the variable, which remains at the final loop state.

```python
# The Trap
funcs = [lambda: i for i in range(3)]

# You expect 0, 1, 2. But you get:
for f in funcs:
    print(f()) # Output: 2, 2, 2
```

## 4. List Modification During Iteration
Python manages `for` loops over lists using a hidden, forward-moving index counter. If you delete an item during the loop, the remaining elements shift left to fill the gap, but the internal counter still steps forward. This results in the loop silently skipping the item immediately following the deleted one.

```python
# The Trap
numbers = [1, 2, 3, 4]
for num in numbers:
    if num == 2:
        numbers.remove(num)

print(numbers) # Output: [1, 3, 4] 
# (But wait, the loop never actually inspected '3'!)
```

## 5. Integer Caching and Identity
Python optimizes memory by pre-allocating a singleton pool of integers from -5 to 256. Variables assigned these values point to the exact same memory address. Once you exceed this arbitrary bound, Python allocates new memory blocks, breaking identity checks unpredictably.

```python
# The Trap
a = 256
b = 256
print(a is b) # Output: True

c = 257
d = 257
print(c is d) # Output: False (Identity breaks!)
```

## 6. Scope Leaking in Loops
Unlike C-family languages that strictly enforce block-level scoping, variables initialized inside a Python `for` or `while` loop leak into the enclosing scope. A loop variable continues to exist and hold its final value after the loop terminates, frequently causing silent overrides of identically named variables.

```python
# The Trap
i = "Safe string"
for i in range(5):
    pass

print(i) # Output: 4 (The original string was silently overwritten)
```

## 7. The Tuple `+=` Anomaly
Tuples are immutable, but they can contain mutable objects like lists. If you attempt to use the `+=` operator on a mutable object inside a tuple, Python raises a `TypeError` because the tuple itself cannot be reassigned. However, the underlying list modification executes *before* the exception is thrown, meaning the data successfully mutates even though the operation formally crashed.

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
