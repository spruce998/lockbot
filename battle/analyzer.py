"""
敌方精灵分析器

基于敌方已确认技能、血量、能耗、精灵种族值等信息，
分析敌方精灵的战斗定位和下一步行动倾向。
"""
from .context import Pet, Skill, Position, BattleContext


class EnemyPositionAnalyzer:
    """
    敌方精灵战斗定位分析器

    定位类型：
    1. 爆发型 - 高能耗高伤害技能为主（如火神带火云车+山火）
    2. 消耗型 - DOT（灼烧/冻结/中毒）+ 防御
    3. 控制型 - 减益 + 状态技能为主
    4. 均衡型 - 攻击/防御/状态均衡搭配
    5. 应对型 - 以应对技能为核心（大量防御/应对技能）
    """

    def analyze(self, confirmed_skills: list[Skill]) -> Position:
        """根据已确认技能分析定位"""
        if not confirmed_skills:
            return Position.UNKNOWN

        atk = [s for s in confirmed_skills if s.damage_type in ('物攻', '魔攻')]
        defense = [s for s in confirmed_skills if s.damage_type == '防御']
        status = [s for s in confirmed_skills if s.damage_type == '状态']

        total = len(confirmed_skills)
        if total == 0:
            return Position.UNKNOWN

        atk_ratio = len(atk) / total
        def_ratio = len(defense) / total
        status_ratio = len(status) / total

        # DOT 优先
        if any(s.is_dot for s in confirmed_skills):
            return Position.DOT

        # 应对型
        counter_skills = [s for s in confirmed_skills if s.has_counter]
        if len(counter_skills) >= 2 or (len(counter_skills) >= 1 and def_ratio >= 0.3):
            return Position.COUNTER

        if total >= 2:
            if atk_ratio >= 0.7:
                return Position.AGGRESSIVE
            elif def_ratio >= 0.5:
                return Position.DEFENSIVE
            elif status_ratio >= 0.5:
                return Position.CONTROL

        return Position.BALANCED

    def predict_action(self, context: BattleContext) -> dict:
        """
        综合预测敌方下回合行动

        返回：
        {
            "predicted_skill": Skill,    # 预测使用的技能
            "confidence": float,          # 预测置信度 0-1
            "reason": str,               # 预测原因
        }
        """
        if not context.enemy_confirmed_skills:
            return {
                "predicted_skill": None,
                "confidence": 0.0,
                "reason": "未知敌方技能",
            }

        from .tracker import EnemySkillTracker
        tracker = EnemySkillTracker(context.enemy_pet)
        tracker.set_learnable_skills(context.enemy_confirmed_skills)
        # 重建历史
        for skill_name, turn in context.enemy_skill_history:
            tracker.record_skill(skill_name, turn)

        predicted = tracker.predict_next(
            enemy_energy=context.enemy_energy,
            enemy_hp_percent=context.enemy_hp_percent,
            my_hp_percent=context.my_pet.hp_percent if context.my_pet else 1.0,
        )

        confidence = self._calc_confidence(context, tracker, predicted)

        reason = self._build_reason(context, tracker, predicted)

        return {
            "predicted_skill": predicted,
            "confidence": confidence,
            "reason": reason,
        }

    def _calc_confidence(self, context: BattleContext,
                         tracker, predicted: Skill) -> float:
        """计算预测置信度"""
        if not predicted:
            return 0.0

        confidence = 0.3  # 基础置信度

        # 已确认技能越多，置信度越高
        confirmed_count = tracker.confirmed_count
        if confirmed_count >= 4:
            confidence += 0.3
        elif confirmed_count >= 3:
            confidence += 0.2
        elif confirmed_count >= 2:
            confidence += 0.1

        # 敌方有明显定位倾向
        position = tracker.analyze_position()
        if position in (Position.AGGRESSIVE, Position.DEFENSIVE, Position.CONTROL):
            confidence += 0.1

        # 预测技能是高频使用的
        usage = tracker.skill_usage_count.get(predicted.name, 0)
        if usage > 0:
            confidence += 0.1

        return min(1.0, confidence)

    def _build_reason(self, context: BattleContext,
                      tracker, predicted: Skill) -> str:
        """构建预测原因"""
        if not predicted:
            return "无法预测"

        reasons = []
        position = tracker.analyze_position()

        # 定位原因
        if position == Position.AGGRESSIVE:
            reasons.append(f"敌方定位爆发型")
        elif position == Position.DEFENSIVE:
            reasons.append(f"敌方定位防守型")
        elif position == Position.COUNTER:
            reasons.append(f"敌方定位应对型")

        # 技能类型原因
        if predicted.damage_type in ('物攻', '魔攻'):
            reasons.append(f"倾向使用攻击技能 {predicted.name}({predicted.power})")
        elif predicted.damage_type == '防御':
            reasons.append("倾向使用防御技能")
        elif predicted.damage_type == '状态':
            reasons.append("倾向使用状态技能")

        # 血量原因
        if context.enemy_hp_percent < 0.3:
            if predicted.is_heal:
                reasons.append("低血量倾向回复")
        if context.my_pet and context.my_pet.hp_percent < 0.3:
            if predicted.power >= 100:
                reasons.append("我方低血量可能被击杀")

        # 能量原因
        if context.enemy_energy >= 5 and predicted.energy_cost >= 4:
            reasons.append(f"高能量({context.enemy_energy})使用高能耗({predicted.energy_cost})")

        return " | ".join(reasons) if reasons else "基于技能库推测"
