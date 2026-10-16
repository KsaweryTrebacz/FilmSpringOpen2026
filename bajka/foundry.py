"""Foundry Local: lokalne modele AI (Phi, Whisper) na NPU, GPU albo CPU — bez chmury i bez kluczy.

Wspólne dla `bajka/local_intent.py` i `bajka/local_stt.py`. Foundry Local sam wybiera wariant modelu
pod sprzęt (na Copilot+ PC wariant na NPU, przez Windows ML); `FOUNDRY_DEVICE` pozwala to wymusić.
Pierwsze uruchomienie pobiera sterowniki akceleratorów i model, kolejne korzystają z pamięci podręcznej.

Lista modeli z katalogu i ich wariantów: python -m bajka.foundry [--device NPU]
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
from collections.abc import Mapping
from typing import Any

from bajka.config import ConfigError

log = logging.getLogger(__name__)

APP_NAME = "bajka"
DEVICES = ("auto", "NPU", "GPU", "CPU")
INSTALL_HINT = 'pip install -e ".[local]"'

_lock = threading.Lock()


class FoundryError(RuntimeError):
    """Foundry Local nie działa: brak pakietu, brak modelu w katalogu albo błąd pobierania."""


def read_device(env: Mapping[str, str]) -> str:
    """FOUNDRY_DEVICE: auto (domyślnie), NPU, GPU albo CPU."""
    value = (env.get("FOUNDRY_DEVICE") or "auto").strip()
    device = "auto" if value.lower() == "auto" else value.upper()
    if device not in DEVICES:
        raise ConfigError(f"FOUNDRY_DEVICE musi być jednym z: {', '.join(DEVICES)}, jest: {value!r}")
    return device


def import_sdk() -> Any:
    try:
        import foundry_local_sdk
    except ImportError as exc:
        raise FoundryError(f"Brak pakietu foundry-local-sdk. Zainstaluj: {INSTALL_HINT}") from exc
    return foundry_local_sdk


def get_manager(sdk: Any = None) -> Any:
    """Inicjuje Foundry Local raz na proces i rejestruje akceleratory (NPU/GPU) dostępne na tym komputerze."""
    sdk = sdk or import_sdk()
    with _lock:
        if sdk.FoundryLocalManager.instance is None:
            sdk.FoundryLocalManager.initialize(sdk.Configuration(app_name=APP_NAME))
            manager = sdk.FoundryLocalManager.instance
            log.info("Foundry Local: przygotowuję akceleratory (pierwszy raz pobiera sterowniki)…")
            try:
                manager.download_and_register_eps(progress_callback=_ProgressLog("akcelerator"))
            except Exception:
                # Bez sieci albo bez sterowników modele nadal działają na CPU; bajka nie może przez to nie wystartować.
                log.warning("Nie udało się przygotować akceleratorów NPU/GPU, modele pójdą na CPU", exc_info=True)
        return sdk.FoundryLocalManager.instance


def device_of(model: Any) -> str:
    runtime = getattr(model.info, "runtime", None)
    device = getattr(runtime, "device_type", None)
    return str(getattr(device, "value", device) or "?").upper()


def load_model(alias: str, device: str = "auto", manager: Any = None) -> Any:
    """Zwraca załadowany model z katalogu Foundry Local, w razie potrzeby najpierw go pobiera."""
    manager = manager or get_manager()
    model = manager.catalog.get_model(alias)
    if model is None:
        raise FoundryError(f"Foundry Local nie zna modelu '{alias}'. Dostępne modele: python -m bajka.foundry")
    if device != "auto":
        _select_device(model, device)
    if not model.is_cached:
        log.info("Pobieram model %s (tylko za pierwszym razem)…", model.id)
        model.download(_ProgressLog(alias))
    if not model.is_loaded:
        model.load()
    log.info("Model gotowy: %s na %s", model.id, device_of(model))
    return model


def openai_base_url(manager: Any = None) -> str:
    """Adres lokalnego serwera zgodnego z OpenAI (uruchamia go przy pierwszym wywołaniu)."""
    manager = manager or get_manager()
    with _lock:
        if not getattr(manager, "urls", None):
            manager.start_web_service()
    return f"{manager.urls[0].rstrip('/')}/v1"


def _select_device(model: Any, device: str) -> None:
    variant = next((v for v in model.variants if device_of(v) == device), None)
    if variant is None:
        available = ", ".join(sorted({device_of(v) for v in model.variants}))
        log.warning("Model %s nie ma wariantu na %s (są: %s), zostaje wybór automatyczny", model.alias, device, available)
        return
    model.select_variant(variant)


class _ProgressLog:
    """Loguje postęp pobierania co 10%, żeby nie zalewać konsoli."""

    def __init__(self, what: str) -> None:
        self._what = what
        self._next = 0.0

    def __call__(self, *args: Any) -> None:
        percent = float(args[-1])  # modele: (procent), akceleratory: (nazwa, procent)
        if percent >= self._next:
            log.info("Pobieranie %s: %.0f%%", args[0] if len(args) > 1 else self._what, percent)
            self._next = percent + 10


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bajka.foundry", description="Modele z katalogu Foundry Local.")
    parser.add_argument("--device", choices=DEVICES[1:], help="pokaż tylko modele z wariantem na tym urządzeniu")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        manager = get_manager()
    except FoundryError as exc:
        print(exc, file=sys.stderr)
        return 2
    except Exception as exc:  # demo ma pokazać każdy błąd Foundry Local, a nie wywrócić się
        print(f"Błąd Foundry Local: {exc}", file=sys.stderr)
        return 1
    print(f"{'model':28} {'zadanie':30} warianty")
    for model in manager.catalog.list_models():
        devices = sorted({device_of(v) for v in model.variants})
        if args.device and args.device not in devices:
            continue
        cached = " (pobrany)" if model.is_cached else ""
        print(f"{model.alias:28} {str(getattr(model.info, 'task', '') or ''):30} {', '.join(devices)}{cached}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
