"""Wspólne narzędzia do ustawień z pliku .env.

Każdy moduł ma własną klasę ustawień (`SttSettings`, `TtsSettings`, `LlmSettings`) z metodą
`from_env`, żeby dwie osoby nie edytowały jednego pliku konfiguracji.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from dotenv import find_dotenv, load_dotenv


class ConfigError(RuntimeError):
    """Brakuje ustawień albo mają zły format."""


def load_env() -> Mapping[str, str]:
    """Ładuje plik .env z bieżącego katalogu (lub nadrzędnego) i zwraca zmienne środowiskowe."""
    load_dotenv(find_dotenv(usecwd=True))
    return os.environ


def require(env: Mapping[str, str], *names: str) -> None:
    missing = [name for name in names if not env.get(name)]
    if missing:
        raise ConfigError("Brak ustawień w .env: " + ", ".join(missing))


def get_int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} musi być liczbą całkowitą, jest: {value!r}") from exc
