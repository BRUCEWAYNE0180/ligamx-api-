#!/usr/bin/env python
"""Chequeo rapido de la API en produccion (Liga MX API).

Le pega a los endpoints clave y reporta OK/FALLO en segundos. Ideal para correr
tras un deploy o despues de cada jornada, y confirmar que la API responde y que
los datos estan frescos.

Uso:
    python scripts/healthcheck.py                       # usa la URL por defecto
    python scripts/healthcheck.py https://mi-api.com    # otra URL
    python scripts/healthcheck.py --max-age-hours 12    # umbral de frescura

Sale con codigo != 0 si algun chequeo CRITICO falla (util para automatizar).
"""
import argparse
import sys
import time

import requests

DEFAULT_URL = "https://ligamx-api.onrender.com"

# (ruta, es_critico, validador_opcional(json)->str|None con mensaje de fallo)
CHECKS = [
    ("/health", True, None),
    ("/health/ready", True, lambda d: None if d.get("ready") and d.get("checks", {}).get("database") == "ok"
     else "database no OK"),
    ("/version", True, None),
    ("/standings", True, lambda d: None if isinstance(d, list) else "no es lista"),
    ("/seasons", True, None),
    ("/teams", True, lambda d: None if isinstance(d, list) and len(d) >= 1 else "sin equipos"),
    ("/players?limit=1", True, None),
    ("/dashboard", True, None),
    ("/calendar", False, None),
    ("/power-ranking", False, None),
    ("/players/leaderboard?metric=goals&limit=5", False, None),
    ("/players/identity-map", False, None),
    ("/liguilla/results", False, None),
    ("/news", False, None),
]

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def _get(base, path, timeout=25):
    t0 = time.time()
    r = requests.get(base + path, timeout=timeout)
    return r, (time.time() - t0) * 1000


def main() -> None:
    ap = argparse.ArgumentParser(description="Chequeo rapido de la Liga MX API")
    ap.add_argument("url", nargs="?", default=DEFAULT_URL, help="URL base de la API")
    ap.add_argument("--max-age-hours", type=float, default=12.0,
                    help="Antiguedad maxima aceptable de los datos (default 12h)")
    args = ap.parse_args()
    base = args.url.rstrip("/")

    print(f"🩺 Chequeando {base}\n")
    failures = 0
    warnings = 0

    # Nota: el primer request puede tardar si el servicio (free tier) estaba dormido.
    for path, critical, validator in CHECKS:
        try:
            r, ms = _get(base, path)
            ok = r.status_code == 200
            detail = ""
            if ok and validator:
                msg = validator(r.json())
                if msg:
                    ok, detail = False, msg
        except Exception as e:
            ok, ms, detail = False, 0, str(e)[:60]

        if ok:
            print(f"  {GREEN}✔{RESET} {path:<45} {int(ms)}ms")
        elif critical:
            failures += 1
            print(f"  {RED}✗{RESET} {path:<45} FALLO {detail}")
        else:
            warnings += 1
            print(f"  {YELLOW}!{RESET} {path:<45} aviso {detail}")

    # Frescura de los datos
    print()
    try:
        r, _ = _get(base, "/sync/status")
        s = r.json()
        age_h = s.get("data_age_hours")
        last = s.get("last_successful_sync") or {}
        print(f"📊 Datos: temporada={last.get('season')} equipos={last.get('teams')} "
              f"jugadores={last.get('players')} partidos={last.get('matches')}")
        if age_h is None:
            print(f"  {YELLOW}!{RESET} sin sync exitoso registrado todavia")
            warnings += 1
        elif age_h > args.max_age_hours:
            print(f"  {YELLOW}!{RESET} datos con {age_h}h de antiguedad (> {args.max_age_hours}h)")
            warnings += 1
        else:
            print(f"  {GREEN}✔{RESET} datos frescos ({age_h}h)")
    except Exception as e:
        print(f"  {RED}✗{RESET} no se pudo leer /sync/status: {str(e)[:60]}")
        failures += 1

    print("\n" + "=" * 50)
    if failures:
        print(f"{RED}RESULTADO: {failures} fallo(s) critico(s), {warnings} aviso(s){RESET}")
        sys.exit(1)
    print(f"{GREEN}RESULTADO: todo OK{RESET}" + (f" ({warnings} aviso(s))" if warnings else ""))


if __name__ == "__main__":
    main()
