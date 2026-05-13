# player.py

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame
from config import CLASS_BASES, PLAYER_SPEED, GRAVITY, JUMP_FORCE, SKILLS, SkillDef, xp_to_next


class Player:
    def __init__(self, class_name: str) -> None:
        self.class_name = class_name
        b = CLASS_BASES[class_name]

        # Atributos base (imutáveis durante o nível)
        self._base_hp  = b.hp
        self._base_mp  = b.mp
        self._base_atk = b.atk
        self._base_def = b.def_
        self._base_spd = b.spd
        self._base_mag = b.mag

        self.level = 1
        self.xp    = 0

        # Equipamentos (dict compatível com serialização JSON)
        self.weapon: Optional[dict] = None
        self.armor : Optional[dict] = None

        # Stats calculados — recalculate após qualquer mudança de level/equip
        self.max_hp = self.max_mp = 0
        self.atk = self.def_ = self.spd = self.mag = 0
        self._recalc_stats()

        self.hp = self.max_hp
        self.mp = self.max_mp

        # Inventário
        self.inventory: List[dict] = []
        self.max_inv   = 20

        # Habilidades desbloqueadas
        self.skills: List[SkillDef] = self._unlocked_skills()

        # Status effects  {"nome": {"turns": N, "val": V}}
        self.effects: Dict[str, dict] = {}

        # Física de exploração
        self.rect      = pygame.Rect(100, 300, 32, 48)
        self.vel_x     = 0.0
        self.vel_y     = 0.0
        self.on_ground = False
        self.facing    = 1   # 1 = direita, -1 = esquerda
        self.color     = b.color

        # Flags de batalha
        self.skip_turn = False

        # Cache da fonte do símbolo
        self._sym_font = pygame.font.SysFont("Arial", 14, bold=True)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def _recalc_stats(self) -> None:
        """Recalcula todos os stats derivados (level + equipamentos)."""
        lvl = self.level - 1  # incremento acima do nível 1

        self.max_hp = self._base_hp  + lvl * 12
        self.max_mp = self._base_mp  + lvl * 6
        self.atk    = self._base_atk + lvl * 3
        self.def_   = self._base_def + lvl * 2
        self.spd    = self._base_spd + lvl * 1
        self.mag    = self._base_mag + lvl * 3

        _STAT_MAP = {
            "atk": "atk", "def_": "def_", "spd": "spd",
            "mag": "mag", "hp": "max_hp", "mp": "max_mp",
        }
        for eq in (self.weapon, self.armor):
            if eq:
                for stat, val in eq["bonus"].items():
                    attr = _STAT_MAP.get(stat)
                    if attr:
                        setattr(self, attr, getattr(self, attr) + val)

    def _unlocked_skills(self) -> List[SkillDef]:
        return [s for s in SKILLS[self.class_name] if s.unlock <= self.level]

    def effective_def(self) -> int:
        return self.def_ * (2 if "def_up" in self.effects else 1)

    # ------------------------------------------------------------------
    # Equipamentos
    # ------------------------------------------------------------------
    def equip(self, item: dict) -> Tuple[bool, str]:
        if self.class_name not in item.get("classes", [self.class_name]):
            return False, "Classe incompatível."

        prev_max_hp = self.max_hp
        prev_max_mp = self.max_mp

        if item["type"] == "weapon":
            self.weapon = item
        elif item["type"] == "armor":
            self.armor = item
        else:
            return False, "Item não equipável."

        self._recalc_stats()
        # Ajusta HP/MP proporcionalmente ao aumento do máximo
        self.hp = min(self.hp + (self.max_hp - prev_max_hp), self.max_hp)
        self.mp = min(self.mp + (self.max_mp - prev_max_mp), self.max_mp)
        return True, f"Equipou {item['name']}!"

    def unequip(self, slot: str) -> None:
        if slot == "weapon":
            self.weapon = None
        elif slot == "armor":
            self.armor = None
        self._recalc_stats()

    # ------------------------------------------------------------------
    # XP / Level up
    # ------------------------------------------------------------------
    def gain_xp(self, amount: int) -> List[str]:
        self.xp += amount
        messages: List[str] = []

        while self.xp >= xp_to_next(self.level):
            self.xp -= xp_to_next(self.level)
            self.level += 1
            self._recalc_stats()
            self.hp = self.max_hp
            self.mp = self.max_mp

            new_skills = [
                s for s in SKILLS[self.class_name]
                if s.unlock == self.level and s not in self.skills
            ]
            self.skills.extend(new_skills)

            msg = f"Level UP! → Nível {self.level}"
            if new_skills:
                msg += f"  |  Nova habilidade: {new_skills[0].name}"
            messages.append(msg)

        return messages

    # ------------------------------------------------------------------
    # Inventário
    # ------------------------------------------------------------------
    def add_item(self, item: dict) -> Tuple[bool, str]:
        if len(self.inventory) >= self.max_inv:
            return False, "Inventário cheio!"
        self.inventory.append(item)
        return True, f"Obteve: {item['name']}"

    def use_item(self, idx: int) -> str:
        if idx >= len(self.inventory):
            return "Item inválido."
        item = self.inventory[idx]
        if item["type"] != "consumable":
            return "Não é consumível."

        parts = [f"Usou {item['name']}."]
        eff   = item.get("effect", {})

        if "hp" in eff:
            healed = min(eff["hp"], self.max_hp - self.hp)
            self.hp += healed
            parts.append(f"+{healed} HP.")

        if "mp" in eff:
            restored = min(eff["mp"], self.max_mp - self.mp)
            self.mp += restored
            parts.append(f"+{restored} MP.")

        if "cure" in eff:
            status = eff["cure"]
            if status in self.effects:
                del self.effects[status]
                parts.append("Efeito curado.")

        self.inventory.pop(idx)
        return " ".join(parts)

    # ------------------------------------------------------------------
    # Exploração (física)
    # ------------------------------------------------------------------
    def update_exploration(self, keys: pygame.key.ScancodeWrapper, platforms: list) -> None:
        self._handle_input(keys)
        self.vel_y = min(self.vel_y + GRAVITY, 20)
        self._move_and_collide(platforms)

    def _handle_input(self, keys: pygame.key.ScancodeWrapper) -> None:
        self.vel_x = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x  = -PLAYER_SPEED
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x  = PLAYER_SPEED
            self.facing = 1
        if (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]) and self.on_ground:
            self.vel_y     = JUMP_FORCE
            self.on_ground = False

    def _move_and_collide(self, platforms: list) -> None:
        self.on_ground = False

        self.rect.x += int(self.vel_x)
        for p in platforms:
            if p.width == 0:
                continue
            if self.rect.colliderect(p):
                if self.vel_x > 0:
                    self.rect.right = p.left
                else:
                    self.rect.left  = p.right
                self.vel_x = 0.0

        self.rect.y += int(self.vel_y)
        for p in platforms:
            if p.width == 0:
                continue
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.rect.bottom = p.top
                    self.on_ground   = True
                else:
                    self.rect.top = p.bottom
                self.vel_y = 0.0

    def draw_exploration(self, surface: pygame.Surface, cam_x: int) -> None:
        rx, ry = self.rect.x - cam_x, self.rect.y
        pygame.draw.rect(surface, self.color, (rx, ry, self.rect.w, self.rect.h), border_radius=6)
        # Olhinhos
        ex = rx + (20 if self.facing == 1 else 8)
        pygame.draw.circle(surface, (255, 255, 255), (ex, ry + 14), 5)
        pygame.draw.circle(surface, (0, 0, 0),       (ex + self.facing * 2, ry + 15), 2)
        # Símbolo da classe
        from config import CLASS_BASES
        sym = self._sym_font.render(CLASS_BASES[self.class_name].symbol, True, (255, 255, 255))
        surface.blit(sym, (rx + 8, ry + self.rect.h - 20))

    # ------------------------------------------------------------------
    # Status effects
    # ------------------------------------------------------------------
    def tick_effects(self) -> List[str]:
        msgs: List[str] = []
        expired: List[str] = []

        for name, data in self.effects.items():
            if name == "poison":
                dmg = max(1, int(self.max_hp * data["val"]))
                self.hp = max(0, self.hp - dmg)
                msgs.append(f"Veneno causa {dmg} de dano!")
            data["turns"] -= 1
            if data["turns"] <= 0:
                expired.append(name)

        for key in expired:
            del self.effects[key]
            msgs.append(f"Efeito '{key}' acabou.")

        return msgs

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "class_name": self.class_name,
            "level"     : self.level,
            "xp"        : self.xp,
            "hp"        : self.hp,
            "mp"        : self.mp,
            "weapon"    : self.weapon,
            "armor"     : self.armor,
            "inventory" : self.inventory,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Player":
        p           = cls(d["class_name"])
        p.level     = d["level"]
        p.xp        = d["xp"]
        p.weapon    = d["weapon"]
        p.armor     = d["armor"]
        p.inventory = d["inventory"]
        p._recalc_stats()
        p.hp     = d["hp"]
        p.mp     = d["mp"]
        p.skills = p._unlocked_skills()
        return p
