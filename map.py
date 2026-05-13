# map.py

from __future__ import annotations

import random
from typing import List, Optional

import pygame
from config import *
from enemy import make_enemy
from items import Chest

TILE = TILE_SIZE


class Phase:
    """Gera e gerencia uma fase completa."""

    def __init__(self, phase_num: int) -> None:
        self.num   = phase_num
        self.theme = PHASE_THEMES[phase_num]
        self.width = 4800

        self.platforms : List[pygame.Rect] = []
        self.enemies   : List             = []
        self.chests    : List[Chest]      = []
        self.goal_rect : Optional[pygame.Rect] = None

        # Fontes cacheadas (criadas uma vez por fase)
        self._font_sm = pygame.font.SysFont("Arial", 11, bold=True)

        self._generate()

    # ------------------------------------------------------------------
    # Geração procedural
    # ------------------------------------------------------------------
    def _generate(self) -> None:
        W      = self.width
        rng    = random.Random(self.num * 42)
        ground = SCREEN_H - TILE

        # Chão base
        self.platforms.append(pygame.Rect(0, ground, W, TILE * 2))

        # Plataformas flutuantes
        x = 300
        while x < W - 400:
            pw = rng.randint(3, 8) * TILE
            py = rng.randint(3, 7) * TILE
            self.platforms.append(pygame.Rect(x, py, pw, TILE))
            x += pw + rng.randint(80, 200)

        # Inimigos
        n_enemies = 6 + self.num * 2
        for i in range(n_enemies):
            is_boss = (self.num == 5) and (i == n_enemies - 1)
            enemy   = make_enemy(self.num, is_boss=is_boss)
            enemy.rect.x = rng.randint(400, W - 200)
            enemy.rect.y = ground - enemy.rect.h
            self.enemies.append(enemy)

        # Baús (preferencialmente sobre plataformas)
        floating = [p for p in self.platforms[1:] if p.width > 0]
        for _ in range(3 + self.num):
            if floating:
                p  = rng.choice(floating)
                cx = p.x + rng.randint(0, max(0, p.width - 40))
                cy = p.y - 30
            else:
                cx = rng.randint(200, W - 200)
                cy = ground - TILE
            self.chests.append(Chest(cx, cy, self.num))

        # Portal de saída
        self.goal_rect = pygame.Rect(W - 120, ground - TILE * 2, TILE, TILE * 2)

    # ------------------------------------------------------------------
    # Colisões (O(n) simples — suficiente para os tamanhos de fase atuais)
    # ------------------------------------------------------------------
    def check_enemy_collision(self, player_rect: pygame.Rect):
        for e in self.enemies:
            if e.active and player_rect.colliderect(e.rect):
                return e
        return None

    def check_chest_collision(self, player_rect: pygame.Rect) -> list:
        items: list = []
        for chest in self.chests:
            items.extend(chest.try_open(player_rect, cam_x=0))
        return items

    def check_goal(self, player_rect: pygame.Rect) -> bool:
        return self.goal_rect is not None and player_rect.colliderect(self.goal_rect)

    # ------------------------------------------------------------------
    # Câmera
    # ------------------------------------------------------------------
    def clamp_camera(self, player_rect: pygame.Rect) -> int:
        cx = player_rect.centerx - SCREEN_W // 2
        return max(0, min(cx, self.width - SCREEN_W))

    # ------------------------------------------------------------------
    # Render (com culling horizontal)
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, cam_x: int) -> None:
        surface.fill(self.theme.sky)
        self._draw_platforms(surface, cam_x)
        for chest in self.chests:
            chest.draw(surface, cam_x)
        for enemy in self.enemies:
            enemy.draw_map(surface, cam_x)
        self._draw_goal(surface, cam_x)

    def _draw_platforms(self, surface: pygame.Surface, cam_x: int) -> None:
        pc = self.theme.platform
        bg = self.theme.bg
        for p in self.platforms:
            if p.width == 0:
                continue
            rx = p.x - cam_x
            # Culling: pula plataformas fora da tela
            if rx + p.width < 0 or rx > SCREEN_W:
                continue
            pygame.draw.rect(surface, pc, (rx, p.y, p.width, p.height))
            pygame.draw.rect(surface, bg, (rx, p.y, p.width, p.height), 2)

    def _draw_goal(self, surface: pygame.Surface, cam_x: int) -> None:
        if not self.goal_rect:
            return
        rx = self.goal_rect.x - cam_x
        if rx + self.goal_rect.width < 0 or rx > SCREEN_W:
            return
        pygame.draw.rect(surface, PURPLE,
                         (rx, self.goal_rect.y, self.goal_rect.width, self.goal_rect.height),
                         border_radius=8)
        pygame.draw.rect(surface, YELLOW,
                         (rx, self.goal_rect.y, self.goal_rect.width, self.goal_rect.height),
                         3, border_radius=8)
        lbl = self._font_sm.render("SAÍDA", True, WHITE)
        surface.blit(lbl, (rx + 2, self.goal_rect.y + 8))
