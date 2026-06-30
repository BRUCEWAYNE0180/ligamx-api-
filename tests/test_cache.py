import time

from app.cache import cached, clear_cache


def test_cache_devuelve_valor_cacheado():
    clear_cache()
    calls = {"n": 0}

    @cached(60)
    def f(x):
        calls["n"] += 1
        return x * 2

    assert f(3) == 6
    assert f(3) == 6  # segunda llamada desde cache
    assert calls["n"] == 1
    # argumento distinto = otra entrada
    assert f(4) == 8
    assert calls["n"] == 2


def test_cache_expira():
    clear_cache()
    calls = {"n": 0}

    @cached(1)
    def f():
        calls["n"] += 1
        return calls["n"]

    a = f()
    time.sleep(1.2)
    b = f()
    assert calls["n"] == 2
    assert b != a
