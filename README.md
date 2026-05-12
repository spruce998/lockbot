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
- ✅ BWIKI 数据爬虫（自动采集宠物、技能数据）

---

## 📊 数据采集

本项目通过 BWIKI 社区 Wiki 自动采集洛克王国世界的游戏数据，为 PVP 决策引擎提供基础数据支持。

### 数据来源

| 数据源 | 地址 | 数据协议 |
|--------|------|---------|
| **BWIKI 洛克王国世界** | https://wiki.biligame.com/rocom/ | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans) |
| 游戏客户端 | 洛克王国世界 PC 端 | 官方游戏（仅截图验证用） |

**BWIKI 简介**：
- 由 B 站社区维护的洛克王国世界 Wiki
- 创建于 2024年9月，截至 2026年5月已有 12,467+ 个页面、1,039+ 位活跃编辑
- 包含完整的精灵图鉴、技能图鉴、克制计算器等

### 已采集数据汇总

| 数据类型 | 数量 | 状态 |
|---------|------|------|
| 宠物（精灵） | **475** 条 | ✅ 已完成 |
| 技能 | **485** 条 | ✅ 已完成 |
| 属性克制关系 | **60** 条 | ⚠️ 需游戏内验证 |
| 宠物-技能关联 | **35,938** 条 | ✅ 已完成 |

### 宠物属性分布

| 属性 | 数量 | 属性 | 数量 |
|------|------|------|------|
| 草 | 50 | 翼 | 33 |
| 水 | 47 | 冰 | 30 |
| 地 | 41 | 普通 | 29 |
| 火 | 32 | 幽 | 23 |
| 虫 | 23 | 恶 | 23 |
| 机械 | 22 | 武 | 22 |
| 电 | 21 | 光 | 20 |
| 毒 | 19 | 萌 | 18 |
| 幻 | 17 | 龙 | 5 |

### 爬虫使用说明

```bash
# 运行爬虫（全量爬取）
python scripts/bwiki_crawler.py --all --import-db

# 测试模式（每种只爬 5 条）
python scripts/bwiki_crawler.py --test

# 断点续传（中断后继续）
python scripts/bwiki_crawler.py --pets --resume

# 重置断点重新爬取
python scripts/bwiki_crawler.py --pets --reset
```

### 爬虫特性

- **防封 7 层防护**：请求限速、UA 轮换、会话管理、指数退避、断点续传、分批休息、时间分散
- **请求间隔**：2-5 秒随机延迟，每批次（20 个）间休息 10-30 秒
- **断点续传**：中断后可自动恢复，不会重复爬取已完成的数据

### 数据存储

```
data/
├── lockbot.db                    # SQLite 数据库（主数据）
├── export/
│   ├── pets.json                 # 宠物 JSON 导出
│   ├── skills.json               # 技能 JSON 导出
│   ├── type_chart.json           # 克制关系 JSON
│   └── crawl_report.json         # 爬取汇总报告
├── .checkpoint/
│   ├── pets.json                 # 宠物断点记录
│   └── skills.json               # 技能断点记录
└── pet_db.json / skill_db.json   # 旧版 JSON（兼容保留）
```

> ⚠️ `data/lockbot.db`、`data/export/`、`data/.checkpoint/` 已加入 `.gitignore`，不包含在仓库中。
> 克隆后运行 `python scripts/init_db.py` 初始化数据库，再运行爬虫采集数据。

---

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

### 3. 初始化数据库

```bash
python scripts/init_db.py
```

### 4. 采集数据

```bash
# 从 BWIKI 爬取宠物、技能数据并导入数据库
python scripts/bwiki_crawler.py --all --import-db
```

### 5. 配置

编辑 `config.yaml`：

```yaml
game:
  window_title: "洛克王国世界"  # 游戏窗口标题
  capture_region: [0, 0, 1920, 1080]  # 截图区域
```

### 6. 运行

```bash
python main.py
```

---

## 📁 项目结构

```
lockbot/
├── core/                    # 核心引擎
│   ├── capture.py          # 屏幕截图
│   ├── recognizer.py       # 图像识别
│   └── controller.py       # 输入控制
├── data/                    # 数据资源
│   ├── lockbot.db          # SQLite 数据库（需运行爬虫后生成）
│   ├── export/             # 爬虫导出文件
│   └── .checkpoint/        # 断点记录
├── features/                # 功能模块
│   └── pvp/
│       └── decision.py     # PVP 决策引擎
├── utils/
│   └── anti_detect.py      # 反检测
├── scripts/                 # 脚本
│   ├── bwiki_crawler.py    # BWIKI 数据爬虫
│   └── init_db.py          # 数据库初始化
├── docs/                    # 文档
│   └── 技术方案_v2.0.md    # 详细技术方案
├── config.yaml              # 配置文件
├── requirements.txt         # 依赖列表
└── main.py                  # 主入口
```

---

## 🎯 开发计划

### Phase 1 - MVP（辅助工具） ✅
- [x] 屏幕捕获模块
- [x] 图像识别模块（模板匹配）
- [x] 输入控制模块（拟人化操作）
- [x] PVP 决策引擎（属性克制）
- [x] 反检测系统
- [x] BWIKI 数据爬虫
- [ ] 游戏内模板图片采集
- [ ] 窗口捕获 + 战斗状态检测

### Phase 2 - 半自动（2-4 周）
- [ ] 自动点击技能按钮
- [ ] 战斗状态完整检测
- [ ] 反检测增强（行为模拟）
- [ ] 图形化控制面板（PyQt6）
- [ ] OCR 文字识别

### Phase 3 - 全自动（4-8 周）
- [ ] 自动排队进入 PVP
- [ ] 自动跑图功能
- [ ] 资源点识别与采集（YOLO）
- [ ] 高级 AI 决策（Minimax / MCTS）

---

## 🔒 反检测功能

当前实现的反检测措施：

| 功能 | 说明 |
|------|------|
| 随机延迟 | 每次操作添加 0.1-0.5 秒随机延迟 |
| 鼠标平滑移动 | 贝塞尔曲线 + 随机扰动 |
| 点击位置偏移 | 3-8 像素随机偏移 |
| 活跃时间限制 | 仅在规定时间段运行 |
| 定时休息 | 每 1-2 小时暂停 5-15 分钟 |
| UA 轮换 | 每 50 次请求自动切换 User-Agent |

---

## ⚠️ 风险提示

1. **封号风险**: 使用自动化脚本违反游戏 ToS，可能被封号
2. **建议使用小号**: 不要用于主账号
3. **适度使用**: 避免长时间连续运行
4. **本地运行**: 不要使用来源不明的脚本

---

## 📝 更新日志

### v0.2.0 (2026-05-12)
- ✅ BWIKI 数据爬虫（v2 DOM 结构化解析）
- ✅ 数据库升级为 SQLite（10 张表）
- ✅ 爬取 475 个宠物、485 个技能数据
- ✅ 数据自动导入数据库

### v0.1.0 (2026-05-12)
- 初始版本
- 核心模块完成
- MVP 决策引擎
- 基础反检测

---

## 📞 问题反馈

遇到问题时，请提供：
1. 错误日志（`logs/crawler_*.log` 或 `logs/lockbot.log`）
2. 游戏分辨率
3. 操作系统版本

## 📄 许可证

本项目代码采用 MIT 许可证。

游戏数据来源于 BWIKI 社区（https://wiki.biligame.com/rocom/），采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans) 协议。
使用本项目数据时请遵守相应协议，注明来源。
