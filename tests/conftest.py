import copy
from pathlib import Path

import pytest

from bajka.scenario import parse_scenario

SCENARIO = {
    "hero": "Lisek Feliks, odważny i ciekawski lis.",
    "start": "intro",
    "scenes": {
        "intro": {
            "clip": "intro.mp4",
            "idle": "intro_idle.mp4",
            "question": "Idziemy do mrocznego lasu czy do jaskini?",
            "reprompt": "Hmm, nie usłyszałem. Las czy jaskinia?",
            "default": "las",
            "choices": {
                "las": {
                    "description": "pójść do mrocznego lasu",
                    "next": "las",
                    "reply": "Do lasu! Trzymaj się blisko!",
                },
                "jaskinia": {
                    "description": "wejść do jaskini",
                    "next": "jaskinia",
                    "reply": "Do jaskini! Mam latarkę!",
                },
            },
        },
        "las": {"clip": "las.mp4"},
        "jaskinia": {"clip": "jaskinia.mp4"},
    },
}


@pytest.fixture
def scenario_dict():
    return copy.deepcopy(SCENARIO)


@pytest.fixture
def scenario(scenario_dict):
    return parse_scenario(scenario_dict, base_dir=Path("film"))
