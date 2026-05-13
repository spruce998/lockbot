"""
激进策略（Aggressive）

优先最大化伤害输出，不考虑能量保留。

特点：
- 优先使用最高伤害技能
- 低血量时反而更激进（赌博式输出）
- 不考虑防御/回复
"""
from .base import DecisionStrategy
from ..context import BattleContext, DecisionResult


class AggressiveStrategy(DecisionStrategy):
    def name(self) -> str:
        return "激进策略"

    def decide(self, ctx: BattleContext) -> DecisionResult:
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0
        best_skill = None
        best_score = -float('inf')
        best_reasons = []

        for skill in ctx.my_equipped_skills:
            if skill.energy_cost > energy:
                continue

            # 基础伤害
            type_mult = self._get_type_multiplier(
                skill.element, ctx.enemy_pet.element) if ctx.enemy_pet else 1
            score = skill.power * type_mult

            # 激进加成：高伤害优先
            if skill.power >= 100:
                score *= 1.5
                best_reasons.append("高伤害优先")

            # 迸发加成
            if skill.has_burst:
                burst = self._calc_burst_bonus(skill)
                score += burst
                best_reasons.append("迸发")

            # 低血量反而更激进
            my_hp = ctx.my_pet.hp_percent if ctx.my_pet else 1.0
            if my_hp < 0.3:
                score *= 1.2
                best_reasons.append("低血量赌博")

            if score > best_score:
                best_score = score
                best_skill = skill
                best_reasons = ["激进策略：最大化输出"] + best_reasons

        return DecisionResult(
            skill=best_skill, score=best_score,
            reasons=best_reasons,
            strategy=self.name(),
            confidence=min(1.0, best_score / 150),
        )
