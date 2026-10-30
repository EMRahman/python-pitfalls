"""Writing to locals() or exec-ing an assignment doesn't change a function's variables."""


# The trap
def configure():
    debug = False
    locals()["debug"] = True
    return debug


def configure_exec():
    debug = False
    exec("debug = True")
    return debug


print(configure(), configure_exec())  # False False
assert configure() is False
assert configure_exec() is False


# The fix: use an explicit dict when names are dynamic.
def configure_fixed():
    settings = {"debug": False}
    exec("debug = True", {}, settings)
    return settings["debug"]


assert configure_fixed() is True
