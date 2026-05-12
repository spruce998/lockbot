"""
洛克王国世界自动化助手 - 主入口
"""
import sys
import time
import yaml
from pathlib import Path
from loguru import logger

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.capture import ScreenCapture
from core.recognizer import ImageRecognizer
from core.controller import InputController
from features.pvp.decision import PVPDecisionEngine
from utils.anti_detect import AntiDetect


def load_config(config_path="config.yaml") -> dict:
    """加载配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def setup_logger(config: dict):
    """配置日志"""
    log_config = config.get("logging", {})
    logger.remove()
    logger.add(
        log_config.get("file", "logs/lockbot.log"),
        level=log_config.get("level", "INFO"),
        rotation="10 MB"
    )
    logger.add(sys.stdout, level=log_config.get("level", "INFO"))


class Lockbot:
    """洛克王国自动化助手主类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.game_config = config.get("game", {})
        self.pvp_config = config.get("pvp", {})
        self.anti_detect_config = config.get("anti_detect", {})
        
        # 初始化核心模块
        self.capture = ScreenCapture(
            window_title=self.game_config.get("window_title"),
            region=tuple(self.game_config.get("capture_region", [0, 0, 0, 0])) or None
        )
        
        self.recognizer = ImageRecognizer()
        self.controller = InputController(anti_detect=self.anti_detect_config.get("enabled", True))
        self.decision_engine = PVPDecisionEngine()
        self.anti_detect = AntiDetect(self.anti_detect_config)
        
        # 状态
        self.running = False
        self.in_battle = False
    
    def start(self):
        """启动助手"""
        logger.info("🎮 洛克王国助手启动中...")
        
        if not self.anti_detect.is_active_hours():
            logger.warning("⚠️ 当前不在活跃时间段内，建议等待")
        
        self.running = True
        
        # 主循环
        while self.running:
            try:
                self._loop()
            except KeyboardInterrupt:
                logger.info("用户中断，停止运行")
                break
            except Exception as e:
                logger.error(f"循环错误：{e}")
                time.sleep(5)
    
    def _loop(self):
        """主循环"""
        # 捕获当前帧
        frame = self.capture.capture()
        
        # 检测是否在战斗中
        battle_detected = self._detect_battle_state(frame)
        
        if battle_detected and not self.in_battle:
            logger.info("⚔️ 检测到进入战斗")
            self.in_battle = True
            self._on_battle_start(frame)
        
        elif battle_detected and self.in_battle:
            # 战斗中决策
            self._battle_logic(frame)
        
        elif not battle_detected and self.in_battle:
            logger.info("✅ 战斗结束")
            self.in_battle = False
            self._on_battle_end()
        
        # 反检测：随机暂停
        if self.anti_detect.should_pause():
            pause_minutes = random.randint(5, 15)
            logger.info(f"⏸️  模拟休息，暂停{pause_minutes}分钟")
            time.sleep(pause_minutes * 60)
        
        # 控制循环频率
        fps = self.game_config.get("fps", 10)
        time.sleep(1.0 / fps)
    
    def _detect_battle_state(self, frame) -> bool:
        """检测是否处于战斗状态"""
        # 检测战斗 UI 元素（如技能栏、血条等）
        # MVP 版本：检测技能按钮模板
        battle_ui_templates = ["skill_slot_1", "skill_slot_2", "skill_slot_3", "skill_slot_4"]
        
        for template in battle_ui_templates:
            matched, pos, conf = self.recognizer.match_template(frame, template, threshold=0.6)
            if matched:
                return True
        
        # TODO: 后续可添加更多战斗状态检测逻辑
        return False
    
    def _on_battle_start(self, frame):
        """战斗开始处理"""
        # 识别敌方宠物
        enemy_info = self._identify_enemy(frame)
        if enemy_info:
            self.decision_engine.set_enemy_pet(
                enemy_info["name"],
                enemy_info.get("hp", 100),
                enemy_info.get("max_hp", 100)
            )
            logger.info(f"识别敌方宠物：{enemy_info['name']}")
    
    def _identify_enemy(self, frame) -> dict:
        """识别敌方宠物信息"""
        # MVP 版本：返回示例数据
        # TODO: 实现实际的宠物识别逻辑
        return {
            "name": "喵喵",
            "hp": 80,
            "max_hp": 100
        }
    
    def _battle_logic(self, frame):
        """战斗中的决策逻辑"""
        # 获取决策
        decision = self.decision_engine.decide()
        
        if decision["action"] == "skill":
            skill_index = decision.get("skill_index", 0)
            logger.info(f"🎯 决策：使用技能 [{decision['skill_name']}] - {decision['reason']}")
            
            # 点击对应技能按钮
            self._click_skill(skill_index)
            
            # 记录操作
            self.anti_detect.record_action()
    
    def _click_skill(self, index: int):
        """点击技能按钮"""
        # 技能按钮位置（需要根据实际游戏 UI 调整）
        skill_positions = [
            (800, 900),  # 技能 1
            (950, 900),  # 技能 2
            (1100, 900), # 技能 3
            (1250, 900)  # 技能 4
        ]
        
        if 0 <= index < len(skill_positions):
            x, y = skill_positions[index]
            
            # 反检测：添加位置偏移
            x, y = self.anti_detect.add_click_variation(x, y)
            
            self.controller.click(x, y)
            logger.debug(f"点击技能按钮 {index+1} 位置：({x}, {y})")
    
    def _on_battle_end(self):
        """战斗结束处理"""
        # 可以添加自动点击继续、返回等操作
        pass
    
    def stop(self):
        """停止助手"""
        self.running = False
        logger.info("👋 助手已停止")
        
        # 输出行为报告
        if self.anti_detect.enabled:
            logger.info(self.anti_detect.generate_report())


def main():
    """主函数"""
    # 加载配置
    config = load_config()
    
    # 设置日志
    setup_logger(config)
    
    logger.info("=" * 50)
    logger.info("🎮 洛克王国世界自动化助手")
    logger.info("=" * 50)
    
    # 创建并启动助手
    bot = Lockbot(config)
    
    try:
        bot.start()
    except Exception as e:
        logger.error(f"启动失败：{e}")
        raise
    finally:
        bot.stop()


if __name__ == "__main__":
    main()
