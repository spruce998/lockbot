"""
洛克王国世界 - 半自动战斗辅助（MVP）

功能：
1. 截图识别战斗状态
2. 识别敌方精灵信息
3. 追踪敌方 4 技能
4. 预测敌方行动
5. 给出技能决策推荐

运行：
    python main.py
"""
import sys
import time
import json
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from battle.context import BattleContext, Pet, Skill, Position
from battle.tracker import EnemySkillTracker
from battle.analyzer import EnemyPositionAnalyzer
from battle.decision import StrategyManager
from battle.database import get_pet_by_name, get_pet_skills, get_type_multiplier


# ============================================================
# 日志配置
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("lockbot_mvp")


# ============================================================
# MVP 战斗辅助主类
# ============================================================

class BattleAssistant:
    """
    半自动战斗辅助

    工作流程：
    1. 用户手动截图或提供战斗信息
    2. 系统识别战斗状态
    3. 追踪敌方技能使用
    4. 预测敌方行动
    5. 推荐我方技能
    """

    def __init__(self):
        self.strategy_mgr = StrategyManager()
        self.analyzer = EnemyPositionAnalyzer()
        self.tracker: EnemySkillTracker = None
        self.context: BattleContext = None
        self.in_battle = False

    def start_battle(self, my_pet_name: str, enemy_pet_name: str):
        """
        开始一场战斗

        :param my_pet_name: 我方精灵名称
        :param enemy_pet_name: 敌方精灵名称
        """
        # 加载我方精灵
        my_pet = get_pet_by_name(my_pet_name)
        if not my_pet:
            logger.error(f"找不到精灵: {my_pet_name}")
            return False

        # 加载敌方精灵
        enemy_pet = get_pet_by_name(enemy_pet_name)
        if not enemy_pet:
            logger.error(f"找不到精灵: {enemy_pet_name}")
            return False

        # 初始化战斗上下文
        self.context = BattleContext()
        self.context.my_pet = my_pet
        self.context.my_equipped_skills = get_pet_skills(my_pet_name)
        self.context.enemy_pet = enemy_pet

        # 初始化敌方技能追踪器
        learnable_skills = get_pet_skills(enemy_pet_name)
        self.tracker = EnemySkillTracker(enemy_pet)
        self.tracker.set_learnable_skills(learnable_skills)

        self.in_battle = True
        logger.info(f"战斗开始: {my_pet_name} vs {enemy_pet_name}")
        logger.info(f"我方技能: {[s.name for s in self.context.my_equipped_skills]}")
        logger.info(f"敌方可学技能: {len(learnable_skills)} 个")
        return True

    def record_enemy_skill(self, skill_name: str):
        """
        记录敌方使用的技能

        调用时机：每回合敌方行动后，用户输入或 OCR 识别
        """
        if not self.in_battle:
            logger.warning("不在战斗中")
            return

        self.context.turn_number += 1
        self.context.update_enemy_skill(skill_name)
        self.tracker.record_skill(skill_name, self.context.turn_number)

        # 更新敌方能量推测
        self._update_enemy_energy(skill_name)

        logger.info(f"回合 {self.context.turn_number}: 敌方使用 {skill_name}")
        logger.info(f"  已确认技能: {self.tracker.confirmed_count}/4 "
                    f"{[s.name for s in self.tracker.confirmed_skills]}")

    def decide(self, my_current_energy: int = None) -> dict:
        """
        做出决策

        :param my_current_energy: 我方当前能量（如不传则使用默认值）
        :return: 决策结果字典
        """
        if not self.in_battle:
            return {"error": "不在战斗中"}

        # 更新能量
        if my_current_energy is not None:
            self.context.my_pet.current_energy = my_current_energy

        # 预测敌方行动
        prediction = self.analyzer.predict_action(self.context)
        self.context.enemy_predicted_skill = prediction.get("predicted_skill")
        self.context.enemy_prediction_confidence = prediction.get("confidence", 0)

        # 做出决策
        result = self.strategy_mgr.decide(self.context)

        # 构建返回
        return {
            "turn": self.context.turn_number,
            "strategy": result.strategy,
            "recommended_skill": result.skill.name if result.skill else None,
            "reasons": result.reasons,
            "score": round(result.score, 1),
            "confidence": round(result.confidence, 2),
            "enemy_prediction": {
                "skill": prediction.get("predicted_skill").name if prediction.get("predicted_skill") else "未知",
                "confidence": round(prediction.get("confidence", 0), 2),
                "reason": prediction.get("reason", ""),
            },
            "enemy_tracking": self.tracker.get_status(),
            "my_energy": self.context.my_pet.current_energy,
            "enemy_hp": round(self.context.enemy_hp_percent * 100, 1),
        }

    def set_strategy(self, name: str):
        """切换策略"""
        self.strategy_mgr.set_strategy(name)

    def list_strategies(self) -> list:
        """列出可用策略"""
        return self.strategy_mgr.list_strategies()

    def end_battle(self, result: str = ""):
        """结束战斗"""
        self.in_battle = False
        logger.info(f"战斗结束: {result}")
        logger.info(f"  敌方最终确认技能: {[s.name for s in self.tracker.confirmed_skills]}")
        logger.info(f"  敌方定位: {self.tracker.analyze_position().value}")

    def _update_enemy_energy(self, skill_name: str):
        """根据敌方使用的技能更新能量推测"""
        skill = self.tracker._find_skill(skill_name)
        if skill:
            # 敌方使用技能消耗能量
            self.context.enemy_energy = max(0,
                self.context.enemy_energy - skill.energy_cost)

        # 每回合恢复能量（假设 2-3，取 2.5）
        self.context.enemy_energy = min(12,
            self.context.enemy_energy + 2)


# ============================================================
# 主程序
# ============================================================

def main():
    logger.info("=" * 50)
    logger.info("洛克王国世界 - 半自动战斗辅助 (MVP)")
    logger.info("=" * 50)

    assistant = BattleAssistant()

    # 列出可用策略
    logger.info(f"可用策略: {assistant.list_strategies()}")

    # 示例：模拟一场战斗
    # 实际使用时，这些信息从图像识别获取
    my_pet = input("输入我方精灵名称（如 阿布）: ").strip()
    enemy_pet = input("输入敌方精灵名称（如 火神）: ").strip()

    if not assistant.start_battle(my_pet, enemy_pet):
        logger.error("战斗初始化失败")
        return

    # 模拟战斗循环
    while assistant.in_battle:
        print("\n" + "=" * 40)
        print(f"回合 {assistant.context.turn_number + 1}")
        print(f"我方能量: {assistant.context.my_pet.current_energy}")
        print(f"敌方血量: {assistant.context.enemy_hp_percent * 100:.0f}%")
        print(f"已确认敌方技能: {assistant.tracker.confirmed_count}/4")

        # 1. 输入敌方使用的技能
        enemy_skill = input("敌方使用的技能（输入技能名，或 'q' 结束）: ").strip()
        if enemy_skill.lower() == 'q':
            assistant.end_battle("手动结束")
            break

        if enemy_skill:
            assistant.record_enemy_skill(enemy_skill)

        # 2. 输入我方当前能量
        energy_input = input(f"我方当前能量（默认 {assistant.context.my_pet.current_energy}）: ").strip()
        energy = int(energy_input) if energy_input.isdigit() else None

        # 3. 做出决策
        result = assistant.decide(energy)

        # 4. 显示结果
        print("\n" + "-" * 40)
        print(f"【决策结果】")
        print(f"  策略: {result['strategy']}")
        print(f"  推荐技能: {result['recommended_skill']}")
        print(f"  原因: {' | '.join(result['reasons'])}")
        print(f"  敌方预测: {result['enemy_prediction']['skill']} "
              f"(置信度 {result['enemy_prediction']['confidence']:.0%})")
        print(f"  敌方已确认技能: {result['enemy_tracking']['skills']}")
        print(f"  敌方定位: {result['enemy_tracking']['position']}")

        # 5. 切换策略（可选）
        switch = input("切换策略？(greedy/conservative/aggressive，直接回车跳过): ").strip()
        if switch:
            try:
                assistant.set_strategy(switch)
            except ValueError as e:
                logger.warning(e)


if __name__ == "__main__":
    main()
