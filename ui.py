# ui.py

from __future__ import annotations

from typing import List, Tuple

import pygame
from config import (
    BLACK, BLUE, BROWN, CYAN, DGRAY, GRAY, GREEN, PURPLE,
    RED, RARITY_COLOR, SCREEN_H, SCREEN_W, WHITE, YELLOW,
    CLASS_BASES, TILE_SIZE, xp_to_next,
)

# ---------------------------------------------------------------------------
# Fontes — inicializadas uma única vez (evita criar objetos a cada frame)
# ---------------------------------------------------------------------------
pygame.font.init()

class _Fonts:
    SM  = pygame.font.SysFont("Arial", 14)
    MD  = pygame.font.SysFont("Arial", 18, bold=True)
    LG  = pygame.font.SysFont("Arial", 26, bold=True)
    XL  = pygame.font.SysFont("Arial", 38, bold=True)
    TTL = pygame.font.SysFont("Arial", 52, bold=True)

F = _Fonts  # alias curto

# ---------------------------------------------------------------------------
# Primitivos de desenho
# ---------------------------------------------------------------------------
def draw_bar(
    surface : pygame.Surface,
    x: int, y: int, w: int, h: int,
    val: int, max_val: int,
    color: tuple,
    bg    = DGRAY,
    border= WHITE,
) -> None:
    pygame.draw.rect(surface, bg,     (x, y, w, h), border_radius=4)
    fill = int(w * max(0, val) / max(1, max_val))
    if fill > 0:
        pygame.draw.rect(surface, color, (x, y, fill, h), border_radius=4)
    pygame.draw.rect(surface, border, (x, y, w, h), 1, border_radius=4)


def draw_text(
    surface : pygame.Surface,
    text    : str,
    x: int, y: int,
    font    = None,
    color   = WHITE,
    shadow  : bool = True,
) -> None:
    if font is None:
        font = F.SM
    if shadow:
        surface.blit(font.render(text, True, BLACK), (x + 1, y + 1))
    surface.blit(font.render(text, True, color), (x, y))


def draw_panel(
    surface : pygame.Surface,
    x: int, y: int, w: int, h: int,
    alpha   : int   = 200,
    color         = DGRAY,
    border        = GRAY,
) -> None:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((*color, alpha))
    surface.blit(s, (x, y))
    pygame.draw.rect(surface, border, (x, y, w, h), 2, border_radius=8)


# ---------------------------------------------------------------------------
# HUD de exploração
# ---------------------------------------------------------------------------
def draw_exploration_hud(
    surface   : pygame.Surface,
    player,
    phase_num : int,
    phase_name: str,
) -> None:
    draw_panel(surface, 0, 0, 320, 72)
    draw_text(surface, f"Fase {phase_num}: {phase_name}",               10, 6,  F.MD, YELLOW)
    draw_text(surface, f"Nível {player.level}  |  XP: {player.xp}/{xp_to_next(player.level)}",
              10, 28, F.SM, CYAN)
    draw_text(surface, "HP", 10, 48, F.SM)
    draw_bar (surface, 32, 50, 120, 14, player.hp, player.max_hp, RED)
    draw_text(surface, f"{player.hp}/{player.max_hp}", 158, 48, F.SM)
    draw_text(surface, "MP", 10, 62, F.SM)
    draw_bar (surface, 32, 64, 120, 10, player.mp, player.max_mp, BLUE)

    fx_x = 330
    for name in player.effects:
        col = RED if name == "poison" else CYAN
        draw_text(surface, f"[{name}]", fx_x, 6, F.SM, col)
        fx_x += 80


# ---------------------------------------------------------------------------
# Tela de batalha
# ---------------------------------------------------------------------------
def draw_battle(
    surface      : pygame.Surface,
    player,
    enemy,
    battle,
    selected_menu: int,
) -> None:
    # Fundo gradiente simples
    surface.fill(DGRAY)
    half = SCREEN_H // 2
    for i in range(half):
        pygame.draw.line(surface, (20, 0, 40), (0, i), (SCREEN_W, i))

    _draw_enemy_panel(surface, enemy)
    _draw_player_panel(surface, player)
    _draw_battle_menu(surface, selected_menu)
    _draw_battle_log(surface, battle)


def _draw_enemy_panel(surface: pygame.Surface, enemy) -> None:
    ew, eh = 120, 160
    ex = SCREEN_W // 2 - ew // 2
    ey = 40
    pygame.draw.rect(surface, enemy.color, (ex, ey, ew, eh), border_radius=12)
    if enemy.is_boss:
        pygame.draw.rect(surface, YELLOW, (ex, ey, ew, eh), 4, border_radius=12)
    draw_text(surface, enemy.name, ex, ey - 22, F.MD, YELLOW if enemy.is_boss else WHITE)
    draw_bar (surface, ex, ey + eh + 4, ew, 14, enemy.hp, enemy.max_hp, RED)
    draw_text(surface, f"{enemy.hp}/{enemy.max_hp}", ex, ey + eh + 20, F.SM)
    if "poison" in enemy.effects:
        draw_text(surface, "[venenado]", ex + ew + 6, ey, F.SM, GREEN)


def _draw_player_panel(surface: pygame.Surface, player) -> None:
    pw, ph = 90, 130
    px, py = 80, SCREEN_H - 280
    pygame.draw.rect(surface, player.color, (px, py, pw, ph), border_radius=10)
    draw_text(surface, player.class_name, px, py - 22, F.MD)
    draw_bar (surface, px, py + ph + 4,  pw + 40, 14, player.hp, player.max_hp, RED)
    draw_text(surface, f"HP {player.hp}/{player.max_hp}", px, py + ph + 20, F.SM)
    draw_bar (surface, px, py + ph + 38, pw + 40, 10, player.mp, player.max_mp, BLUE)
    draw_text(surface, f"MP {player.mp}/{player.max_mp}", px, py + ph + 50, F.SM, CYAN)


def _draw_battle_menu(surface: pygame.Surface, selected: int) -> None:
    mx, my = SCREEN_W - 280, SCREEN_H - 200
    options = ["[A] Atacar", "[H] Habilidade", "[I] Item", "[F] Fugir"]
    draw_panel(surface, mx - 10, my - 10, 270, 170)
    for i, opt in enumerate(options):
        draw_text(surface, opt, mx, my + i * 36, F.MD, YELLOW if i == selected else WHITE)


def _draw_battle_log(surface: pygame.Surface, battle) -> None:
    lx, ly = 10, SCREEN_H - 200
    draw_panel(surface, lx - 4, ly - 4, 460, 190)
    for i, line in enumerate(battle.recent_log()):
        if any(w in line for w in ("crítico", "CRÍTICO")):
            col = CYAN
        elif any(w in line for w in ("derrotado", "vitória", "✨")):
            col = YELLOW
        elif any(w in line for w in ("veneno", "💀")):
            col = RED
        else:
            col = WHITE
        draw_text(surface, line[:55], lx, ly + i * 22, F.SM, col)


# ---------------------------------------------------------------------------
# Menu de habilidades
# ---------------------------------------------------------------------------
def draw_skill_menu(surface: pygame.Surface, player) -> None:
    draw_panel(surface, 200, 100, 560, 320)
    draw_text(surface, "⚡ Habilidades", 220, 110, F.LG, YELLOW)

    if not player.skills:
        draw_text(surface, "Nenhuma habilidade desbloqueada.", 220, 160, F.MD, GRAY)
        return

    for i, sk in enumerate(player.skills):
        avail = player.mp >= sk.mp_cost
        col   = WHITE if avail else GRAY
        draw_text(surface, f"[{i+1}] {sk.name}  (MP: {sk.mp_cost})", 220, 155 + i * 50, F.MD, col)
        draw_text(surface, sk.desc, 240, 175 + i * 50, F.SM, CYAN if avail else GRAY)

    draw_text(surface, "[ESC] Voltar", 220, 390, F.SM, GRAY)


# ---------------------------------------------------------------------------
# Inventário
# ---------------------------------------------------------------------------
def draw_inv_menu(surface: pygame.Surface, player, selected: int = 0) -> None:
    draw_panel(surface, 100, 60, 760, 420)
    draw_text(surface, "🎒 Inventário", 120, 70, F.LG, YELLOW)

    wp = player.weapon["name"] if player.weapon else "—"
    ar = player.armor ["name"] if player.armor  else "—"
    draw_text(surface, f"Arma:     {wp}", 120, 110, F.SM, CYAN)
    draw_text(surface, f"Armadura: {ar}", 120, 128, F.SM, CYAN)

    if not player.inventory:
        draw_text(surface, "Inventário vazio.", 120, 170, F.MD, GRAY)
    else:
        for i, item in enumerate(player.inventory):
            ry  = 160 + i * 28
            col = RARITY_COLOR.get(item["rarity"], WHITE)
            bg  = (60, 60, 80) if i == selected else DGRAY
            pygame.draw.rect(surface, bg, (110, ry - 2, 720, 26), border_radius=4)
            draw_text(surface, f"[{i}] {item['name']}", 120, ry, F.SM, col)
            draw_text(surface, item["desc"],             360, ry, F.SM, GRAY)
            draw_text(surface, item["rarity"],           660, ry, F.SM, col)

    draw_text(surface, "[E] Equipar/Usar  |  [ESC] Fechar", 120, 450, F.SM, GRAY)


# ---------------------------------------------------------------------------
# Seleção de classe
# ---------------------------------------------------------------------------
def draw_class_select(surface: pygame.Surface, hovered: int) -> None:
    surface.fill((10, 10, 30))
    draw_text(surface, "Chronicles of Pyxel", SCREEN_W // 2 - 240, 40,  F.TTL, YELLOW)
    draw_text(surface, "Escolha sua classe:", SCREEN_W // 2 - 140, 110, F.LG,  WHITE)

    for i, (cname, b) in enumerate(CLASS_BASES.items()):
        cx  = 120 + i * 280
        cy  = 180
        sel = (i == hovered)
        draw_panel(surface, cx, cy, 240, 300, alpha=210, color=(20, 20, 50),
                   border=YELLOW if sel else GRAY)
        pygame.draw.circle(surface, b.color, (cx + 120, cy + 60), 44)
        draw_text(surface, b.symbol, cx + 104, cy + 42,  F.XL, WHITE)
        draw_text(surface, cname,    cx + 60,  cy + 115, F.LG, b.color)
        draw_text(surface, b.desc,   cx + 10,  cy + 145, F.SM, GRAY)

        stats = [
            f"HP:  {b.hp}",  f"MP:  {b.mp}",
            f"ATK: {b.atk}", f"DEF: {b.def_}",
            f"SPD: {b.spd}", f"MAG: {b.mag}",
        ]
        for j, s in enumerate(stats):
            draw_text(surface, s, cx + 14, cy + 172 + j * 20, F.SM)

    draw_text(surface, "← → para navegar   |   ENTER para confirmar",
              SCREEN_W // 2 - 240, SCREEN_H - 50, F.SM, GRAY)


# ---------------------------------------------------------------------------
# Telas de Game Over / Vitória / Pausa
# ---------------------------------------------------------------------------
def draw_end_screen(surface: pygame.Surface, won: bool) -> None:
    surface.fill((5, 0, 15) if not won else (5, 20, 5))
    msg = "✨ VITÓRIA! ✨" if won else "💀 GAME OVER"
    sub = "Você derrotou o Lorde das Sombras!" if won else "Tente novamente..."
    draw_text(surface, msg, SCREEN_W // 2 - 200, SCREEN_H // 2 - 80, F.XL,
              YELLOW if won else RED)
    draw_text(surface, sub, SCREEN_W // 2 - 200, SCREEN_H // 2,      F.LG)
    draw_text(surface, "[R] Jogar novamente   |   [ESC] Sair",
              SCREEN_W // 2 - 230, SCREEN_H // 2 + 80, F.MD, GRAY)


def draw_pause(surface: pygame.Surface) -> None:
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    surface.blit(overlay, (0, 0))
    draw_text(surface, "⏸  PAUSADO",
              SCREEN_W // 2 - 100, SCREEN_H // 2 - 60, F.XL, YELLOW)
    draw_text(surface, "[P] Continuar  |  [I] Inventário  |  [ESC] Menu",
              SCREEN_W // 2 - 230, SCREEN_H // 2 + 20, F.MD)


# ---------------------------------------------------------------------------
# Texto flutuante
# ---------------------------------------------------------------------------
class FloatingText:
    def __init__(
        self,
        text    : str,
        x       : int,
        y       : int,
        color         = WHITE,
        duration: int = 90,
    ) -> None:
        self.text     = text
        self.x        = float(x)
        self.y        = float(y)
        self.color    = color
        self.life     = duration
        self.max_life = duration

    def update(self) -> None:
        self.y    -= 0.8
        self.life -= 1

    def draw(self, surface: pygame.Surface) -> None:
        alpha = int(255 * self.life / self.max_life)
        surf  = F.MD.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x), int(self.y)))

    @property
    def alive(self) -> bool:
        return self.life > 0
