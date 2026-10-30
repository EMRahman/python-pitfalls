"""A context manager whose __exit__ returns a truthy value swallows exceptions."""


# The trap
class Transaction:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return self.rollback() if exc_type else self.commit()

    def rollback(self):
        return True  # "Rollback succeeded"... which also means "suppress the error".

    def commit(self):
        return True


with Transaction():
    raise ValueError("invalid order")

print("execution continued as if nothing happened")


# The fix: return None (or False) unless you deliberately mean to suppress.
class TransactionFixed(Transaction):
    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        return None


try:
    with TransactionFixed():
        raise ValueError("invalid order")
except ValueError:
    pass
else:
    raise AssertionError("expected ValueError")
