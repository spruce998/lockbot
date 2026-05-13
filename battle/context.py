"""
战斗上下文 - 基于洛克王国世界真实游戏规则
数据源：BWIKI + GitHub (TsingShui/roco-world-skill)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Position(Enum):
    """敌方精灵战斗定位"""
    AGGRESSIVE = "爆发型"     # 高能耗高伤害为主
    DEFENSIVE = "防守型"      # 应对/防御技能为主
    CONTROL = "控制型"        # 减益/状态技能为主
    DOT = "消耗型"            # DOT（灼烧/冻结/中毒/寄生）
    COUNTER = "应对型"        # 以应对技能为核心
    BALANCED = "均衡型"
    UNKNOWN = "未知"


class SkillCategory(Enum):
    """技能分类（真实游戏）"""
    ATTACK_PHYSICAL = "物攻"
    ATTACK_MAGICAL = "魔攻"
    DEFENSE = "防御"
    STATUS = "状态"


# 19 种属性（包含"无"）
ELEMENTS = [
    "普通", "草", "火", "水", "光", "地", "冰", "龙", "电",
    "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻", "无"
]


@dataclass
class Skill:
    """技能 - 基于 BWIKI + GitHub 真实数据"""
    id: int = 0
    name: str = ""
    element: str = ""                    # 技能属性（19 种之一）
    category: str = ""                   # 物攻/魔攻/防御/状态
    cost: int = 0                        # 能耗（0-10+）
    power: int = 0                       # 威力
    effect: str = ""                     # 效果描述

    # 解析出的特性
    has_charge: bool = False             # 蓄力
    has_burst: bool = False              # 迸发
    has_counter: bool = False            # 应对
    has_transmission: bool = False       # 传动
    has_combo: bool = False              # 连击
    combo_count: int = 0                 # 连击数
    has_return: bool = False             # 折返/脱离/返场
    has_priority: bool = False           # 先手+X
    priority_value: int = 0              # 先手值

    @property
    def is_dot(self) -> bool:
        return any(kw in self.effect for kw in ["灼烧", "冻结", "中毒", "寄生"])

    @property
    def is_heal(self) -> bool:
        return "回复" in self.effect and ("生命" in self.effect or "%" in self.effect)

    @property
    def is_energy_recover(self) -> bool:
        return "回复" in self.effect and "能量" in self.effect

    @property
    def is_buff(self) -> bool:
        return "自己获得" in self.effect or "+" in self.effect

    @property
    def is_debuff(self) -> bool:
        return "敌方获得" in self.effect or "-" in self.effect

    @property
    def is_counter(self) -> bool:
        return "应对" in self.effect

    @property
    def energy_recovery(self) -> int:
        """获取技能回复的能量值"""
        import re
        match = re.search(r'回复\s*(\d+)\s*能量', self.effect)
        if match:
            return int(match.group(1))
        return 0


@dataclass
class Pet:
    """精灵 - 基于 BWIKI 真实数据"""
    id: int = 0
    name: str = ""
    element: str = ""                    # 主属性
    sub_element: Optional[str] = None    # 副属性
    base_stat_total: int = 0
    base_hp: int = 0
    base_atk: int = 0                    # 物攻
    base_spatk: int = 0                  # 特攻
    base_def: int = 0                    # 物防
    base_spdef: int = 0                  # 特防
    base_spd: int = 0                    # 速度
    trait_name: str = ""
    trait_description: str = ""
    personality: str = ""                # 性格

    # 运行时状态
    current_hp: int = 0
    max_hp: int = 0
    current_energy: int = 10             # 默认 10 能量
    max_energy: int = 10                 # 能量上限（可被特性突破）
    is_first_appearance: bool = True     # 是否首次出场（影响初始能量）

    # Buff/Debuff 层数
    atk_buff: int = 0
    spatk_buff: int = 0
    def_buff: int = 0
    spdef_buff: int = 0
    spd_buff: int = 0

    # 印记
    positive_marks: dict = field(default_factory=dict)   # {印记名: 层数}
    negative_marks: dict = field(default_factory=dict)   # {负面名: 层数}

    # 战斗中携带的技能（4 个）
    equipped_skills: list = field(default_factory=list)
    skill_positions: dict = field(default_factory=dict)  # {技能名: 位置(1-4)}

    @property
    def hp_percent(self) -> float:
        if self.max_hp == 0:
            return 1.0
        return self.current_hp / self.max_hp

    @property
    def effective_atk(self) -> int:
        return max(1, int(self.base_atk * (1 + self.atk_buff * 0.1)))

    @property
    def effective_spatk(self) -> int:
        return max(1, int(self.base_spatk * (1 + self.spatk_buff * 0.1)))

    @property
    def effective_def(self) -> int:
        return max(1, int(self.base_def * (1 + self.def_buff * 0.1)))

    @property
    def effective_spdef(self) -> int:
        return max(1, int(self.base_spdef * (1 + self.spdef_buff * 0.1)))

    @property
    def effective_spd(self) -> int:
        return max(1, int(self.base_spd * (1 + self.spd_buff * 0.1)))


@dataclass
class DecisionResult:
    """决策结果"""
    skill: Optional[Skill]
    score: float
    reasons: list = field(default_factory=list)
    strategy: str = ""
    confidence: float = 0.0
    enemy_prediction: Optional[Skill] = None

    @property
    def summary(self) -> str:
        if not self.skill:
            return "无可用技能"
        reason_str = " | ".join(self.reasons[:3])
        return f"推荐: {self.skill.name} (能耗{self.skill.cost}, {reason_str})"


@dataclass
class BattleContext:
    """
    战斗上下文 - 每回合决策所需的全部信息

    关键游戏规则：
    - 能量不会每回合自然恢复
    - 使用聚能回复 5 能量（状态技能，可被打断）
    - 先后手 = 先手值 > 速度
    - 双属性克制倍率相乘
    - 每只精灵携带 4 个技能
    """
    # === 我方状态 ===
    my_pet: Optional[Pet] = None
    my_equipped_skills: list = field(default_factory=list)
    my_skill_positions: dict = field(default_factory=dict)

    # === 敌方状态 ===
    enemy_pet: Optional[Pet] = None
    enemy_hp_percent: float = 1.0
    enemy_energy: int = 10

    # === 敌方技能推测 ===
    enemy_confirmed_skills: list = field(default_factory=list)
    enemy_remaining_candidates: list = field(default_factory=list)
    enemy_position: Position = Position.UNKNOWN
    enemy_predicted_skill: Optional[Skill] = None
    enemy_prediction_confidence: float = 0.0

    # === 战斗历史 ===
    battle_log: list = field(default_factory=list)
    turn_number: int = 0
    my_last_skill: str = ""
    enemy_last_skill: str = ""
    enemy_skill_history: list = field(default_factory=list)

    # === 环境 ===
    weather: str = ""               # 下雨/沙暴/暴风雪
    field_effect: str = ""
    marks: dict = field(default_factory=dict)    # {印记名: (层数, 所属方)}

    # === 时间 ===
    timestamp: datetime = field(default_factory=datetime.now)

    def update_enemy_skill(self, skill_name: str):
        """更新敌方使用技能记录"""
        self.enemy_skill_history.append((skill_name, self.turn_number))
        self.enemy_last_skill = skill_name

        confirmed_names = {s.name for s in self.enemy_confirmed_skills}
        if skill_name not in confirmed_names:
            from .database import get_skill_by_name
            skill = get_skill_by_name(skill_name)
            if skill:
                self.enemy_confirmed_skills.append(skill)

    def get_enemy_skill_usage_count(self, skill_name: str) -> int:
        return sum(1 for s, _ in self.enemy_skill_history if s == skill_name)
