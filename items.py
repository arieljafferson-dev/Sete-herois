# items.py

from __future__ import annotations

import random
from typing import List

import pygame
from config import BROWN, DGRAY, GRAY, ITEM_TABLE, RARITY_COLOR, WHITE, YELLOW


class Chest:
    """Baú no mapa que contém itens."""

    # Peso base por raridade — modificado pela fase
    _BASE_WEIGHTS = {"comum": 20, "raro": 5, "épico": 0}

    def __init__(self, x: int, y: int, phase: int) -> None:
        self.rect    = pygame.Rect(x, y, 36, 30)
        self.opened  = False
        self.phase   = phase
        self.content = self._generate()
        self._font   = pygame.font.SysFont("Arial", 14, bold=True)

    def _generate(self) -> List[dict]:
        weights = {
            "comum": max(5,  20 - self.phase * 2),
            "raro":  5 + self.phase * 2,
            "épico": max(0,  self.phase - 2),
        }

        candidates = [item for item in ITEM_TABLE if weights.get(item.rarity, 0) > 0]
        if not candidates:
            return []

        wts   = [weights[item.rarity] for item in candidates]
        picks = random.choices(candidates, weights=wts, k=random.randint(1, 3))
        # Converte ItemDef → dict para compatibilidade com o restante do código
        return [item.as_dict() for item in picks]

    def try_open(self, player_rect: pygame.Rect, cam_x: int = 0) -> List[dict]:
        """Retorna lista de itens se o jogador colidiu, senão []."""
        if self.opened or not player_rect.colliderect(self.rect):
            return []
        self.opened = True
        return self.content

    def draw(self, surface: pygame.Surface, cam_x: int) -> None:
        rx = self.rect.x - cam_x
        ry = self.rect.y
        # Culling
        if rx + self.rect.w < 0 or rx > surface.get_width():
            return

        color  = BROWN if not self.opened else DGRAY
        border = YELLOW if not self.opened else GRAY
        pygame.draw.rect(surface, color,  (rx, ry, self.rect.w, self.rect.h), border_radius=4)
        pygame.draw.rect(surface, border, (rx, ry, self.rect.w, self.rect.h), 2, border_radius=4)

        icon = self._font.render("📦" if not self.opened else "  ", True, WHITE)
        surface.blit(icon, (rx + 6, ry + 6))


def loot_description(item: dict) -> str:
    return f"[{item['rarity'].upper()}] {item['name']} — {item['desc']}"
