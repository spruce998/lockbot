"""决策策略基类"""
from __future__ import annotations

from abc import ABC, abstractmethod
from ..context import BattleContext, DecisionResult


class DecisionStrategy(ABC):
    """决策策略基类"""

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def decide(self, context: BattleContext) -> DecisionResult:
        pass

    def _get_type_multiplier(self, atk_element: str, def_element: str,
                             def_sub_element: str = None) -> float:
        """
        获取属性克制倍率（支持双属性）

        双属性：倍率相乘
        例：草/虫 vs 火 = 2 × 2 = 4 倍
        """
        from ..database import get_type_multiplier

        mult = get_type_multiplier(atk_element, def_element)

        if def_sub_element:
            sub_mult = get_type_multiplier(atk_element, def_sub_element)
            mult *= sub_mult

        return mult

    def _calc_damage(self, skill, context: BattleContext) -> float:
        """计算期望伤害（简化版）"""
        if not context.enemy_pet:
            return 0

        if skill.category == '物攻':
            atk_stat = context.my_pet.effective_atk if context.my_pet else 100
            def_stat = context.enemy_pet.effective_def
        elif skill.category == '魔攻':
            atk_stat = context.my_pet.effective_spatk if context.my_pet else 100
            def_stat = context.enemy_pet.effective_spdef
        else:
            return 0

        base_dmg = skill.power * (atk_stat / max(def_stat, 1))
        base_dmg *= 0.925  # 随机波动

        # 克制倍率（由调用方单独乘）
        return base_dmg

    def _calc_position_bonus(self, skill, context: BattleContext) -> float:
        """计算位置效果加成"""
        pos = context.my_skill_positions.get(skill.name, 0)
        if pos == 0:
            return 0

        # 离子震荡: 传动
        if skill.name == '离子震荡':
            return 15

        # 啮合传递: 位于 1 号位时能耗 -2，传动
        if skill.name == '啮合传递' and pos == 1:
            return 20

        # 钢铁洪流: 4 号位威力 +80
        if skill.name == '钢铁洪流' and pos == 4:
            return 80

        # 山火: 每使用 1 次其他火系技能威力翻倍（需追踪历史）
        # 吹火: 每次使用后威力永久 +20（需追踪使用次数）

        return 0

    def _calc_burst_bonus(self, skill) -> float:
        """计算迸发加成"""
        if skill.name == '超导':
            return 10  # 能耗 -1
        if skill.name == '电弧':
            return 40  # 威力 +40
        if skill.name == '天旋地转':
            return 30  # 威力 +30
        return 0

    def _calc_counter_value(self, skill, context: BattleContext) -> float:
        """计算应对价值"""
        if not skill.is_counter:
            return 0

        if context.enemy_predicted_skill:
            if context.enemy_predicted_skill.category in ('物攻', '魔攻'):
                return 50
            elif context.enemy_predicted_skill.category == '状态':
                return 30

        return 10

    def _calc_permanent_value(self, skill, context: BattleContext) -> float:
        """计算永久加成价值"""
        if not skill.effect:
            return 0

        # 过曝: 每使用过 1 个其他系别技能威力永久 +30
        if '永久' in skill.effect:
            return 30

        # 吹火: 每次使用后威力永久 +20
        if skill.name == '吹火':
            return 20

        # 山火: 每使用 1 次其他火系技能威力永久翻倍
        if skill.name == '山火':
            return 50

        # 蓄力需要等待 1 回合，惩罚
        if '蓄力' in skill.effect:
            return -20

        return 0
