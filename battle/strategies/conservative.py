"""
保守策略（Conservative）

优先保证存活，次优输出。
- 血量低于 50% 时优先防御/回复
- 优先使用低能耗技能保持灵活性
- 能量不会自然恢复，需谨慎使用
"""
from .base import DecisionStrategy
from .greedy import GreedyStrategy, JUNENG_SKILL
from ..context import BattleContext, DecisionResult


class ConservativeStrategy(DecisionStrategy):
    def name(self) -> str:
        return "保守策略"

    def decide(self, ctx: BattleContext) -> DecisionResult:
        my_hp = ctx.my_pet.hp_percent if ctx.my_pet else 1.0
        my_energy = ctx.my_pet.current_energy if ctx.my_pet else 0

        if my_hp < 0.3:
            return self._survival_mode(ctx)
        elif my_hp < 0.5:
            return self._cautious_attack(ctx)
        else:
            # 能量低时倾向保守
            if my_energy <= 2:
                return self._energy_conservation(ctx)
            return GreedyStrategy().decide(ctx)

    def _survival_mode(self, ctx: BattleContext) -> DecisionResult:
        """危急状态：优先回复/防御"""
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0

        for skill in ctx.my_equipped_skills:
            if skill.cost <= energy and (skill.is_heal or skill.category == '防御'):
                return DecisionResult(
                    skill=skill, score=999,
                    reasons=["危急状态，优先保命"],
                    strategy=self.name(), confidence=0.9,
                )

        # 没有回复技能 → 聚能
        return DecisionResult(
            skill=JUNENG_SKILL, score=900,
            reasons=["危急状态，聚能回复能量"],
            strategy=self.name(), confidence=0.85,
        )

    def _cautious_attack(self, ctx: BattleContext) -> DecisionResult:
        """危险状态：低能耗克制攻击"""
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0

        best = None
        best_score = 0
        for skill in ctx.my_equipped_skills:
            if skill.category in ('物攻', '魔攻') and skill.cost <= 2:
                if skill.cost <= energy:
                    type_mult = self._get_type_multiplier(
                        skill.element, ctx.enemy_pet.element,
                        ctx.enemy_pet.sub_element) if ctx.enemy_pet else 1
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
        return DecisionResult(
            skill=JUNENG_SKILL, score=50,
            reasons=["能量不足，聚能"],
            strategy=self.name(), confidence=0.6,
        )

    def _energy_conservation(self, ctx: BattleContext) -> DecisionResult:
        """能量保护：0 能耗回复技能 > 低能耗 > 聚能"""
        energy = ctx.my_pet.current_energy if ctx.my_pet else 0

        # 找 0 能耗且有回复效果的技能
        for skill in ctx.my_equipped_skills:
            if skill.cost == 0 and skill.is_energy_recover:
                return DecisionResult(
                    skill=skill, score=80,
                    reasons=["0 能耗回复能量"],
                    strategy=self.name(), confidence=0.8,
                )

        # 找 1 能耗技能
        for skill in ctx.my_equipped_skills:
            if skill.cost == 1 and skill.cost <= energy:
                type_mult = self._get_type_multiplier(
                    skill.element, ctx.enemy_pet.element,
                    ctx.enemy_pet.sub_element) if ctx.enemy_pet else 1
                return DecisionResult(
                    skill=skill, score=skill.power * type_mult,
                    reasons=["低能耗攻击"],
                    strategy=self.name(), confidence=0.6,
                )

        return DecisionResult(
            skill=JUNENG_SKILL, score=50,
            reasons=["能量不足，聚能"],
            strategy=self.name(), confidence=0.6,
        )
