# main.py — Chronicles of Pyxel

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import List, Optional

import pygame

from battle import BattleSystem
from config import (
    CLASS_BASES, CYAN, FPS, GameState, GREEN, RARITY_COLOR,
    RED, SCREEN_H, SCREEN_W, TILE_SIZE, TITLE, WHITE, YELLOW,
)
from enemy import Enemy
from map import Phase
from player import Player
from ui import (
    FloatingText,
    draw_battle, draw_class_select, draw_end_screen,
    draw_exploration_hud, draw_inv_menu, draw_pause,
    draw_skill_menu,
)

# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------
SAVE_FILE = "save.json"


def save_game(player: Player, phase_num: int) -> None:
    data = {"phase": phase_num, "player": player.to_dict()}
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("[SAVE] Jogo salvo.")


def load_game() -> tuple[Optional[Player], Optional[int]]:
    if not os.path.exists(SAVE_FILE):
        return None, None
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return Player.from_dict(data["player"]), data["phase"]


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------
class Game:
    def __init__(self) -> None:
        self.state: GameState = GameState.CLASS_SELECT

        self.player      : Optional[Player]      = None
        self.phase_num   : int                   = 1
        self.phase       : Optional[Phase]       = None
        self.battle      : Optional[BattleSystem]= None
        self.active_enemy: Optional[Enemy]       = None
        self.cam_x       : int                   = 0

        # UI state
        self.class_cursor = 0
        self.sel_menu     = 0
        self.inv_cursor   = 0
        self.skill_open   = False
        self.floating     : List[FloatingText] = []

        # Flag de vitória/derrota para a tela final
        self.won = False

    # ------------------------------------------------------------------
    # Fase
    # ------------------------------------------------------------------
    def _start_phase(self, num: int) -> None:
        self.phase_num   = num
        self.phase       = Phase(num)
        ground_y         = SCREEN_H - TILE_SIZE
        self.player.rect.x = 80
        self.player.rect.y = ground_y - self.player.rect.h
        self.cam_x         = 0
        self.state         = GameState.EXPLORE

    # ------------------------------------------------------------------
    # Loop público
    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Chamado a cada frame pelo loop principal."""
        self._handle_events()
        self._update()
        self._draw()

    # ------------------------------------------------------------------
    # Eventos — roteados por estado
    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                self._dispatch_key(ev.key)

    def _dispatch_key(self, key: int) -> None:
        handlers = {
            GameState.CLASS_SELECT: self._key_class_select,
            GameState.EXPLORE:      self._key_explore,
            GameState.BATTLE:       self._key_battle,
            GameState.INVENTORY:    self._key_inventory,
            GameState.PAUSED:       self._key_paused,
            GameState.END:          self._key_end,
        }
        handler = handlers.get(self.state)
        if handler:
            handler(key)

    def _key_class_select(self, key: int) -> None:
        n = len(CLASS_BASES)
        if key in (pygame.K_LEFT,  pygame.K_a):
            self.class_cursor = (self.class_cursor - 1) % n
        if key in (pygame.K_RIGHT, pygame.K_d):
            self.class_cursor = (self.class_cursor + 1) % n
        if key == pygame.K_RETURN:
            cname = list(CLASS_BASES.keys())[self.class_cursor]
            saved_player, saved_phase = load_game()
            if saved_player and saved_player.class_name == cname:
                self.player    = saved_player
                self.phase_num = saved_phase
            else:
                self.player = Player(cname)
            self._start_phase(self.phase_num)

    def _key_explore(self, key: int) -> None:
        if key == pygame.K_p:
            self.state = GameState.PAUSED
        if key == pygame.K_i:
            self._open_inventory()

    def _key_battle(self, key: int) -> None:
        if self.skill_open:
            if key == pygame.K_ESCAPE:
                self.skill_open = False
                return
            for i in range(len(self.player.skills)):
                if key == pygame.K_1 + i:
                    err = self.battle.player_skill(i)
                    if err:
                        self._float(err, RED)
                    self.skill_open = False
                    self._post_player_action()
                    return
            return

        if key == pygame.K_a: self._battle_attack()
        if key == pygame.K_h: self.skill_open = True
        if key == pygame.K_i: self._open_inventory()
        if key == pygame.K_f: self._battle_flee()

    def _key_inventory(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.state = GameState.BATTLE if self.battle else GameState.EXPLORE
        if key == pygame.K_UP:
            self.inv_cursor = max(0, self.inv_cursor - 1)
        if key == pygame.K_DOWN:
            self.inv_cursor = min(len(self.player.inventory) - 1, self.inv_cursor + 1)
        if key == pygame.K_e:
            self._use_or_equip(self.inv_cursor)

    def _key_paused(self, key: int) -> None:
        if key in (pygame.K_p, pygame.K_ESCAPE):
            self.state = GameState.EXPLORE
        if key == pygame.K_i:
            self._open_inventory()
        if key == pygame.K_s:
            save_game(self.player, self.phase_num)
            self._float("Jogo salvo!", CYAN)

    def _key_end(self, key: int) -> None:
        if key == pygame.K_r:
            self.__init__()
        if key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

    # ------------------------------------------------------------------
    # Ações de batalha
    # ------------------------------------------------------------------
    def _battle_attack(self) -> None:
        self.battle.player_attack()
        self._post_player_action()

    def _battle_flee(self) -> None:
        self.battle.player_flee()
        self._check_battle_end()

    def _post_player_action(self) -> None:
        self._check_battle_end()
        if self.state == GameState.BATTLE and self.battle.state == "enemy_turn":
            self.battle.enemy_act()
            self._check_battle_end()

    def _check_battle_end(self) -> None:
        if not self.battle:
            return
        s = self.battle.state

        if s == "victory":
            self._float(f"+{self.battle.xp_gained} XP", YELLOW, SCREEN_W // 2, SCREEN_H // 2)
            if self.active_enemy:
                self.active_enemy.active = False
            if self.active_enemy and self.active_enemy.is_boss and self.phase_num == 5:
                self._end_game(won=True)
                return
            self.battle       = None
            self.active_enemy = None
            self.state        = GameState.EXPLORE

        elif s == "defeat":
            self._end_game(won=False)

        elif s == "fled":
            self.battle       = None
            self.active_enemy = None
            self.state        = GameState.EXPLORE

    def _end_game(self, *, won: bool) -> None:
        self.won   = won
        self.state = GameState.END

    # ------------------------------------------------------------------
    # Inventário
    # ------------------------------------------------------------------
    def _open_inventory(self) -> None:
        self.inv_cursor = 0
        self.state      = GameState.INVENTORY

    def _use_or_equip(self, idx: int) -> None:
        if idx >= len(self.player.inventory):
            return
        item = self.player.inventory[idx]
        if item["type"] == "consumable":
            self._float(self.player.use_item(idx), GREEN)
        else:
            ok, msg = self.player.equip(item)
            if ok:
                self.player.inventory.pop(idx)
                self.inv_cursor = max(0, self.inv_cursor - 1)
            self._float(msg, CYAN if ok else RED)

    # ------------------------------------------------------------------
    # Texto flutuante
    # ------------------------------------------------------------------
    def _float(
        self,
        text : str,
        color       = WHITE,
        x    : Optional[int] = None,
        y    : Optional[int] = None,
    ) -> None:
        self.floating.append(
            FloatingText(text, x or 30, y or SCREEN_H - 280, color)
        )

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def _update(self) -> None:
        # Atualiza e limpa textos flutuantes
        for ft in self.floating:
            ft.update()
        self.floating = [ft for ft in self.floating if ft.alive]

        if self.state == GameState.EXPLORE:
            self._update_explore()

    def _update_explore(self) -> None:
        keys     = pygame.key.get_pressed()
        self.player.update_exploration(keys, self.phase.platforms)
        self.cam_x = self.phase.clamp_camera(self.player.rect)

        # Queda em buraco
        if self.player.rect.y > SCREEN_H + 100:
            self.player.hp -= 20
            ground_y = SCREEN_H - TILE_SIZE
            self.player.rect.x = max(80, self.player.rect.x - 200)
            self.player.rect.y = ground_y - self.player.rect.h
            self._float("-20 HP (buraco!)", RED)
            if self.player.hp <= 0:
                self._end_game(won=False)
            return

        # Colisão com inimigo
        enemy = self.phase.check_enemy_collision(self.player.rect)
        if enemy:
            self.active_enemy = enemy
            self.battle       = BattleSystem(self.player, enemy)
            self.sel_menu     = 0
            self.state        = GameState.BATTLE
            return

        # Baús
        for item in self.phase.check_chest_collision(self.player.rect):
            self.player.add_item(item)
            self._float(f"Obteve: {item['name']}", RARITY_COLOR.get(item["rarity"], WHITE))

        # Saída da fase
        if self.phase.check_goal(self.player.rect):
            if self.phase_num < 5:
                save_game(self.player, self.phase_num + 1)
                self._start_phase(self.phase_num + 1)
            else:
                self._end_game(won=True)

    # ------------------------------------------------------------------
    # Draw — roteado por estado
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        draw_fns = {
            GameState.CLASS_SELECT: self._draw_class_select,
            GameState.EXPLORE:      self._draw_explore,
            GameState.PAUSED:       self._draw_paused,
            GameState.BATTLE:       self._draw_battle,
            GameState.INVENTORY:    self._draw_inventory,
            GameState.END:          self._draw_end,
        }
        fn = draw_fns.get(self.state)
        if fn:
            fn()
        pygame.display.flip()

    def _draw_class_select(self) -> None:
        draw_class_select(screen, self.class_cursor)

    def _draw_explore(self) -> None:
        self.phase.draw(screen, self.cam_x)
        self.player.draw_exploration(screen, self.cam_x)
        draw_exploration_hud(screen, self.player, self.phase_num, self.phase.theme.name)
        for ft in self.floating:
            ft.draw(screen)

    def _draw_paused(self) -> None:
        self._draw_explore()
        draw_pause(screen)

    def _draw_battle(self) -> None:
        draw_battle(screen, self.player, self.active_enemy, self.battle, self.sel_menu)
        if self.skill_open:
            draw_skill_menu(screen, self.player)
        for ft in self.floating:
            ft.draw(screen)

    def _draw_inventory(self) -> None:
        if self.battle:
            draw_battle(screen, self.player, self.active_enemy, self.battle, self.sel_menu)
        else:
            self.phase.draw(screen, self.cam_x)
        draw_inv_menu(screen, self.player, self.inv_cursor)

    def _draw_end(self) -> None:
        draw_end_screen(screen, self.won)


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption(TITLE)
clock  = pygame.time.Clock()


async def main() -> None:
    game = Game()
    while True:
        await asyncio.sleep(0)   # cede controle ao browser (Pygbag)
        game.tick()
        clock.tick(FPS)


asyncio.run(main())
