"""
敌方技能追踪器

核心逻辑：
- 每只精灵可学习 30-60+ 个技能
- 战斗中只能携带 4 个
- 通过观察敌方已使用的技能，逐步缩小 4 技能范围
- 结合能量管理推测敌方行动（能量不会自然恢复）
"""
from __future__ import annotations

from typing import Optional

from .context import Pet, Skill, Position


class EnemySkillTracker:
    """敌方精灵技能追踪器"""

    def __init__(self, enemy_pet: Pet):
        self.enemy_pet = enemy_pet
        self.confirmed_skills: list[Skill] = []
        self.usage_history: list[tuple[str, int]] = []
        self.skill_usage_count: dict[str, int] = {}
        self._learnable_skills: list[Skill] = []

    def set_learnable_skills(self, skills: list[Skill]):
        """设置该精灵可学习的全部技能"""
        self._learnable_skills = skills

    def record_skill(self, skill_name: str, turn: int):
        """记录敌方使用的技能"""
        self.usage_history.append((skill_name, turn))
        self.skill_usage_count[skill_name] = self.skill_usage_count.get(skill_name, 0) + 1

        if not any(s.name == skill_name for s in self.confirmed_skills):
            skill = self._find_skill(skill_name)
            if skill:
                self.confirmed_skills.append(skill)

    def _find_skill(self, skill_name: str) -> Optional[Skill]:
        for skill in self._learnable_skills:
            if skill.name == skill_name:
                return skill
        return None

    @property
    def confirmed_count(self) -> int:
        return len(self.confirmed_skills)

    @property
    def is_complete(self) -> bool:
        return self.confirmed_count >= 4

    def get_candidates(self) -> list[Skill]:
        """获取第 N+1 个技能的候选列表"""
        if self.is_complete:
            return []
        confirmed_names = {s.name for s in self.confirmed_skills}
        return [s for s in self._learnable_skills if s.name not in confirmed_names]

    def analyze_position(self) -> Position:
        """分析敌方精灵的战斗定位"""
        if not self.confirmed_skills:
            return Position.UNKNOWN

        atk = [s for s in self.confirmed_skills if s.category in ('物攻', '魔攻')]
        defense = [s for s in self.confirmed_skills if s.category == '防御']
        status = [s for s in self.confirmed_skills if s.category == '状态']

        total = len(self.confirmed_skills)
        if total == 0:
            return Position.UNKNOWN

        atk_ratio = len(atk) / total
        def_ratio = len(defense) / total
        status_ratio = len(status) / total

        # DOT 优先
        if any(s.is_dot for s in self.confirmed_skills):
            return Position.DOT

        # 应对型
        counter_skills = [s for s in self.confirmed_skills if s.is_counter]
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

    def predict_next(self, enemy_energy: int, enemy_hp_percent: float,
                     my_hp_percent: float) -> Optional[Skill]:
        """
        预测敌方下回合使用的技能

        考虑因素：
        1. 敌方当前能量（不会自然恢复）
        2. 敌方血量（低血量倾向回复/防御）
        3. 我方血量（低血量倾向高伤害击杀）
        4. 敌方定位
        5. 技能使用历史
        6. 聚能判断（能量不足时）
        """
        if not self.confirmed_skills:
            return None

        position = self.analyze_position()
        candidates = []

        for skill in self.confirmed_skills:
            effective_cost = skill.cost
            if effective_cost > enemy_energy:
                continue

            score = 0

            # 基础分
            if skill.category in ('物攻', '魔攻'):
                score = skill.power
            elif skill.category == '防御':
                score = 45
            elif skill.category == '状态':
                score = 35
                if skill.is_energy_recover:
                    score += 60  # 能量回复技能价值高
                if skill.is_heal:
                    score += 40
                if skill.is_buff:
                    score += 25

            # 定位加权
            if position == Position.AGGRESSIVE and skill.category in ('物攻', '魔攻'):
                score *= 1.5
            elif position == Position.DEFENSIVE and skill.category == '防御':
                score *= 1.8
            elif position == Position.CONTROL and skill.category == '状态':
                score *= 1.5
            elif position == Position.COUNTER and skill.is_counter:
                score *= 2.0

            # 血量因素
            if enemy_hp_percent < 0.3:
                if skill.is_heal:
                    score *= 3.0
                if skill.is_energy_recover:
                    score *= 2.0
                if skill.category == '防御':
                    score *= 1.5

            if my_hp_percent < 0.3:
                if skill.category in ('物攻', '魔攻') and skill.power >= 100:
                    score *= 1.8

            # 能量因素（无自然恢复）
            if enemy_energy >= 5 and skill.cost >= 4:
                score *= 1.3
            elif enemy_energy <= 1:
                if skill.is_energy_recover:
                    score *= 2.0
                elif skill.cost == 0:
                    score *= 1.2

            # 使用频率
            usage = self.skill_usage_count.get(skill.name, 0)
            total_uses = max(1, sum(self.skill_usage_count.values()))
            if usage / total_uses > 0.4:
                score *= 1.1

            candidates.append((skill, score))

        # 如果能量不足且没有 0 能耗技能 → 可能聚能
        if not candidates:
            from .strategies.greedy import JUNENG_SKILL
            return JUNENG_SKILL

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def get_status(self) -> dict:
        return {
            "confirmed": self.confirmed_count,
            "skills": [s.name for s in self.confirmed_skills],
            "position": self.analyze_position().value,
            "history": self.usage_history[-5:],
            "is_complete": self.is_complete,
        }
