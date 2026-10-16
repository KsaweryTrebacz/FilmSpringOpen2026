"""Ustawienia aplikacji z pliku .env i zmiennych środowiskowych."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv

OPENAI_VARS = ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
SPEECH_VARS = ("AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION")


class ConfigError(RuntimeError):
    """Brakuje ustawień albo mają zły format."""


@dataclass(frozen=True)
class Settings:
    openai_endpoint: str
    openai_api_key: str
    openai_deployment: str
    openai_api_version: str = "2024-10-21"
    speech_key: str = ""
    speech_region: str = ""
    language: str = "pl-PL"
    voice: str = "pl-PL-MarekNeural"
    voice_rate: str = "-10%"
    initial_silence_ms: int = 6000
    end_silence_ms: int = 1200
    max_reprompts: int = 2


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


def load_settings(env: Mapping[str, str] | None = None, *, require_speech: bool = True) -> Settings:
    """Czyta ustawienia. Bez `env` najpierw ładuje plik .env z bieżącego katalogu."""
    if env is None:
        env = load_env()
    require(env, *OPENAI_VARS, *(SPEECH_VARS if require_speech else ()))
    defaults = Settings(openai_endpoint="", openai_api_key="", openai_deployment="")
    return Settings(
        openai_endpoint=env["AZURE_OPENAI_ENDPOINT"],
        openai_api_key=env["AZURE_OPENAI_API_KEY"],
        openai_deployment=env["AZURE_OPENAI_DEPLOYMENT"],
        openai_api_version=env.get("AZURE_OPENAI_API_VERSION") or defaults.openai_api_version,
        speech_key=env.get("AZURE_SPEECH_KEY", ""),
        speech_region=env.get("AZURE_SPEECH_REGION", ""),
        language=env.get("BAJKA_LANGUAGE") or defaults.language,
        voice=env.get("BAJKA_VOICE") or defaults.voice,
        voice_rate=env.get("BAJKA_VOICE_RATE") or defaults.voice_rate,
        initial_silence_ms=get_int(env, "BAJKA_INITIAL_SILENCE_MS", defaults.initial_silence_ms),
        end_silence_ms=get_int(env, "BAJKA_END_SILENCE_MS", defaults.end_silence_ms),
        max_reprompts=get_int(env, "BAJKA_MAX_REPROMPTS", defaults.max_reprompts),
    )
