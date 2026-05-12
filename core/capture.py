"""
屏幕捕获模块
支持窗口捕获、区域捕获、持续捕获
"""
import cv2
import numpy as np
import pyautogui
from PIL import ImageGrab
import win32gui
import win32con
import win32ui


class ScreenCapture:
    def __init__(self, window_title=None, region=None):
        """
        :param window_title: 游戏窗口标题
        :param region: 捕获区域 (x, y, width, height)，None 表示全屏
        """
        self.window_title = window_title
        self.region = region
        self.hwnd = None
        
        if window_title:
            self.hwnd = self._find_window(window_title)
    
    def _find_window(self, title):
        """查找游戏窗口句柄"""
        def callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    results.append(hwnd)
            return True
        
        results = []
        win32gui.EnumWindows(callback, results)
        return results[0] if results else None
    
    def capture(self):
        """捕获一帧图像"""
        if self.hwnd:
            # 窗口捕获
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            width = right - left
            height = bottom - top
            
            hwnd_dc = win32gui.GetWindowDC(self.hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)
            
            bmpinfo = bitmap.GetInfo()
            bmpstr = bitmap.GetBitmapBits(True)
            
            img = np.frombuffer(bmpstr, dtype='uint8')
            img = img.reshape((height, width, 4))
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(self.hwnd, hwnd_dc)
            
            return img
        else:
            # 全屏/区域捕获
            if self.region:
                screenshot = ImageGrab.grab(bbox=self.region)
            else:
                screenshot = ImageGrab.grab()
            
            return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    def capture_async(self, callback):
        """异步捕获（用于持续监控）"""
        import threading
        threading.Thread(target=self._capture_loop, args=(callback,), daemon=True).start()
    
    def _capture_loop(self, callback, fps=10):
        """持续捕获循环"""
        import time
        interval = 1.0 / fps
        
        while True:
            frame = self.capture()
            callback(frame)
            time.sleep(interval)


# 使用示例
if __name__ == "__main__":
    # 示例：捕获游戏窗口
    capture = ScreenCapture(window_title="洛克王国世界")
    frame = capture.capture()
    print(f"捕获图像尺寸：{frame.shape}")
    
    # 保存测试截图
    cv2.imwrite("test_capture.png", frame)
    print("测试截图已保存到 test_capture.png")
