"""Atrapy modułów do testów silnika ze scenami generowanymi na żywo."""

from pathlib import Path


class FakePlayer:
    def __init__(self):
        self.calls = []

    def play(self, clip):
        self.calls.append(("play", clip.name))

    def loop(self, clip):
        self.calls.append(("loop", clip.name))


class FakeListener:
    """Zwraca kolejne odpowiedzi; wyjątek z listy zostaje rzucony."""

    def __init__(self, *answers):
        self._answers = list(answers)

    def listen(self):
        answer = self._answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeVoice:
    def __init__(self):
        self.lines = []

    def say(self, text):
        self.lines.append(text)


class FakeResolver:
    """Mapuje transkrypcję na Interpretation."""

    def __init__(self, answers):
        self._answers = answers

    def resolve(self, scene, transcript):
        return self._answers[transcript]


class FakeImaginer:
    """Mapuje transkrypcję na Vision albo wyjątek."""

    def __init__(self, answers=None):
        self._answers = answers or {}
        self.calls = []

    def imagine(self, scene, transcript):
        self.calls.append((scene.id, transcript))
        answer = self._answers[transcript]
        if isinstance(answer, Exception):
            raise answer
        return answer


class FakeIllustrator:
    """Zapamiętuje prompty; może rzucić wyjątkiem albo czekać na sygnał (symulacja wolnego Azure)."""

    def __init__(self, error=None, gate=None):
        self.prompts = []
        self._error = error
        self._gate = gate

    def draw(self, prompt):
        self.prompts.append(prompt)
        if self._gate is not None:
            self._gate.wait(timeout=5)
        if self._error is not None:
            raise self._error
        return Path(f"obraz_{len(self.prompts)}.png")


class FakeAnimator:
    def __init__(self, error=None):
        self._error = error

    def animate(self, image):
        if self._error is not None:
            raise self._error
        return image.with_suffix(".mp4")
