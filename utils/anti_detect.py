"""
反检测模块
模拟人类行为，降低被检测风险
"""
import random
import time
import pyautogui
from datetime import datetime


class AntiDetect:
    """反检测系统"""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.active_hours = self.config.get("active_hours", [8, 23])
        
        # 行为统计
        self.action_count = 0
        self.last_action_time = None
        self.session_start = datetime.now()
    
    def is_active_hours(self) -> bool:
        """检查是否在活跃时间段内"""
        current_hour = datetime.now().hour
        start, end = self.active_hours
        return start <= current_hour <= end
    
    def should_pause(self) -> bool:
        """判断是否应该暂停（模拟休息）"""
        if not self.enabled:
            return False
        
        # 连续运行 1-2 小时后，随机暂停 5-15 分钟
        elapsed = (datetime.now() - self.session_start).total_seconds()
        if elapsed > random.uniform(3600, 7200):
            return True
        
        return False
    
    def get_random_delay(self) -> float:
        """获取随机延迟时间"""
        if not self.enabled:
            return 0.1
        
        min_delay = self.config.get("random_delay", [0.1, 0.5])[0]
        max_delay = self.config.get("random_delay", [0.1, 0.5])[1]
        return random.uniform(min_delay, max_delay)
    
    def human_delay(self, base_delay: float = 0.2):
        """拟人化延迟"""
        if self.enabled:
            delay = base_delay + self.get_random_delay()
            time.sleep(delay)
        else:
            time.sleep(base_delay)
    
    def random_mouse_movement(self, range_pixels: int = 50):
        """随机微小鼠标移动（模拟无意识动作）"""
        if not self.enabled:
            return
        
        current_x, current_y = pyautogui.position()
        offset_x = random.uniform(-range_pixels, range_pixels)
        offset_y = random.uniform(-range_pixels, range_pixels)
        
        pyautogui.moveRel(offset_x, offset_y, duration=random.uniform(0.3, 0.8))
    
    def add_click_variation(self, x: int, y: int) -> tuple:
        """添加点击位置微小偏移"""
        if not self.enabled or not self.config.get("human_like_clicks", True):
            return x, y
        
        # 3-8 像素的随机偏移
        offset_x = random.randint(-8, 8)
        offset_y = random.randint(-8, 8)
        return x + offset_x, y + offset_y
    
    def record_action(self):
        """记录一次操作"""
        self.action_count += 1
        self.last_action_time = datetime.now()
    
    def get_behavior_stats(self) -> dict:
        """获取行为统计"""
        elapsed = (datetime.now() - self.session_start).total_seconds()
        return {
            "session_duration_sec": elapsed,
            "total_actions": self.action_count,
            "actions_per_minute": self.action_count / (elapsed / 60) if elapsed > 0 else 0,
            "last_action": self.last_action_time.isoformat() if self.last_action_time else None
        }
    
    def generate_report(self) -> str:
        """生成行为报告（用于自我检查）"""
        stats = self.get_behavior_stats()
        report = f"""
=== 反检测行为报告 ===
会话时长：{stats['session_duration_sec']:.0f} 秒 ({stats['session_duration_sec']/60:.1f} 分钟)
总操作数：{stats['total_actions']}
操作频率：{stats['actions_per_minute']:.2f} 次/分钟
最后操作：{stats['last_action'] or '无'}

建议:
- 正常人类操作频率：10-60 次/分钟
- 如果超过 100 次/分钟，建议增加随机延迟
- 每 1-2 小时应暂停 5-15 分钟
"""
        return report


class ActivityScheduler:
    """活动调度器 - 模拟人类作息"""
    
    def __init__(self):
        self.sessions = []
    
    def should_run(self) -> bool:
        """判断当前是否应该运行"""
        now = datetime.now()
        hour = now.hour
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        
        # 工作日：避开工作时间（9-12 点，14-18 点）
        if weekday < 5:
            if 9 <= hour <= 12 or 14 <= hour <= 18:
                return False
        
        # 每天：避开深夜（23 点 - 次日 7 点）
        if 23 <= hour or hour <= 7:
            return False
        
        return True
    
    def get_next_run_time(self) -> datetime:
        """计算下次运行时间"""
        now = datetime.now()
        
        # 简单实现：1 小时后
        from datetime import timedelta
        return now + timedelta(hours=1)


# 使用示例
if __name__ == "__main__":
    anti_detect = AntiDetect({
        "enabled": True,
        "random_delay": [0.2, 0.8],
        "human_like_clicks": True,
        "active_hours": [8, 23]
    })
    
    print("活跃时间检查:", anti_detect.is_active_hours())
    print("随机延迟:", anti_detect.get_random_delay())
    
    # 模拟几次操作
    for i in range(5):
        anti_detect.record_action()
        anti_detect.human_delay()
    
    print("\n行为报告:")
    print(anti_detect.generate_report())
