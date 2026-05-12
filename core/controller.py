"""
输入控制模块
模拟鼠标键盘操作，带反检测功能
"""
import pyautogui
import pynput
import numpy as np
import time
import random
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController


class InputController:
    def __init__(self, anti_detect=True):
        self.anti_detect = anti_detect
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        
        # pyautogui 设置
        pyautogui.FAILSAFE = True  # 鼠标移到屏幕角落可中止
        pyautogui.PAUSE = 0.1
    
    def move_to(self, x, y, duration=0.3):
        """平滑移动鼠标到目标位置"""
        if self.anti_detect:
            self._human_move_to(x, y, duration)
        else:
            pyautogui.moveTo(x, y, duration=duration)
    
    def _human_move_to(self, end_x, end_y, duration=0.3):
        """拟人化鼠标移动（贝塞尔曲线 + 随机扰动）"""
        start_x, start_y = pyautogui.position()
        
        # 生成贝塞尔曲线控制点
        control_x = (start_x + end_x) / 2 + random.uniform(-50, 50)
        control_y = (start_y + end_y) / 2 + random.uniform(-50, 50)
        
        steps = int(duration * 60)  # 60 FPS
        for i in range(steps + 1):
            t = i / steps
            
            # 二次贝塞尔曲线
            x = (1-t)**2 * start_x + 2*(1-t)*t * control_x + t**2 * end_x
            y = (1-t)**2 * start_y + 2*(1-t)*t * control_y + t**2 * end_y
            
            # 添加微小抖动
            x += random.uniform(-2, 2)
            y += random.uniform(-2, 2)
            
            self.mouse.position = (int(x), int(y))
            time.sleep(duration / steps)
    
    def click(self, x=None, y=None, button='left', clicks=1):
        """点击操作"""
        if x is not None and y is not None:
            self.move_to(x, y)
        
        if self.anti_detect:
            # 随机延迟
            time.sleep(random.uniform(0.1, 0.3))
        
        for _ in range(clicks):
            self.mouse.press(Button.left)
            time.sleep(random.uniform(0.05, 0.15))
            self.mouse.release(Button.left)
            
            if clicks > 1:
                time.sleep(random.uniform(0.1, 0.3))
    
    def double_click(self, x=None, y=None):
        """双击"""
        self.click(x, y, clicks=2)
    
    def press_key(self, key, duration=0.1):
        """按键"""
        if self.anti_detect:
            time.sleep(random.uniform(0.05, 0.15))
        
        self.keyboard.press(key)
        time.sleep(duration + random.uniform(0, 0.05))
        self.keyboard.release(key)
    
    def press_keys(self, keys, delay=0.05):
        """组合键"""
        for key in keys:
            self.keyboard.press(key)
            time.sleep(delay)
        for key in reversed(keys):
            self.keyboard.release(key)
    
    def scroll(self, amount, x=None, y=None):
        """滚动"""
        if x is not None and y is not None:
            self.move_to(x, y)
        
        self.mouse.scroll(0, amount)
    
    def random_idle(self, min_sec=1, max_sec=5):
        """随机空闲时间（模拟人类思考）"""
        time.sleep(random.uniform(min_sec, max_sec))


# 使用示例
if __name__ == "__main__":
    controller = InputController(anti_detect=True)
    
    print("5 秒后开始测试...")
    time.sleep(5)
    
    # 测试移动
    controller.move_to(500, 500)
    print("移动到 (500, 500)")
    
    # 测试点击
    controller.click()
    print("点击")
    
    # 测试按键
    controller.press_key('a')
    print("按下 'a' 键")
