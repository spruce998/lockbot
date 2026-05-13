"""
敌方技能追踪器

核心逻辑：
- 每只精灵可学习 30-60+ 个技能
- 战斗中只能携带 4 个
- 通过观察敌方已使用的技能，逐步缩小 4 技能范围
"""
from __future__ import annotations

from typing import Optional

from .context import Pet, Skill, Position


class EnemySkillTracker:
    """
    敌方精灵技能追踪器

    工作流程：
    1. 识别敌方精灵 → 从数据库获取可学习技能池（30-60+ 个）
    2. 观察敌方使用的技能 → 逐个确认到 4 技能中
    3. 当确认 3/4 技能后 → 对剩余候选池进行评分排序
    4. 结合敌方定位和战斗状态 → 预测下回合行动
    """

    def __init__(self, enemy_pet: Pet):
        self.enemy_pet = enemy_pet
        self.confirmed_skills: list[Skill] = []
        self.usage_history: list[tuple[str, int]] = []  # [(skill_name, turn), ...]
        self.skill_usage_count: dict[str, int] = {}
        self._learnable_skills: list[Skill] = []

    def set_learnable_skills(self, skills: list[Skill]):
        """设置该精灵可学习的全部技能（从数据库加载）"""
        self._learnable_skills = skills

    def record_skill(self, skill_name: str, turn: int):
        """
        记录敌方使用的技能

        调用时机：每回合敌方行动后，从图像识别或战斗日志中获取
        """
        self.usage_history.append((skill_name, turn))
        self.skill_usage_count[skill_name] = self.skill_usage_count.get(skill_name, 0) + 1

        # 确认这是敌方携带的技能
        if not any(s.name == skill_name for s in self.confirmed_skills):
            skill = self._find_skill(skill_name)
            if skill:
                self.confirmed_skills.append(skill)

    def _find_skill(self, skill_name: str) -> Optional[Skill]:
        """从可学习技能池中查找技能"""
        for skill in self._learnable_skills:
            if skill.name == skill_name:
                return skill
        return None

    @property
    def confirmed_count(self) -> int:
        return len(self.confirmed_skills)

    @property
    def is_complete(self) -> bool:
        """是否已确认全部 4 个技能"""
        return self.confirmed_count >= 4

    def get_candidates(self) -> list[Skill]:
        """
        获取第 N+1 个技能的候选列表

        返回：可学习技能池 - 已确认技能
        """
        if self.is_complete:
            return []

        confirmed_names = {s.name for s in self.confirmed_skills}
        return [s for s in self._learnable_skills if s.name not in confirmed_names]

    def analyze_position(self) -> Position:
        """
        分析敌方精灵的战斗定位

        基于已确认的技能类型分布：
        - 攻击技能占比高 → 爆发型
        - 防御技能占比高 → 防守型
        - 状态技能占比高 → 控制型
        - 有 DOT 技能 → 消耗型
        - 有应对技能 → 应对型
        """
        if not self.confirmed_skills:
            return Position.UNKNOWN

        atk_skills = [s for s in self.confirmed_skills
                      if s.damage_type in ('物攻', '魔攻')]
        def_skills = [s for s in self.confirmed_skills
                      if s.damage_type == '防御']
        status_skills = [s for s in self.confirmed_skills
                         if s.damage_type == '状态']

        total = len(self.confirmed_skills)
        if total == 0:
            return Position.UNKNOWN

        atk_ratio = len(atk_skills) / total
        def_ratio = len(def_skills) / total
        status_ratio = len(status_skills) / total

        # DOT 技能优先判断
        if any(s.is_dot for s in self.confirmed_skills):
            return Position.DOT

        # 应对型判断
        if any(s.has_counter for s in self.confirmed_skills) and def_ratio >= 0.3:
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
        1. 敌方当前能量
        2. 敌方血量（低血量倾向回复/防御）
        3. 我方血量（我方低血量倾向高伤害击杀）
        4. 敌方定位（爆发型倾向攻击，防守型倾向防御）
        5. 技能使用历史（冷却/重复使用倾向）
        6. 能量管理（高能量时倾向高能耗技能）
        """
        if not self.confirmed_skills:
            return None

        position = self.analyze_position()
        candidates = []

        for skill in self.confirmed_skills:
            # 能量检查
            effective_cost = skill.energy_cost
            if effective_cost > enemy_energy:
                continue  # 能量不足

            score = 0

            # --- 基础分 ---
            if skill.damage_type in ('物攻', '魔攻'):
                score = skill.power  # 伤害技能看威力
            elif skill.damage_type == '防御':
                score = 40  # 防御技能基础分
            elif skill.damage_type == '状态':
                score = 30  # 状态技能基础分
                if skill.is_buff:
                    score += 20
                if skill.is_debuff:
                    score += 20

            # --- 定位加权 ---
            if position == Position.AGGRESSIVE:
                if skill.damage_type in ('物攻', '魔攻'):
                    score *= 1.5
            elif position == Position.DEFENSIVE:
                if skill.damage_type == '防御':
                    score *= 1.8
            elif position == Position.CONTROL:
                if skill.damage_type == '状态':
                    score *= 1.5
            elif position == Position.COUNTER:
                if skill.has_counter:
                    score *= 2.0

            # --- 血量因素 ---
            if enemy_hp_percent < 0.3:
                if skill.is_heal:
                    score *= 3.0
                if skill.damage_type == '防御':
                    score *= 1.5
                if skill.is_energy_recover:
                    score *= 2.0

            if my_hp_percent < 0.3:
                if skill.damage_type in ('物攻', '魔攻') and skill.power >= 100:
                    score *= 1.8  # 可能使用击杀技能

            # --- 能量因素 ---
            if enemy_energy >= 5 and skill.energy_cost >= 4:
                score *= 1.3  # 高能量时倾向高能耗
            elif enemy_energy <= 1:
                if skill.energy_cost <= 1:
                    score *= 1.2

            # --- 使用频率 ---
            usage = self.skill_usage_count.get(skill.name, 0)
            total_uses = sum(self.skill_usage_count.values())
            if total_uses > 0:
                usage_ratio = usage / total_uses
                # 频繁使用的技能可能继续用（习惯）
                if usage_ratio > 0.4:
                    score *= 1.1
                # 很久没用的技能可能冷却结束
                elif usage == 0 and len(self.confirmed_skills) > 1:
                    score *= 1.1

            candidates.append((skill, score))

        if not candidates:
            # 如果所有技能能量都不够，选能耗最低的
            min_cost_skill = min(self.confirmed_skills,
                                 key=lambda s: s.energy_cost)
            return min_cost_skill

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def get_status(self) -> dict:
        """获取追踪状态摘要"""
        return {
            "confirmed": self.confirmed_count,
            "skills": [s.name for s in self.confirmed_skills],
            "position": self.analyze_position().value,
            "history": self.usage_history[-5:],  # 最近 5 次
            "is_complete": self.is_complete,
        }
