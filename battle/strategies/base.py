"""决策策略基类"""
from __future__ import annotations

from abc import ABC, abstractmethod
from ..context import BattleContext, DecisionResult


class DecisionStrategy(ABC):
    """
    决策策略基类

    所有决策算法必须继承此类，实现 decide 方法。
    支持运行时切换策略。
    """

    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @abstractmethod
    def decide(self, context: BattleContext) -> DecisionResult:
        """
        做出决策

        :param context: 战斗上下文（包含所有状态信息）
        :return: 决策结果（推荐技能 + 原因 + 置信度）
        """
        pass

    def _get_type_multiplier(self, atk_element: str, def_element: str) -> float:
        """
        获取属性克制倍率

        :param atk_element: 攻击方属性
        :param def_element: 防御方属性
        :return: 倍率（2.0=克制, 0.5=抵抗, 0.0=无效, 1.0=正常）
        """
        from ..database import get_type_multiplier
        return get_type_multiplier(atk_element, def_element)

    def _calc_damage(self, skill, context: BattleContext) -> float:
        """
        计算期望伤害（简化版）

        公式：伤害 = 威力 × (攻击方攻击 / 防御方防御) × 克制倍率 × 0.925
        """
        if not context.enemy_pet:
            return 0

        if skill.damage_type == '物攻':
            atk_stat = context.my_pet.effective_atk if context.my_pet else 100
            def_stat = context.enemy_pet.effective_def
        elif skill.damage_type == '魔攻':
            atk_stat = context.my_pet.effective_spatk if context.my_pet else 100
            def_stat = context.enemy_pet.effective_spdef
        else:
            return 0

        base_dmg = skill.power * (atk_stat / max(def_stat, 1))
        base_dmg *= 0.925  # 随机波动

        # 克制倍率
        type_mult = self._get_type_multiplier(skill.element, context.enemy_pet.element)
        base_dmg *= type_mult

        return base_dmg

    def _calc_position_bonus(self, skill, context: BattleContext) -> float:
        """计算位置效果加成"""
        pos = context.my_skill_positions.get(skill.name, 0)
        if pos == 0:
            return 0

        # 离子震荡: 3号位威力+40
        if skill.name == '离子震荡' and pos == 3:
            return 40

        # 械斗: 1号位威力+60
        if skill.name == '械斗' and pos == 1:
            return 60

        # 啮合传递: 1号或3号位物攻+60%
        if skill.name == '啮合传递' and pos in (1, 3):
            atk = context.my_pet.effective_atk if context.my_pet else 100
            return atk * 0.6

        return 0

    def _calc_burst_bonus(self, skill) -> float:
        """计算迸发加成"""
        if skill.name == '超导':
            return 10  # 能耗-1 的价值
        if skill.name == '电弧':
            return 40  # 威力+40
        if skill.name == '天旋地转':
            return 30  # 威力+30
        return 0

    def _calc_counter_value(self, skill, context: BattleContext) -> float:
        """计算应对价值"""
        if not skill.has_counter:
            return 0

        # 预测敌方攻击 → 应对技能价值高
        if context.enemy_predicted_skill:
            if context.enemy_predicted_skill.damage_type in ('物攻', '魔攻'):
                return 50
            elif context.enemy_predicted_skill.damage_type == '状态':
                return 30

        return 10

    def _calc_permanent_value(self, skill, context: BattleContext) -> float:
        """计算永久加成价值"""
        if not skill.permanent_effect and not skill.has_charge:
            return 0

        # 过曝/吹火等永久叠加技能
        if '永久' in skill.effect_description or '永久' in skill.permanent_effect:
            return 30

        # 蓄力技能需要等待 1 回合，惩罚
        if skill.has_charge:
            return -20

        return 0
