"""A weak reference to a bound method dies immediately."""

import weakref


class Listener:
    def on_tick(self):
        return "tick"


listener = Listener()

# The trap: each attribute access builds a new, temporary bound method.
assert listener.on_tick is not listener.on_tick
callback = weakref.ref(listener.on_tick)
print(callback())  # None (the listener is alive, but the callback is gone)
assert callback() is None

# The fix: WeakMethod tracks the instance and the function separately.
callback = weakref.WeakMethod(listener.on_tick)
assert callback()() == "tick"
del listener
assert callback() is None  # Now it dies with the instance, as intended.
