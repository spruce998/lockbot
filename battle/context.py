"""
战斗上下文 - 包含所有决策需要的信息
基于 BWIKI 洛克王国世界真实数据结构
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
    DOT = "消耗型"            # DOT（灼烧/冻结/中毒）
    COUNTER = "应对型"        # 以应对技能为核心
    BALANCED = "均衡型"
    UNKNOWN = "未知"


class SkillCategory(Enum):
    """技能分类"""
    ATTACK_PHYSICAL = "物攻"
    ATTACK_MAGICAL = "魔攻"
    DEFENSE = "防御"
    STATUS = "状态"


@dataclass
class Skill:
    """技能 - 基于 BWIKI 真实数据结构"""
    id: int
    name: str
    element: str                    # 技能属性（火/水/草/光...）
    damage_type: str                # 物攻/魔攻/防御/状态
    power: int = 0                  # 威力
    energy_cost: int = 0            # 能耗（0-7）
    has_charge: bool = False        # 是否蓄力
    has_burst: bool = False         # 是否有迸发
    has_counter: bool = False       # 是否有应对
    has_transmission: bool = False  # 是否有传动
    position_effect: str = ""       # 位置效果描述
    permanent_effect: str = ""      # 永久效果描述
    effect_description: str = ""    # 效果描述
    unlock_level: int = 0

    @property
    def is_dot(self) -> bool:
        """是否为持续伤害技能"""
        dot_keywords = ["灼烧", "冻结", "中毒"]
        return any(kw in self.effect_description for kw in dot_keywords)

    @property
    def is_heal(self) -> bool:
        """是否为回复生命技能"""
        return "回复" in self.effect_description and ("生命" in self.effect_description or "%" in self.effect_description)

    @property
    def is_energy_recover(self) -> bool:
        """是否为回复能量技能"""
        return "回复" in self.effect_description and "能量" in self.effect_description

    @property
    def is_buff(self) -> bool:
        """是否为增益技能"""
        return any(kw in self.effect_description for kw in ["获得", "+"])

    @property
    def is_debuff(self) -> bool:
        """是否为减益技能"""
        return any(kw in self.effect_description for kw in ["敌方获得", "-"])


@dataclass
class Pet:
    """精灵 - 基于 BWIKI 真实数据结构"""
    id: int
    name: str
    element: str                    # 主属性
    sub_element: Optional[str] = None  # 副属性
    base_stat_total: int = 0
    base_hp: int = 0
    base_atk: int = 0
    base_spatk: int = 0
    base_def: int = 0
    base_spdef: int = 0
    base_spd: int = 0
    trait_name: str = ""
    trait_description: str = ""

    # 运行时状态（非数据库字段）
    current_hp: int = 0
    current_energy: int = 10        # 默认 10 能量
    max_hp: int = 0
    atk_buff: int = 0               # 物攻增益层数
    spatk_buff: int = 0             # 魔攻增益层数
    def_buff: int = 0               # 防御增益层数
    spd_buff: int = 0               # 速度增益层数
    is_charging: bool = False       # 是否在蓄力

    # 战斗中携带的技能（4 个）
    equipped_skills: list = field(default_factory=list)
    skill_positions: dict = field(default_factory=dict)  # {技能名: 位置}

    @property
    def hp_percent(self) -> float:
        if self.max_hp == 0:
            return 1.0
        return self.current_hp / self.max_hp

    @property
    def effective_atk(self) -> int:
        return max(1, self.base_atk * (1 + self.atk_buff * 0.2))

    @property
    def effective_spatk(self) -> int:
        return max(1, self.base_spatk * (1 + self.spatk_buff * 0.2))

    @property
    def effective_def(self) -> int:
        return max(1, self.base_def * (1 + self.def_buff * 0.2))

    @property
    def effective_spdef(self) -> int:
        return max(1, self.base_spdef * (1 + self.def_buff * 0.2))


@dataclass
class DecisionResult:
    """决策结果"""
    skill: Optional[Skill]
    score: float
    reasons: list = field(default_factory=list)
    strategy: str = ""
    confidence: float = 0.0
    enemy_prediction: Optional[Skill] = None
    enemy_predicted_action: str = ""

    @property
    def summary(self) -> str:
        if not self.skill:
            return "无可用技能"
        reason_str = " | ".join(self.reasons[:3])
        return f"推荐: {self.skill.name} (能耗{self.skill.energy_cost}, {reason_str})"


@dataclass
class BattleContext:
    """
    战斗上下文 - 每回合决策所需的全部信息

    数据来源：
    - 图像识别：我方/敌方精灵名、血量、能量、技能栏
    - 数据库（BWIKI）：精灵属性、种族值、技能列表、克制关系
    - 战斗历史：敌方已使用技能记录
    """
    # === 我方状态 ===
    my_pet: Optional[Pet] = None
    my_equipped_skills: list = field(default_factory=list)       # 我方 4 个技能
    my_skill_positions: dict = field(default_factory=dict)       # {技能名: 位置(1-4)}

    # === 敌方状态 ===
    enemy_pet: Optional[Pet] = None
    enemy_hp_percent: float = 1.0                                # 敌方血量百分比
    enemy_energy: int = 10                                       # 推测敌方能量

    # === 敌方技能推测 ===
    enemy_confirmed_skills: list = field(default_factory=list)   # 已确认携带的技能
    enemy_remaining_candidates: list = field(default_factory=list)  # 剩余候选
    enemy_position: Position = Position.UNKNOWN                  # 敌方定位
    enemy_predicted_skill: Optional[Skill] = None                # 预测敌方下回合技能
    enemy_prediction_confidence: float = 0.0

    # === 战斗历史 ===
    battle_log: list = field(default_factory=list)               # [(turn, who, skill_name), ...]
    turn_number: int = 0
    my_last_skill: str = ""
    enemy_last_skill: str = ""
    enemy_skill_history: list = field(default_factory=list)      # [(skill_name, turn), ...]

    # === 环境 ===
    weather: str = ""
    field_effect: str = ""

    # === 时间 ===
    timestamp: datetime = field(default_factory=datetime.now)

    def update_enemy_skill(self, skill_name: str):
        """更新敌方使用技能记录"""
        self.enemy_skill_history.append((skill_name, self.turn_number))
        self.enemy_last_skill = skill_name

        # 确认这是敌方携带的技能
        confirmed_names = {s.name for s in self.enemy_confirmed_skills}
        if skill_name not in confirmed_names:
            # 从数据库查找该技能
            from .database import get_skill_by_name
            skill = get_skill_by_name(skill_name)
            if skill:
                self.enemy_confirmed_skills.append(skill)

    def get_enemy_skill_usage_count(self, skill_name: str) -> int:
        """获取敌方技能使用次数"""
        return sum(1 for s, _ in self.enemy_skill_history if s == skill_name)
