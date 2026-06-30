"""Cache en memoria con TTL para endpoints "en vivo".

Los endpoints que consultan fuentes externas (ESPN, 365Scores, TheSportsDB)
golpean la red en cada request. Eso es lento y arriesga rate-limits/baneos.
Este cache guarda la respuesta por unos segundos para responder al instante
y reducir las llamadas externas.

Es un cache simple por proceso (suficiente para 1 worker). Con varios workers
cada uno tiene el suyo, lo cual es aceptable para datos de baja criticidad.
"""
import time
import threading
import functools
from typing import Callable

_store = {}
_lock = threading.Lock()


def _make_key(fn, args, kwargs):
    return (fn.__module__, fn.__qualname__, args, tuple(sorted(kwargs.items())))


def cached(ttl: int) -> Callable:
    """Decorador: cachea el resultado de la funcion durante `ttl` segundos.
    Los argumentos deben ser hashables (str/int/None, como los query params)."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = _make_key(fn, args, kwargs)
            now = time.time()
            with _lock:
                entry = _store.get(key)
                if entry and entry[0] > now:
                    return entry[1]
            value = fn(*args, **kwargs)
            with _lock:
                _store[key] = (now + ttl, value)
            return value
        wrapper.__wrapped__ = fn
        return wrapper
    return decorator


def clear_cache():
    """Vacia todo el cache (util en tests)."""
    with _lock:
        _store.clear()


def cache_stats():
    """Numero de entradas vivas/expiradas (para diagnostico)."""
    now = time.time()
    with _lock:
        live = sum(1 for exp, _ in _store.values() if exp > now)
        return {"entries": len(_store), "live": live, "expired": len(_store) - live}
