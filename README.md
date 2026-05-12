# 洛克王国世界自动化助手

> ⚠️ **免责声明**: 本项目仅供学习和研究使用。使用自动化脚本可能违反游戏服务条款，请谨慎使用，建议使用小号测试。

## 📋 项目概述

洛克王国世界 PVP 对战自动化工具，从辅助工具逐步迭代到半自动/全自动。

### 当前阶段：Phase 1 - MVP（辅助工具）

- ✅ 屏幕捕获模块
- ✅ 图像识别模块（模板匹配）
- ✅ 输入控制模块（拟人化操作）
- ✅ PVP 决策引擎（属性克制）
- ✅ 反检测系统

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Windows 10/11（游戏仅在 Windows 运行）
- 洛克王国世界 PC 客户端

### 2. 安装依赖

```bash
cd lockbot
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置

编辑 `config.yaml`：

```yaml
game:
  window_title: "洛克王国世界"  # 游戏窗口标题
  capture_region: [0, 0, 1920, 1080]  # 截图区域
```

### 4. 运行

```bash
python main.py
```

## 📁 项目结构

```
lockbot/
├── core/                    # 核心引擎
│   ├── capture.py          # 屏幕截图
│   ├── recognizer.py       # 图像识别
│   └── controller.py       # 输入控制
├── data/                    # 数据资源
│   ├── templates/          # UI 模板图片
│   ├── pet_db.json         # 宠物数据库
│   └── skill_db.json       # 技能数据库
├── features/                # 功能模块
│   └── pvp/
│       └── decision.py     # PVP 决策引擎
├── utils/
│   └── anti_detect.py      # 反检测
├── config.yaml              # 配置文件
└── main.py                  # 主入口
```

## 🎯 Phase 1 待完成任务

### 第一步：收集游戏素材

运行测试截图工具：

```bash
python core/capture.py
```

这会生成 `test_capture.png`，用于：

1. 确认窗口捕获是否正常工作
2. 截取技能图标、宠物头像等模板图片

### 第二步：创建模板图片

在 `data/templates/` 目录下放置以下模板：

- `skill_slot_1.png` - 技能栏位置 1
- `skill_slot_2.png` - 技能栏位置 2
- `skill_slot_3.png` - 技能栏位置 3
- `skill_slot_4.png` - 技能栏位置 4
- `pet_fire.png` - 火系宠物标识
- `pet_water.png` - 水系宠物标识
- `pet_grass.png` - 草系宠物标识
- `hp_bar.png` - 血条模板
- `battle_ui.png` - 战斗界面标识

**如何获取模板**：
1. 手动截图游戏界面
2. 用画图工具裁剪出需要的图标
3. 保存到 `data/templates/` 目录

### 第三步：完善宠物数据库

编辑 `data/pet_db.json`，添加你拥有的宠物信息：

```json
{
  "你的宠物名": {
    "element": "fire",  // fire/water/grass/electric/ice/...
    "hp": 100,
    "speed": 80,
    "skills": ["技能 1", "技能 2", "技能 3", "技能 4"]
  }
}
```

### 第四步：测试运行

```bash
python main.py
```

观察日志输出，确认：
- 窗口捕获正常
- 战斗状态检测正常
- 决策逻辑正常

## 🔒 反检测功能

当前实现的反检测措施：

| 功能 | 说明 |
|------|------|
| 随机延迟 | 每次操作添加 0.1-0.5 秒随机延迟 |
| 鼠标平滑移动 | 贝塞尔曲线 + 随机扰动 |
| 点击位置偏移 | 3-8 像素随机偏移 |
| 活跃时间限制 | 仅在规定时间段运行 |
| 定时休息 | 每 1-2 小时暂停 5-15 分钟 |

## 📊 下一步开发计划

### Phase 2 - 半自动（2-4 周）
- [ ] 完善宠物识别（YOLO 模型）
- [ ] 自动点击技能按钮
- [ ] 战斗状态完整检测
- [ ] 图形化控制面板

### Phase 3 - 全自动（4-8 周）
- [ ] 自动排队进入 PVP
- [ ] 自动跑图功能
- [ ] 资源点识别与采集
- [ ] 高级反检测（行为学习）

## 🛠️ 开发指南

### 添加新宠物

1. 在 `data/pet_db.json` 中添加宠物信息
2. 截取宠物头像模板到 `data/templates/`
3. 在识别器中注册新模板

### 调整技能位置

编辑 `main.py` 中的 `skill_positions`：

```python
skill_positions = [
    (800, 900),  # 根据你的屏幕分辨率调整
    (950, 900),
    (1100, 900),
    (1250, 900)
]
```

### 调试模式

```bash
# 设置日志级别为 DEBUG
# 编辑 config.yaml:
logging:
  level: "DEBUG"
```

## ⚠️ 风险提示

1. **封号风险**: 使用自动化脚本违反游戏 ToS，可能被封号
2. **建议使用小号**: 不要用于主账号
3. **适度使用**: 避免长时间连续运行
4. **本地运行**: 不要使用来源不明的脚本

## 📝 更新日志

### v0.1.0 (2026-05-12)
- 初始版本
- 核心模块完成
- MVP 决策引擎
- 基础反检测

## 📞 问题反馈

遇到问题时，请提供：
1. 错误日志（`logs/lockbot.log`）
2. 游戏分辨率
3. 操作系统版本
