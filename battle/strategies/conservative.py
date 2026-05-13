"""
保守策略（Conservative）

优先保证存活，次优输出。

特点：
- 血量低于 50% 时优先防御/回复
- 优先使用低能耗技能保持灵活性
- 只有在优势明显时才使用高能耗技能
"""
from .base import DecisionStrategy
from .greedy import GreedyStrategy
from ..context import BattleContext, DecisionResult


class ConservativeStrategy(DecisionStrategy):
    def name(self) -> str:
        return "保守策略"

    def decide(self, ctx: BattleContext) -> DecisionResult:
        my_hp = ctx.my_pet.hp_percent if ctx.my_pet else 1.0

        if my_hp < 0.3:
            return self._survival_mode(ctx)
        elif my_hp < 0.5:
            return self._cautious_attack(ctx)
        else:
            return GreedyStrategy().decide(ctx)

    def _survival_mode(self, ctx: BattleContext) -> DecisionResult:
        """危急状态：优先回复/防御"""
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0

        # 找回复技能
        for skill in ctx.my_equipped_skills:
            if skill.energy_cost <= energy and (skill.is_heal or skill.damage_type == '防御'):
                return DecisionResult(
                    skill=skill, score=999,
                    reasons=["危急状态，优先保命"],
                    strategy=self.name(), confidence=0.9,
                )

        # 没有回复技能，用最低能耗
        return self._lowest_cost_skill(ctx)

    def _cautious_attack(self, ctx: BattleContext) -> DecisionResult:
        """危险状态：低能耗克制攻击"""
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0

        best = None
        best_score = 0
        for skill in ctx.my_equipped_skills:
            if skill.damage_type in ('物攻', '魔攻') and skill.energy_cost <= 2:
                if skill.energy_cost <= energy:
                    type_mult = self._get_type_multiplier(
                        skill.element, ctx.enemy_pet.element) if ctx.enemy_pet else 1
                    score = skill.power * type_mult
                    if score > best_score:
                        best_score = score
                        best = skill

        if best:
            return DecisionResult(
                skill=best, score=best_score,
                reasons=["危险状态，低能耗克制攻击"],
                strategy=self.name(), confidence=0.7,
            )
        return GreedyStrategy().decide(ctx)

    def _lowest_cost_skill(self, ctx: BattleContext) -> DecisionResult:
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0
        min_cost = float('inf')
        best = None
        for skill in ctx.my_equipped_skills:
            if skill.energy_cost <= energy and skill.energy_cost < min_cost:
                min_cost = skill.energy_cost
                best = skill
        return DecisionResult(
            skill=best, score=0,
            reasons=["使用最低能耗技能"],
            strategy=self.name(), confidence=0.5,
        )
