"""An AttributeError inside a property makes Python fall back to __getattr__."""


class Device:
    pass


# The trap
class SensorProxy:
    def __init__(self, device):
        self._device = device

    @property
    def temperature(self):
        return self._raw_reading * 0.1  # Bug: _raw_reading doesn't exist.

    def __getattr__(self, name):
        return getattr(self._device, name)  # Delegate unknown attributes.


try:
    SensorProxy(Device()).temperature
except AttributeError as e:
    message = str(e)

print(message)  # 'Device' object has no attribute 'temperature'
assert "temperature" in message
assert "_raw_reading" not in message  # The real bug is nowhere in the error.


# The fix: don't let AttributeError escape a property when __getattr__ exists.
class SensorProxyFixed(SensorProxy):
    @property
    def temperature(self):
        try:
            return self._raw_reading * 0.1
        except AttributeError as e:
            raise RuntimeError("failed to compute temperature") from e


try:
    SensorProxyFixed(Device()).temperature
except RuntimeError as e:
    assert "_raw_reading" in str(e.__cause__)
