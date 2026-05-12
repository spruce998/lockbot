"""
图像识别模块
支持模板匹配、YOLO 目标检测、OCR 文字识别
"""
import cv2
import numpy as np
from pathlib import Path


class ImageRecognizer:
    def __init__(self, template_dir="data/templates"):
        self.template_dir = Path(template_dir)
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板图片"""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for img_path in self.template_dir.glob("*.png"):
            name = img_path.stem
            template = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
            self.templates[name] = template
            print(f"加载模板：{name} - {template.shape}")
    
    def match_template(self, frame, template_name, threshold=0.8):
        """
        模板匹配
        :param frame: 当前帧
        :param template_name: 模板名称
        :param threshold: 匹配阈值
        :return: 匹配结果 (是否匹配，位置，置信度)
        """
        if template_name not in self.templates:
            return False, None, 0.0
        
        template = self.templates[template_name]
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return True, (center_x, center_y), max_val
        
        return False, None, max_val
    
    def match_all_templates(self, frame, threshold=0.8):
        """匹配所有模板，返回所有匹配结果"""
        results = {}
        for name in self.templates:
            matched, pos, conf = self.match_template(frame, name, threshold)
            if matched:
                results[name] = {"position": pos, "confidence": conf}
        return results
    
    def find_multiple(self, frame, template_name, threshold=0.8, min_distance=30):
        """查找多个匹配实例（用于资源点检测）"""
        if template_name not in self.templates:
            return []
        
        template = self.templates[template_name]
        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        
        locations = []
        h, w = template.shape[:2]
        
        while True:
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val < threshold:
                break
            
            # 检查与已找到位置的距离
            is_new = True
            for existing in locations:
                dist = np.sqrt((max_loc[0] - existing[0])**2 + **(max_loc[1] - existing[1])2)
                if dist < min_distance:
                    is_new = False
                    break
            
            if is_new:
                locations.append(max_loc)
            
            # 屏蔽已找到的区域
            x1 = max(0, max_loc[0] - w//2)
            y1 = max(0, max_loc[1] - h//2)
            x2 = min(result.shape[1], max_loc[0] + w//2)
            y2 = min(result.shape[0], max_loc[1] + h//2)
            result[y1:y2, x1:x2] = 0
        
        # 转换为中点坐标
        centers = [(loc[0] + w//2, loc[1] + h//2) for loc in locations]
        return centers
    
    def add_template(self, name, image_path):
        """添加新模板"""
        template = cv2.imread(str(image_path))
        if template is not None:
            self.templates[name] = template
            save_path = self.template_dir / f"{name}.png"
            cv2.imwrite(str(save_path), template)
            print(f"模板已保存：{save_path}")
            return True
        return False


# 使用示例
if __name__ == "__main__":
    recognizer = ImageRecognizer()
    
    # 测试识别
    frame = cv2.imread("test_capture.png")
    if frame is not None:
        results = recognizer.match_all_templates(frame)
        print("识别结果:", results)
    else:
        print("请先运行 capture.py 生成测试截图")
