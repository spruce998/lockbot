"""
贪心策略（Greedy）- MVP 默认策略

选择当前回合期望收益最高的技能。

评分维度（按权重排序）：
1. 属性克制倍率（最高权重）
2. 有效伤害（威力 × 克制倍率）
3. 能量利用效率（威力 / 能耗）
4. 当前状态需求（低血量回复、高血量输出）
5. 技能位置效果
6. 特殊机制（迸发/蓄力/永久加成）
7. 敌方行为预测（防御应对）
"""
from .base import DecisionStrategy
from ..context import BattleContext, DecisionResult


class GreedyStrategy(DecisionStrategy):
    def name(self) -> str:
        return "贪心策略"

    def decide(self, ctx: BattleContext) -> DecisionResult:
        if not ctx.my_equipped_skills:
            return DecisionResult(skill=None, score=0, reasons=["无可用技能"])

        best_skill = None
        best_score = -float('inf')
        best_reasons = []

        for skill in ctx.my_equipped_skills:
            score = 0.0
            reasons = []

            # --- 1. 能量检查 ---
            if skill.energy_cost > (ctx.my_pet.current_energy if ctx.my_pet else 0):
                continue

            # --- 2. 属性克制（最高权重）---
            if ctx.enemy_pet:
                type_mult = self._get_type_multiplier(skill.element, ctx.enemy_pet.element)
            else:
                type_mult = 1.0

            if type_mult >= 2.0:
                score += 100 * type_mult
                reasons.append(f"克制 ×{type_mult}")
            elif type_mult <= 0.5:
                score *= 0.3
                reasons.append(f"被抵抗 ×{type_mult}")

            # --- 3. 伤害计算 ---
            if skill.damage_type in ('物攻', '魔攻'):
                base_dmg = self._calc_damage(skill, ctx)
                score += base_dmg * type_mult
                reasons.append(f"期望伤害 {base_dmg:.0f}")
            elif skill.damage_type == '防御':
                score += 40
                reasons.append("防御")
            elif skill.damage_type == '状态':
                if skill.is_buff:
                    score += 50
                    reasons.append("增益")
                elif skill.is_debuff:
                    score += 45
                    reasons.append("减益")
                elif skill.is_energy_recover:
                    score += 60
                    reasons.append("回复能量")
                elif skill.is_heal:
                    score += 55
                    reasons.append("回复生命")
                elif skill.is_dot:
                    score += 35
                    reasons.append("持续伤害")
                else:
                    score += 25
                    reasons.append("状态")

            # --- 4. 能量效率 ---
            if skill.energy_cost > 0:
                efficiency = (skill.power * type_mult) / skill.energy_cost
                score += efficiency * 5
                if efficiency > 20:
                    reasons.append(f"高能量效率")
            else:
                score += 15  # 0 能耗技能有额外分
                reasons.append("0 能耗")

            # --- 5. 位置效果 ---
            pos_bonus = self._calc_position_bonus(skill, ctx)
            score += pos_bonus
            if pos_bonus > 0:
                reasons.append(f"位置加成 +{pos_bonus}")

            # --- 6. 迸发 ---
            if skill.has_burst:
                burst_bonus = self._calc_burst_bonus(skill)
                score += burst_bonus
                if burst_bonus > 0:
                    reasons.append("迸发")

            # --- 7. 应对价值 ---
            counter_value = self._calc_counter_value(skill, ctx)
            score += counter_value
            if counter_value > 20:
                reasons.append("应对敌方")

            # --- 8. 血量因素 ---
            my_hp = ctx.my_pet.hp_percent if ctx.my_pet else 1.0
            if my_hp < 0.3:
                if skill.is_heal or skill.is_energy_recover:
                    score *= 2.0
                    reasons.append("危急回复")
            elif my_hp < 0.5:
                if skill.damage_type == '防御':
                    score *= 1.3
                    reasons.append("危险防御")

            # --- 9. 敌方预测 ---
            if ctx.enemy_predicted_skill:
                if ctx.enemy_predicted_skill.damage_type in ('物攻', '魔攻'):
                    if skill.damage_type == '防御':
                        score *= 1.5
                        reasons.append("应对攻击")

            # --- 10. 永久加成 ---
            permanent_value = self._calc_permanent_value(skill, ctx)
            score += permanent_value
            if permanent_value > 0:
                reasons.append("永久加成")

            if score > best_score:
                best_score = score
                best_skill = skill
                best_reasons = reasons

        if not best_skill:
            # 所有技能能量都不够 → 选能耗最低的
            min_cost = min(s.energy_cost for s in ctx.my_equipped_skills)
            for s in ctx.my_equipped_skills:
                if s.energy_cost == min_cost:
                    best_skill = s
                    best_reasons = [f"能量不足，使用最低能耗({min_cost})技能"]
                    best_score = 0
                    break

        return DecisionResult(
            skill=best_skill,
            score=best_score,
            reasons=best_reasons,
            strategy=self.name(),
            confidence=min(1.0, best_score / 200),
            enemy_prediction=ctx.enemy_predicted_skill,
        )
