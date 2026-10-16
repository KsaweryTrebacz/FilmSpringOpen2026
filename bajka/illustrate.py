"""Ilustracje scen w stylu bajki przez Azure AI Foundry (wdrożenie modelu gpt-image).

Moduł spełnia kontrakt `bajka.ports.Illustrator`. Styl i obrazy referencyjne postaci bierze ze scenariusza.
Jedna ilustracja z pomiarem czasu:  python -m bajka.illustrate SCENARIUSZ "opis sceny po angielsku"
Produkcja i pomiar wielu ujęć:      python -m bajka.illustrate SCENARIUSZ --batch ujecia.yaml
"""

from __future__ import annotations

import argparse
import base64
import statistics
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from bajka.config import ConfigError, get_int, load_env, require
from bajka.scenario import ScenarioError, load_scenario


@dataclass(frozen=True)
class ImageSettings:
    endpoint: str
    api_key: str
    deployment: str  # nazwa wdrożenia w Azure, np. gpt-image-2
    api_version: str = "2025-04-01-preview"
    size: str = "1536x1024"
    quality: str = "medium"
    timeout_s: int = 25

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ImageSettings:
        require(env, "AZURE_IMAGE_ENDPOINT", "AZURE_IMAGE_API_KEY", "AZURE_IMAGE_DEPLOYMENT")
        return cls(
            endpoint=env["AZURE_IMAGE_ENDPOINT"],
            api_key=env["AZURE_IMAGE_API_KEY"],
            deployment=env["AZURE_IMAGE_DEPLOYMENT"],
            api_version=env.get("AZURE_IMAGE_API_VERSION") or cls.api_version,
            size=env.get("BAJKA_IMAGE_SIZE") or cls.size,
            quality=env.get("BAJKA_IMAGE_QUALITY") or cls.quality,
            timeout_s=get_int(env, "BAJKA_IMAGE_TIMEOUT_S", cls.timeout_s),
        )


def build_prompt(scene_prompt: str, style: str, with_references: bool) -> str:
    parts = [scene_prompt.strip().rstrip(".") + "."]
    if style:
        parts.append(f"Style: {style.strip().rstrip('.')}.")
    if with_references:
        parts.append("Draw the characters exactly as they look in the reference images.")
    # Ilustracja, nie zdjęcie: Azure domyślnie blokuje fotorealistyczne obrazy dzieci.
    parts.append("Illustration for young children, not photorealistic, no text or letters.")
    return " ".join(parts)


class AzureIllustrator:
    def __init__(
        self,
        client: Any,
        deployment: str,
        out_dir: Path,
        style: str = "",
        references: Sequence[Path] = (),
        size: str = "1536x1024",
        quality: str = "medium",
    ) -> None:
        self._client = client
        self._deployment = deployment
        self._out_dir = Path(out_dir)
        self._style = style
        self._references = tuple(references)
        self._size = size
        self._quality = quality

    @classmethod
    def from_settings(
        cls,
        settings: ImageSettings,
        out_dir: Path,
        style: str = "",
        references: Sequence[Path] = (),
        max_retries: int = 0,
    ) -> AzureIllustrator:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            timeout=float(settings.timeout_s),
            max_retries=max_retries,  # na żywo 0: lepiej od razu klip zapasowy niż czekanie na ponowienie
        )
        return cls(client, settings.deployment, out_dir, style, references, settings.size, settings.quality)

    def draw(self, prompt: str, name: str | None = None) -> Path:
        full_prompt = build_prompt(prompt, self._style, with_references=bool(self._references))
        options = {"model": self._deployment, "prompt": full_prompt, "size": self._size, "quality": self._quality}
        if self._references:
            with ExitStack() as stack:
                images = [stack.enter_context(open(path, "rb")) for path in self._references]
                result = self._client.images.edit(image=images, **options)
        else:
            result = self._client.images.generate(n=1, **options)
        self._out_dir.mkdir(parents=True, exist_ok=True)
        target = self._out_dir / f"{name or 'obraz_' + uuid.uuid4().hex[:8]}.png"
        target.write_bytes(base64.b64decode(result.data[0].b64_json))
        return target


def load_shots(path: Path) -> list[tuple[str, str]]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{path}: oczekiwano listy ujęć [{{name, prompt}}, ...]")
    shots = []
    for number, item in enumerate(raw, start=1):
        name = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
        prompt = str(item.get("prompt") or "").strip() if isinstance(item, dict) else ""
        if not name or not prompt:
            raise ValueError(f"{path}: ujęcie {number} musi mieć 'name' i 'prompt'")
        shots.append((name, prompt))
    return shots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m bajka.illustrate", description="Ilustracje scen przez Azure AI Foundry, z pomiarem czasu."
    )
    parser.add_argument("scenario", type=Path, help="scenariusz YAML (styl i obrazy referencyjne postaci)")
    parser.add_argument("prompt", nargs="?", help="opis sceny po angielsku")
    parser.add_argument("--batch", type=Path, help="plik YAML z listą ujęć: [{name, prompt}, ...]")
    parser.add_argument("--out", type=Path, default=Path("ilustracje"), help="katalog na obrazy (domyślnie ilustracje)")
    parser.add_argument(
        "--retries",
        type=int,
        help="ponowienia przy błędach i limicie Azure (domyślnie 3 dla --batch, 0 dla jednego obrazu; do pomiaru czasu: 0)",
    )
    args = parser.parse_args(argv)
    if (args.prompt is None) == (args.batch is None):
        parser.error("podaj opis sceny albo --batch")
    try:
        scenario = load_scenario(args.scenario)
        settings = ImageSettings.from_env(load_env())
        shots = load_shots(args.batch) if args.batch else [(None, args.prompt)]
    except (ScenarioError, ConfigError, ValueError, OSError, yaml.YAMLError) as exc:
        print(exc, file=sys.stderr)
        return 2

    # Przy produkcji wolno ponawiać (limit to ok. 5 obrazów na minutę); czas mierzymy bez ponowień (--retries 0).
    retries = args.retries if args.retries is not None else (3 if args.batch else 0)
    illustrator = AzureIllustrator.from_settings(
        settings, args.out, scenario.style, scenario.references, max_retries=retries
    )
    times = []
    for name, prompt in shots:
        started = time.perf_counter()
        try:
            path = illustrator.draw(prompt, name=name)
        except Exception as exc:  # demo pokazuje każdy błąd Azure (filtr treści, limit, klucz) i idzie dalej
            print(f"Błąd ({name or prompt}, {time.perf_counter() - started:.1f} s): {exc}", file=sys.stderr)
            continue
        times.append(time.perf_counter() - started)
        print(f"{path} ({times[-1]:.1f} s)", flush=True)
    if not times:
        return 1
    if len(shots) > 1:
        median, longest = statistics.median(times), max(times)
        print(f"Mediana: {median:.1f} s, maksimum: {longest:.1f} s, udane: {len(times)}/{len(shots)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
