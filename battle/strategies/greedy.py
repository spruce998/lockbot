"""
贪心策略（Greedy）- MVP 默认策略

选择当前回合期望收益最高的技能。

真实游戏规则：
- 能量不会每回合自然恢复
- 使用聚能回复 5 能量（状态技能，可被打断）
- 先后手 = 先手值 > 速度
- 双属性克制倍率相乘
"""
from .base import DecisionStrategy
from ..context import BattleContext, DecisionResult, Skill


# 聚能技能（特殊行动，不是携带技能）
JUNENG_SKILL = Skill(
    name="聚能",
    element="普通",
    category="状态",
    cost=0,  # 不消耗能量
    power=0,
    effect="回复5能量。可被应对状态的技能打断。",
)


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
            my_energy = ctx.my_pet.current_energy if ctx.my_pet else 0
            if skill.cost > my_energy:
                continue

            # --- 2. 属性克制（最高权重）---
            if ctx.enemy_pet:
                type_mult = self._get_type_multiplier(
                    skill.element, ctx.enemy_pet.element, ctx.enemy_pet.sub_element)
            else:
                type_mult = 1.0

            if type_mult >= 4.0:
                score += 200 * type_mult
                reasons.append(f"双属性克制 ×{type_mult}")
            elif type_mult >= 2.0:
                score += 100 * type_mult
                reasons.append(f"克制 ×{type_mult}")
            elif type_mult <= 0.25:
                score *= 0.2
                reasons.append(f"双重抵抗 ×{type_mult}")
            elif type_mult <= 0.5:
                score *= 0.4
                reasons.append(f"被抵抗 ×{type_mult}")

            # --- 3. 伤害计算 ---
            if skill.category in ('物攻', '魔攻'):
                base_dmg = self._calc_damage(skill, ctx)
                score += base_dmg * max(type_mult, 1.0)
                reasons.append(f"期望伤害 {base_dmg:.0f}")
            elif skill.category == '防御':
                score += 50
                reasons.append("防御")
            elif skill.category == '状态':
                if skill.is_energy_recover:
                    score += 80  # 高价值：回复能量
                    reasons.append("回复能量")
                elif skill.is_heal:
                    score += 60
                    reasons.append("回复生命")
                elif skill.is_buff:
                    score += 55
                    reasons.append("增益")
                elif skill.is_debuff:
                    score += 50
                    reasons.append("减益")
                elif skill.is_dot:
                    score += 40
                    reasons.append("持续伤害")
                else:
                    score += 30
                    reasons.append("状态")

            # --- 4. 能量效率 ---
            if skill.cost > 0:
                efficiency = (skill.power * max(type_mult, 1.0)) / skill.cost
                score += efficiency * 5
            else:
                score += 20  # 0 能耗有额外分
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
                if skill.is_heal:
                    score *= 2.5
                    reasons.append("危急回复")
                elif skill.category == '防御':
                    score *= 1.5
                    reasons.append("危险防御")
                elif skill.is_energy_recover:
                    score *= 1.8
                    reasons.append("低血量攒能量")
            elif my_hp < 0.5:
                if skill.category == '防御':
                    score *= 1.2

            # --- 9. 敌方预测 ---
            if ctx.enemy_predicted_skill:
                if ctx.enemy_predicted_skill.category in ('物攻', '魔攻'):
                    if skill.category == '防御':
                        score *= 1.5
                        reasons.append("应对攻击")

            # --- 10. 永久加成 ---
            permanent_value = self._calc_permanent_value(skill, ctx)
            score += permanent_value
            if permanent_value > 0:
                reasons.append("永久加成")

            # --- 11. 能量管理 ---
            # 如果能量很低且没有回复技能 → 考虑聚能
            if my_energy <= 1 and skill.cost == 0 and skill.is_energy_recover:
                score *= 1.5
                reasons.append("能量不足回复")

            if score > best_score:
                best_score = score
                best_skill = skill
                best_reasons = reasons

        # 如果所有技能能量都不够 → 考虑聚能
        if not best_skill:
            return DecisionResult(
                skill=JUNENG_SKILL, score=50,
                reasons=["能量不足，聚能回复 5 能量"],
                strategy=self.name(), confidence=0.8,
            )

        # 如果能量很低（≤1），且聚能的价值高于当前最佳技能 → 推荐聚能
        my_energy = ctx.my_pet.current_energy if ctx.my_pet else 0
        if my_energy <= 1 and best_score < 60:
            return DecisionResult(
                skill=JUNENG_SKILL, score=55,
                reasons=[f"能量不足({my_energy})，聚能回复 5 能量"],
                strategy=self.name(), confidence=0.7,
                enemy_prediction=ctx.enemy_predicted_skill,
            )

        return DecisionResult(
            skill=best_skill,
            score=best_score,
            reasons=best_reasons,
            strategy=self.name(),
            confidence=min(1.0, best_score / 200),
            enemy_prediction=ctx.enemy_predicted_skill,
        )
