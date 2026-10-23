"""Registre des cas de test. Chaque module de cas s'enregistre via @case(...)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

REGISTRY: list["Case"] = []


@dataclass
class Case:
    endpoint: str          # speech | transcriptions | chat-image | chat-audio
    name: str
    title: str
    fn: Callable
    expect: str = "2xx"    # 2xx | 4xx | any  (attente d'après la doc OpenAI ; un écart est un résultat)
    tags: tuple[str, ...] = ()
    notes: str = ""

    @property
    def id(self) -> str:
        return f"{self.endpoint}/{self.name}"


def case(endpoint: str, name: str, title: str, expect: str = "2xx", tags: tuple[str, ...] = (), notes: str = ""):
    def deco(fn):
        REGISTRY.append(Case(endpoint, name, title, fn, expect, tuple(tags), notes))
        return fn
    return deco


def load_all() -> list[Case]:
    from . import speech, transcriptions, chat_image, chat_audio  # noqa: F401  (effet de bord : enregistrement)
    return REGISTRY
