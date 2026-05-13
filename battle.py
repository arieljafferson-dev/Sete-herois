# battle.py

from __future__ import annotations

import random
from typing import TYPE_CHECKING, List, Optional, Tuple

from config import *

if TYPE_CHECKING:
    from player import Player
    from enemy  import Enemy

# ---------------------------------------------------------------------------
# Cálculo de dano (função pura — sem efeitos colaterais)
# ---------------------------------------------------------------------------
def calc_damage(
    atk      : int,
    def_     : int,
    *,
    mult     : float = 1.0,
    ignore_def: bool = False,
    crit     : bool  = False,
) -> Tuple[int, bool]:
    """
    Retorna (dano_final, foi_critico).
    A variação aleatória (±15 %) e a chance base de crítico (8 %) são
    aplicadas aqui de forma centralizada.
    """
    effective_def = 0 if ignore_def else def_ // 2
    base          = max(1, atk - effective_def)
    dmg           = int(base * mult * random.uniform(0.85, 1.15))
    is_crit       = crit or (random.random() < 0.08)
    if is_crit:
        dmg = int(dmg * 2.0)
    return dmg, is_crit


# ---------------------------------------------------------------------------
# BattleSystem
# ---------------------------------------------------------------------------
class BattleSystem:
    """
    Gerencia uma batalha por turnos entre Player e Enemy.
    Cada ação pública retorna None (sucesso) ou str (mensagem de erro).
    """

    MAX_LOG = 60

    def __init__(self, player: "Player", enemy: "Enemy") -> None:
        self.player = player
        self.enemy  = enemy
        self.state  = "intro"
        self.log: List[str] = []
        self.xp_gained  = 0
        self.loot_gained: list = []

        self._log(f"⚔  Batalha iniciada contra {enemy.name}!")
        first = "player_turn" if player.spd >= enemy.spd else "enemy_turn"
        self._set_state(first)

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------
    def _log(self, msg: str) -> None:
        self.log.append(msg)
        if len(self.log) > self.MAX_LOG:
            self.log.pop(0)

    def _set_state(self, state: str) -> None:
        self.state = state

    def _check_deaths(self) -> bool:
        """Verifica mortes. Retorna True se a batalha acabou."""
        if self.enemy.hp <= 0:
            self._resolve_victory()
            return True
        if self.player.hp <= 0:
            self._log("💀 Você foi derrotado...")
            self._set_state("defeat")
            return True
        return False

    def _apply_damage_to_enemy(self, dmg: int, is_crit: bool, label: str = "") -> None:
        self.enemy.hp = max(0, self.enemy.hp - dmg)
        suffix = " (CRÍTICO!)" if is_crit else ""
        self._log(f"{label}{dmg} de dano{suffix}.")

    # ------------------------------------------------------------------
    # Turno do jogador — ações públicas
    # ------------------------------------------------------------------
    def player_attack(self) -> None:
        if self.state != "player_turn":
            return
        dmg, crit = calc_damage(self.player.atk, self.enemy.effective_def())
        self._apply_damage_to_enemy(dmg, crit, "Você ataca por ")
        self._end_player_turn()

    def player_skill(self, skill_idx: int) -> Optional[str]:
        """Retorna mensagem de erro ou None em caso de sucesso."""
        if self.state != "player_turn":
            return "Estado inválido."
        if skill_idx >= len(self.player.skills):
            return "Habilidade inválida."

        skill = self.player.skills[skill_idx]
        if self.player.mp < skill.mp_cost:
            return f"MP insuficiente! (precisa {skill.mp_cost})"

        self.player.mp -= skill.mp_cost
        self._execute_skill(skill.name)
        self._end_player_turn()
        return None

    def _execute_skill(self, name: str) -> None:
        """Tabela de despacho de habilidades — substitui o if/elif gigante."""
        p, e = self.player, self.enemy

        handlers = {
            "Golpe Forte":     self._skill_golpe_forte,
            "Defesa Elevada":  self._skill_defesa_elevada,
            "Investida":       self._skill_investida,
            "Bola de Fogo":    self._skill_bola_de_fogo,
            "Cura":            self._skill_cura,
            "Tempestade":      self._skill_tempestade,
            "Ataque Crítico":  self._skill_ataque_critico,
            "Envenenar":       self._skill_envenenar,
            "Sombra Dupla":    self._skill_sombra_dupla,
        }
        handler = handlers.get(name)
        if handler:
            handler()
        else:
            self._log(f"Habilidade desconhecida: {name}")

    # -- Implementações individuais das habilidades ----------------------

    def _skill_golpe_forte(self) -> None:
        p, e = self.player, self.enemy
        dmg, crit = calc_damage(p.atk, e.effective_def() * 0.7, mult=1.8)
        e.hp = max(0, e.hp - dmg)
        self._log(f"Golpe Forte causa {dmg} de dano!" + (" (CRÍTICO!)" if crit else ""))

    def _skill_defesa_elevada(self) -> None:
        self.player.effects["def_up"] = {"turns": 3, "val": 0}
        self._log("Defesa dobrada por 3 turnos!")

    def _skill_investida(self) -> None:
        p, e = self.player, self.enemy
        dmg, _ = calc_damage(p.atk, e.effective_def(), mult=2.5)
        e.hp = max(0, e.hp - dmg)
        p.skip_turn = True
        self._log(f"Investida! {dmg} de dano — você pulará o próximo turno.")

    def _skill_bola_de_fogo(self) -> None:
        p, e = self.player, self.enemy
        dmg, _ = calc_damage(p.mag, e.def_ // 3, mult=2.0, ignore_def=True)
        e.hp = max(0, e.hp - dmg)
        self._log(f"Bola de Fogo! {dmg} de dano mágico!")

    def _skill_cura(self) -> None:
        p = self.player
        healed = int(p.max_hp * 0.4)
        p.hp   = min(p.max_hp, p.hp + healed)
        self._log(f"Cura restaura {healed} HP!")

    def _skill_tempestade(self) -> None:
        p, e = self.player, self.enemy
        dmg, _ = calc_damage(p.mag, 0, mult=3.5, ignore_def=True)
        e.hp   = max(0, e.hp - dmg)
        if random.random() < 0.35:
            e.effects["stun"] = {"turns": 1, "val": 0}
            self._log(f"Tempestade! {dmg} de dano + inimigo atordoado!")
        else:
            self._log(f"Tempestade! {dmg} de dano mágico!")

    def _skill_ataque_critico(self) -> None:
        p, e = self.player, self.enemy
        dmg, _ = calc_damage(p.atk, e.effective_def(), crit=True)
        e.hp   = max(0, e.hp - dmg)
        self._log(f"Ataque Crítico! {dmg} de dano (CRÍTICO GARANTIDO)!")

    def _skill_envenenar(self) -> None:
        self.enemy.effects["poison"] = {"turns": 4, "val": 0.08}
        self._log(f"{self.enemy.name} está envenenado por 4 turnos!")

    def _skill_sombra_dupla(self) -> None:
        p, e = self.player, self.enemy
        dmg1, c1 = calc_damage(p.atk, e.effective_def())
        dmg2, c2 = calc_damage(p.atk, e.effective_def())
        e.hp = max(0, e.hp - dmg1 - dmg2)
        crit_tag = " (CRÍTICO)" if (c1 or c2) else ""
        self._log(f"Sombra Dupla! {dmg1} + {dmg2} de dano{crit_tag}!")

    # ------------------------------------------------------------------
    def player_item(self, inv_idx: int) -> None:
        if self.state != "player_turn":
            return
        msg = self.player.use_item(inv_idx)
        self._log(msg)
        self._end_player_turn()

    def player_flee(self) -> None:
        if self.state != "player_turn":
            return
        chance = min(0.9, 0.3 + (self.player.spd - self.enemy.spd) * 0.04)
        if random.random() < chance:
            self._log("Você fugiu com sucesso!")
            self._set_state("fled")
        else:
            self._log("Fuga falhou!")
            self._end_player_turn()

    def _end_player_turn(self) -> None:
        if self._check_deaths():
            return
        for msg in self.enemy.tick_effects():
            self._log(msg)
        if self._check_deaths():
            return
        self._set_state("enemy_turn")

    # ------------------------------------------------------------------
    # Turno do inimigo
    # ------------------------------------------------------------------
    def enemy_act(self) -> None:
        if self.state != "enemy_turn":
            return
        e, p = self.enemy, self.player

        if "stun" in e.effects:
            del e.effects["stun"]
            self._log(f"{e.name} está atordoado e perde o turno!")
            self._end_enemy_turn()
            return

        action = e.choose_action()
        self._log(action["msg"])
        self._resolve_enemy_action(action)
        self._end_enemy_turn()

    def _resolve_enemy_action(self, action: dict) -> None:
        """Aplica o efeito da ação do inimigo sobre o jogador."""
        t = action["type"]
        p = self.player
        e = self.enemy

        if t == "attack":
            dmg, crit = calc_damage(e.atk, p.effective_def())
            p.hp = max(0, p.hp - dmg)
            self._log(f"  → {dmg} de dano" + (" (CRÍTICO)" if crit else "") + ".")

        elif t == "skill":
            ign = action.get("ignore_def", False)
            dmg, _ = calc_damage(
                e.atk,
                0 if ign else p.effective_def(),
                mult=action.get("mult", 1.5),
            )
            p.hp = max(0, p.hp - dmg)
            self._log(f"  → {dmg} de dano!")

        elif t == "poison":
            p.effects["poison"] = {"turns": 3, "val": 0.08}
            self._log("  → Você foi envenenado!")

        elif t == "buff_def":
            e.def_up = True
            self._log(f"  → {e.name} aumentou sua defesa!")

        elif t == "debuff":
            p.effects["debuff_atk"] = {"turns": 2, "val": 0}
            self._log("  → Sua defesa foi reduzida por 2 turnos!")

    def _end_enemy_turn(self) -> None:
        if self._check_deaths():
            return
        for msg in self.player.tick_effects():
            self._log(msg)
        if self._check_deaths():
            return

        if self.player.skip_turn:
            self.player.skip_turn = False
            self._log("Você recupera o fôlego após a Investida...")
            self._set_state("enemy_turn")
            self.enemy_act()
        else:
            self._set_state("player_turn")

    # ------------------------------------------------------------------
    # Vitória
    # ------------------------------------------------------------------
    def _resolve_victory(self) -> None:
        self._log(f"✨ {self.enemy.name} derrotado!")
        self.xp_gained = self.enemy.xp_reward
        for msg in self.player.gain_xp(self.xp_gained):
            self._log(f"🌟 {msg}")
        self._log(f"+{self.xp_gained} XP")
        self._set_state("victory")

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------
    def recent_log(self, n: int = 8) -> List[str]:
        return self.log[-n:]
