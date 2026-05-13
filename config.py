# config.py — Configurações e constantes globais

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Tuple

import pygame

# ---------------------------------------------------------------------------
# Tela
# ---------------------------------------------------------------------------
SCREEN_W, SCREEN_H = 960, 540
FPS                 = 60
TITLE               = "Chronicles of Pyxel"

# ---------------------------------------------------------------------------
# Cores (tuplas nomeadas para evitar magic numbers espalhados)
# ---------------------------------------------------------------------------
Color = Tuple[int, int, int]

BLACK   : Color = (0,   0,   0)
WHITE   : Color = (255, 255, 255)
GRAY    : Color = (120, 120, 120)
DGRAY   : Color = (40,  40,  40)
RED     : Color = (220, 50,  50)
GREEN   : Color = (60,  200, 80)
BLUE    : Color = (60,  120, 220)
YELLOW  : Color = (255, 220, 0)
ORANGE  : Color = (255, 150, 30)
PURPLE  : Color = (170, 60,  220)
CYAN    : Color = (60,  220, 220)
PINK    : Color = (255, 100, 180)
BROWN   : Color = (140, 90,  40)
DKGREEN : Color = (30,  100, 40)

RARITY_COLOR: Dict[str, Color] = {
    "comum": WHITE,
    "raro":  BLUE,
    "épico": PURPLE,
}

# ---------------------------------------------------------------------------
# Física / mapa
# ---------------------------------------------------------------------------
GRAVITY      = 0.55
JUMP_FORCE   = -13
PLAYER_SPEED = 4
TILE_SIZE    = 48

# ---------------------------------------------------------------------------
# Estados do jogo (enum elimina strings mágicas e permite autocomplete)
# ---------------------------------------------------------------------------
class GameState(Enum):
    CLASS_SELECT = auto()
    EXPLORE      = auto()
    BATTLE       = auto()
    INVENTORY    = auto()
    PAUSED       = auto()
    END          = auto()

# ---------------------------------------------------------------------------
# Temas das fases
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PhaseTheme:
    name    : str
    bg      : Color
    platform: Color
    sky     : Color

PHASE_THEMES: Dict[int, PhaseTheme] = {
    1: PhaseTheme("Floresta",    (60,  120, 60),  (80,  160, 80),  (100, 180, 255)),
    2: PhaseTheme("Caverna",     (50,  45,  40),  (90,  80,  70),  (30,  30,  50)),
    3: PhaseTheme("Castelo",     (70,  70,  90),  (110, 110, 130), (60,  60,  100)),
    4: PhaseTheme("Deserto",     (200, 170, 80),  (210, 190, 110), (255, 210, 120)),
    5: PhaseTheme("Mundo Final", (80,  20,  20),  (140, 40,  40),  (20,  0,   30)),
}

# ---------------------------------------------------------------------------
# XP
# ---------------------------------------------------------------------------
def xp_to_next(level: int) -> int:
    return int(80 * (level ** 1.4))

# ---------------------------------------------------------------------------
# Classes de personagem
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ClassBase:
    hp    : int
    mp    : int
    atk   : int
    def_  : int
    spd   : int
    mag   : int
    color : Color
    symbol: str
    desc  : str

CLASS_BASES: Dict[str, ClassBase] = {
    "Guerreiro": ClassBase(
        hp=120, mp=30,  atk=18, def_=14, spd=8,  mag=4,
        color=(200, 80, 60), symbol="⚔",
        desc="Alta vida e defesa. Tanque das batalhas.",
    ),
    "Mago": ClassBase(
        hp=70,  mp=100, atk=6,  def_=6,  spd=9,  mag=22,
        color=(100, 120, 240), symbol="✦",
        desc="Alto dano mágico. Frágil mas devastador.",
    ),
    "Assassino": ClassBase(
        hp=90,  mp=50,  atk=14, def_=8,  spd=16, mag=6,
        color=(60, 200, 140), symbol="🗡",
        desc="Alta velocidade e chance de crítico.",
    ),
}

# ---------------------------------------------------------------------------
# Habilidades
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SkillDef:
    name    : str
    mp_cost : int
    unlock  : int   # nível mínimo para desbloquear
    desc    : str

SKILLS: Dict[str, Tuple[SkillDef, ...]] = {
    "Guerreiro": (
        SkillDef("Golpe Forte",    8,  1, "Dano físico x1.8, ignora 30% da defesa."),
        SkillDef("Defesa Elevada", 10, 3, "Dobra a defesa por 3 turnos."),
        SkillDef("Investida",      15, 6, "Dano x2.5 mas pula próximo turno."),
    ),
    "Mago": (
        SkillDef("Bola de Fogo",  12, 1, "Dano mágico x2.0."),
        SkillDef("Cura",          15, 2, "Restaura 40% do HP máximo."),
        SkillDef("Tempestade",    25, 5, "Dano mágico x3.5, chance de atordoar."),
    ),
    "Assassino": (
        SkillDef("Ataque Crítico", 10, 1, "Garante crítico (x2.5 dano)."),
        SkillDef("Envenenar",       8, 2, "Aplica veneno: 8% do HP/turno por 4 turnos."),
        SkillDef("Sombra Dupla",   18, 5, "Ataca duas vezes no mesmo turno."),
    ),
}

# ---------------------------------------------------------------------------
# Itens
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ItemDef:
    id     : str
    name   : str
    type   : str          # "consumable" | "weapon" | "armor"
    rarity : str          # "comum" | "raro" | "épico"
    desc   : str
    effect : Dict         = field(default_factory=dict)
    bonus  : Dict         = field(default_factory=dict)
    classes: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        """Compatibilidade com código legado que usa dicts."""
        return {
            "id": self.id, "name": self.name, "type": self.type,
            "rarity": self.rarity, "desc": self.desc,
            "effect": self.effect, "bonus": self.bonus,
            "classes": list(self.classes),
        }

ITEM_TABLE: Tuple[ItemDef, ...] = (
    # consumíveis
    ItemDef("potion_s", "Poção Pequena",  "consumable", "comum", "Recupera 40 HP.",   effect={"hp": 40}),
    ItemDef("potion_m", "Poção Média",    "consumable", "raro",  "Recupera 100 HP.",  effect={"hp": 100}),
    ItemDef("ether_s",  "Éter Pequeno",   "consumable", "comum", "Recupera 30 MP.",   effect={"mp": 30}),
    ItemDef("antidote", "Antídoto",       "consumable", "comum", "Cura veneno.",       effect={"cure": "poison"}),
    # armas — Guerreiro
    ItemDef("sword_1", "Espada de Ferro",  "weapon", "comum", "+8 ATK",          bonus={"atk": 8},        classes=("Guerreiro",)),
    ItemDef("sword_2", "Espada Prateada",  "weapon", "raro",  "+18 ATK +4 DEF",  bonus={"atk": 18, "def_": 4},  classes=("Guerreiro",)),
    ItemDef("sword_3", "Lâmina Épica",     "weapon", "épico", "+32 ATK +8 DEF",  bonus={"atk": 32, "def_": 8},  classes=("Guerreiro",)),
    # armas — Mago
    ItemDef("staff_1", "Cajado de Madeira","weapon", "comum", "+10 MAG",         bonus={"mag": 10},       classes=("Mago",)),
    ItemDef("staff_2", "Cajado Arcano",    "weapon", "raro",  "+22 MAG +20 MP",  bonus={"mag": 22, "mp": 20},   classes=("Mago",)),
    ItemDef("staff_3", "Orbe do Caos",     "weapon", "épico", "+38 MAG +40 MP",  bonus={"mag": 38, "mp": 40},   classes=("Mago",)),
    # armas — Assassino
    ItemDef("dagger_1","Faca Enferrujada", "weapon", "comum", "+6 ATK +2 SPD",   bonus={"atk": 6,  "spd": 2},  classes=("Assassino",)),
    ItemDef("dagger_2","Adaga Venenosa",   "weapon", "raro",  "+14 ATK +4 SPD",  bonus={"atk": 14, "spd": 4},  classes=("Assassino",)),
    ItemDef("dagger_3","Lâmina Sombria",   "weapon", "épico", "+26 ATK +8 SPD",  bonus={"atk": 26, "spd": 8},  classes=("Assassino",)),
    # armaduras
    ItemDef("armor_1", "Couro Simples",   "armor", "comum", "+6 DEF",            bonus={"def_": 6},       classes=("Guerreiro","Assassino")),
    ItemDef("armor_2", "Cota de Malha",   "armor", "raro",  "+16 DEF +20 HP",    bonus={"def_": 16, "hp": 20}, classes=("Guerreiro",)),
    ItemDef("armor_3", "Armadura Épica",  "armor", "épico", "+28 DEF +40 HP",    bonus={"def_": 28, "hp": 40}, classes=("Guerreiro",)),
    ItemDef("robe_1",  "Manto Simples",   "armor", "comum", "+4 MAG +15 MP",     bonus={"mag": 4,  "mp": 15},  classes=("Mago",)),
    ItemDef("robe_2",  "Manto Arcano",    "armor", "raro",  "+10 MAG +30 MP",    bonus={"mag": 10, "mp": 30},  classes=("Mago",)),
    ItemDef("cloak_1", "Capa das Sombras","armor", "raro",  "+5 SPD +8 DEF",     bonus={"spd": 5,  "def_": 8}, classes=("Assassino",)),
)

# Índice rápido por id — O(1) em vez de iterar a tupla toda vez
ITEM_BY_ID: Dict[str, ItemDef] = {item.id: item for item in ITEM_TABLE}
