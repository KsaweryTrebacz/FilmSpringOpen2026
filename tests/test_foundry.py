from types import SimpleNamespace

import pytest

from bajka.config import ConfigError
from bajka.foundry import FoundryError, device_of, get_manager, load_model, openai_base_url, read_device


def variant(model_id, device):
    return SimpleNamespace(id=model_id, info=SimpleNamespace(runtime=SimpleNamespace(device_type=device)))


class FakeModel:
    def __init__(self, alias, variants, cached=False):
        self.alias = alias
        self.variants = variants
        self.selected = variants[0]
        self.is_cached = cached
        self.is_loaded = False
        self.downloads = 0

    @property
    def id(self):
        return self.selected.id

    @property
    def info(self):
        return self.selected.info

    def select_variant(self, chosen):
        self.selected = chosen

    def download(self, progress):
        progress(50.0)
        progress(100.0)
        self.downloads += 1
        self.is_cached = True

    def load(self):
        self.is_loaded = True


class FakeManager:
    def __init__(self, *models):
        models_by_alias = {m.alias: m for m in models}
        self.catalog = SimpleNamespace(get_model=models_by_alias.get)
        self.urls = []

    def start_web_service(self):
        self.urls = ["http://127.0.0.1:5273/"]


def phi():
    return FakeModel("phi-4-mini", [variant("phi-4-mini-cpu:1", "CPU"), variant("phi-4-mini-npu:1", "NPU")])


def test_device_setting_is_case_insensitive():
    assert read_device({}) == "auto"
    assert read_device({"FOUNDRY_DEVICE": "Auto"}) == "auto"
    assert read_device({"FOUNDRY_DEVICE": "npu"}) == "NPU"
    with pytest.raises(ConfigError):
        read_device({"FOUNDRY_DEVICE": "kalkulator"})


def test_device_of_reads_enum_values():
    enum_like = SimpleNamespace(value="npu")
    assert device_of(SimpleNamespace(info=SimpleNamespace(runtime=SimpleNamespace(device_type=enum_like)))) == "NPU"
    assert device_of(SimpleNamespace(info=SimpleNamespace(runtime=None))) == "?"


def test_load_model_downloads_once_and_loads():
    model = phi()

    loaded = load_model("phi-4-mini", manager=FakeManager(model))

    assert loaded is model
    assert model.downloads == 1 and model.is_loaded
    assert loaded.id == "phi-4-mini-cpu:1"  # auto: wariant wybrany przez Foundry Local


def test_load_model_selects_requested_device():
    model = phi()

    assert load_model("phi-4-mini", device="NPU", manager=FakeManager(model)).id == "phi-4-mini-npu:1"


def test_missing_device_variant_keeps_automatic_choice():
    model = phi()

    assert load_model("phi-4-mini", device="GPU", manager=FakeManager(model)).id == "phi-4-mini-cpu:1"


def test_cached_model_is_not_downloaded_again():
    model = FakeModel("whisper-tiny", [variant("whisper-tiny-cpu:1", "CPU")], cached=True)

    load_model("whisper-tiny", manager=FakeManager(model))

    assert model.downloads == 0


def test_unknown_model_is_reported():
    with pytest.raises(FoundryError, match="nie-ma"):
        load_model("nie-ma", manager=FakeManager())


def test_web_service_starts_once_and_returns_openai_url():
    manager = FakeManager()

    assert openai_base_url(manager) == "http://127.0.0.1:5273/v1"
    manager.start_web_service = lambda: pytest.fail("serwer uruchomiony drugi raz")
    assert openai_base_url(manager) == "http://127.0.0.1:5273/v1"


def test_manager_is_initialized_once_and_registers_accelerators():
    calls = []

    class FakeLocalManager:
        instance = None

        @classmethod
        def initialize(cls, config):
            calls.append(("init", config.app_name))
            cls.instance = SimpleNamespace(download_and_register_eps=lambda progress_callback: calls.append("eps"))

    sdk = SimpleNamespace(FoundryLocalManager=FakeLocalManager, Configuration=lambda app_name: SimpleNamespace(app_name=app_name))

    first = get_manager(sdk)
    second = get_manager(sdk)

    assert first is second
    assert calls == [("init", "bajka"), "eps"]


def test_failed_accelerator_download_does_not_stop_the_story():
    class FakeLocalManager:
        instance = None

        @classmethod
        def initialize(cls, config):
            def no_network(progress_callback):
                raise ConnectionError("brak internetu")

            cls.instance = SimpleNamespace(download_and_register_eps=no_network)

    sdk = SimpleNamespace(FoundryLocalManager=FakeLocalManager, Configuration=lambda app_name: SimpleNamespace(app_name=app_name))

    assert get_manager(sdk) is FakeLocalManager.instance
