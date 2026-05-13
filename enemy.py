# enemy.py

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame
from config import *

# ---------------------------------------------------------------------------
# Templates de inimigos — dataclasses imutáveis (hashable, seguras para cache)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EnemyTemplate:
    name  : str
    hp    : int
    atk   : int
    def_  : int
    spd   : int
    xp    : int
    gold  : int
    color : Tuple[int, int, int]
    skill : Optional[str] = None
    is_boss: bool         = False


# Fase 1 — Floresta
_PHASE_1 = (
    EnemyTemplate("Goblin",  35,  8,  3,  7, 20,  8, (80,  180, 80)),
    EnemyTemplate("Lobo",    50, 12,  4, 11, 30, 12, (160, 140, 100), skill="mordida"),
    EnemyTemplate("Slime",   28,  5,  8,  4, 15,  6, (100, 220, 180)),
)
# Fase 2 — Caverna
_PHASE_2 = (
    EnemyTemplate("Morcego",        40, 10,  3, 14, 28, 10, (100, 80,  130)),
    EnemyTemplate("Aranha",         55, 14,  5, 10, 38, 14, (60,  60,  80),  skill="veneno"),
    EnemyTemplate("Golem de Pedra", 90, 16, 14,  3, 55, 20, (140, 120, 100)),
)
# Fase 3 — Castelo
_PHASE_3 = (
    EnemyTemplate("Cavaleiro Sombrio", 80, 18, 12,  7, 50, 18, (80,  80,  120), skill="defesa"),
    EnemyTemplate("Arqueiro",          60, 20,  5, 12, 45, 16, (160, 120, 60)),
    EnemyTemplate("Mago Traidor",      55,  8,  6,  9, 48, 20, (120, 80,  200), skill="magia"),
)
# Fase 4 — Deserto
_PHASE_4 = (
    EnemyTemplate("Escorpião", 70, 22,  8, 10, 58, 22, (200, 160, 40),  skill="veneno"),
    EnemyTemplate("Múmia",    100, 16, 10,  5, 65, 25, (210, 200, 170), skill="maldição"),
    EnemyTemplate("Djinn",     65, 24,  8, 13, 72, 28, (255, 140, 60),  skill="magia"),
)
# Fase 5 — Mundo Final (minions)
_PHASE_5 = (
    EnemyTemplate("Demônio",  110, 28, 12, 12, 90, 35, (200, 40,  40),  skill="magia"),
    EnemyTemplate("Espectro",  80, 24,  6, 18, 80, 30, (180, 180, 255), skill="veneno"),
)

ENEMY_TEMPLATES: Dict[int, Tuple[EnemyTemplate, ...]] = {
    1: _PHASE_1,
    2: _PHASE_2,
    3: _PHASE_3,
    4: _PHASE_4,
    5: _PHASE_5,
}

BOSS_TEMPLATE = EnemyTemplate(
    name="Lorde das Sombras",
    hp=600, atk=35, def_=18, spd=10,
    xp=500, gold=200,
    color=(140, 0, 160),
    is_boss=True,
)

# ---------------------------------------------------------------------------
# Enemy
# ---------------------------------------------------------------------------
class Enemy:
    def __init__(self, template: EnemyTemplate, phase_level_bonus: int = 0) -> None:
        b = phase_level_bonus
        self.name        = template.name
        self.max_hp      = template.hp   + b * 10
        self.hp          = self.max_hp
        self.atk         = template.atk  + b * 2
        self.def_        = template.def_ + b
        self.spd         = template.spd
        self.xp_reward   = template.xp   + b * 8
        self.gold_reward = template.gold  + b * 4
        self.color       = template.color
        self.skill       = template.skill
        self.is_boss     = template.is_boss

        # Estado de batalha
        self.effects: Dict[str, dict] = {}
        self.turn_count = 0
        self.def_up     = False

        # Posição no mapa
        self.rect   = pygame.Rect(0, 0, 36, 48)
        self.active = True

        # Cache da fonte (evita criar nova a cada frame)
        self._label_font = pygame.font.SysFont("Arial", 11, bold=True)

    # ------------------------------------------------------------------
    # Lógica de batalha
    # ------------------------------------------------------------------
    def choose_action(self) -> dict:
        self.turn_count += 1

        if self.is_boss and self.turn_count % 3 == 0:
            return {
                "type": "skill", "name": "Explosão das Trevas",
                "mult": 2.5, "msg": f"{self.name} usa Explosão das Trevas!",
            }

        if self.skill and random.random() < 0.35:
            return self._skill_action()

        return {"type": "attack", "msg": f"{self.name} ataca!"}

    def _skill_action(self) -> dict:
        """Retorna a ação de habilidade correspondente ao skill deste inimigo."""
        dispatch = {
            "veneno":   lambda: {"type": "poison",   "msg": f"{self.name} injeta veneno!"},
            "magia":    lambda: {"type": "skill",    "name": "Magia", "mult": 1.8,
                                  "ignore_def": True, "msg": f"{self.name} lança uma magia!"},
            "defesa":   lambda: {"type": "buff_def", "msg": f"{self.name} assume postura defensiva!"},
            "mordida":  lambda: {"type": "skill",    "name": "Mordida", "mult": 1.4,
                                  "msg": f"{self.name} morde ferozmente!"},
            "maldição": lambda: {"type": "debuff",   "msg": f"{self.name} lança uma maldição!"},
        }
        factory = dispatch.get(self.skill)
        return factory() if factory else {"type": "attack", "msg": f"{self.name} ataca!"}

    def effective_def(self) -> int:
        return self.def_ * (2 if self.def_up else 1)

    def tick_effects(self) -> List[str]:
        msgs: List[str] = []
        expired: List[str] = []

        for name, data in self.effects.items():
            if name == "poison":
                dmg = max(1, int(self.max_hp * data["val"]))
                self.hp = max(0, self.hp - dmg)
                msgs.append(f"{self.name} sofre {dmg} de veneno!")
            data["turns"] -= 1
            if data["turns"] <= 0:
                expired.append(name)

        for key in expired:
            del self.effects[key]

        return msgs

    # ------------------------------------------------------------------
    # Render no mapa de exploração
    # ------------------------------------------------------------------
    def draw_map(self, surface: pygame.Surface, cam_x: int) -> None:
        if not self.active:
            return
        rx = self.rect.x - cam_x
        ry = self.rect.y
        # Culling: não desenha se fora da tela
        if rx + self.rect.w < 0 or rx > SCREEN_W:
            return

        pygame.draw.rect(surface, self.color, (rx, ry, self.rect.w, self.rect.h), border_radius=5)
        if self.is_boss:
            pygame.draw.rect(surface, YELLOW, (rx, ry, self.rect.w, self.rect.h), 3, border_radius=5)

        lbl = self._label_font.render(self.name[:6], True, WHITE)
        surface.blit(lbl, (rx + 2, ry + self.rect.h - 16))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def make_enemy(phase: int, *, is_boss: bool = False) -> Enemy:
    bonus = (phase - 1) * 2
    if is_boss:
        return Enemy(BOSS_TEMPLATE, bonus)
    pool = ENEMY_TEMPLATES.get(phase, ENEMY_TEMPLATES[1])
    return Enemy(random.choice(pool), bonus)
