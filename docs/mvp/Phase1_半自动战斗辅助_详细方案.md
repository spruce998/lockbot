# 洛克王国世界 MVP 开发方案 - 半自动战斗辅助

**版本**: v1.0  
**创建时间**: 2026-05-13  
**作者**: 智能 AI 电脑  
**状态**: 待审核  

**核心目标**：通过截图识别战斗状态，分析敌方精灵信息和行为模式，
给出技能决策建议（显示在 UI 上），用户手动点击执行。

---

## 1. 项目范围（MVP 限定）

### 1.1 MVP 做什么

| 功能 | 说明 |
|------|------|
| 战斗状态检测 | 检测是否进入/退出 PVP 战斗 |
| 敌方精灵识别 | 识别敌方精灵名称、属性、血量百分比 |
| 我方状态识别 | 识别我方精灵、当前能量、技能栏 4 个技能 |
| 敌方行为追踪 | 记录敌方已使用的技能，推测其携带的 4 个技能 |
| 敌方行为预测 | 基于敌方行为历史、血量、能量、精灵定位，预测其下回合行动 |
| 技能决策推荐 | 综合以上信息，从 4 个技能中推荐 1 个 |
| 决策原因展示 | 在 UI 上显示"为什么推荐这个技能" |

### 1.2 MVP 不做什么

| 功能 | 说明 |
|------|------|
| 自动点击 | 用户手动点击，辅助工具只推荐 |
| 自动排队 | 不自动进入匹配 |
| 跑图/资源 | 不在此阶段 |
| 多账号 | 单账号 |

---

## 2. BWIKI 真实数据结构

### 2.1 精灵数据结构（从 BWIKI 提取）

```
精灵详情页结构：
┌─────────────────────────────────────────┐
│ 编号 名称                                 │
│ - 属性                                    │
│                                           │
│ 种族值                                    │
│ - 生命 / 物攻 / 魔攻                      │
│ - 物防 / 魔防 / 速度                      │
│ - 身高范围 / 体重范围                     │
│                                           │
│ 精灵分布: xxx                             │
│ 描述                                      │
│                                           │
│ 特性                                      │
│ 特性名称                                  │
│ 特性描述                                  │
│                                           │
│ 进化链                                    │
│                                           │
│ 克制表 (克制/被克制/抵抗/被抵抗)            │
│                                           │
│ 技能列表 (可学习的全部技能)                  │
│ LV1  技能名  能耗  类型  威力             │
│         ✦效果描述                         │
│                                           │
│ 特殊技能 (非等级解锁)                      │
│ 技能名  能耗  类型  威力                  │
│         ✦效果描述                         │
└─────────────────────────────────────────┘
```

**示例 - 迪莫（光系）**：

```
001 迪莫 - 光
种族值: 582
生命:120 物攻:80 魔攻:80 物防:105 魔防:105 速度:92

特性: 最好的伙伴
    造成克制伤害后，获得攻防速+20%，并回复2能量。

技能示例:
LV1  抓挠       0  物攻  35   ✦造成物伤，自己回复1能量。
LV1  防御       1  防御  0    ✦减伤70%，应对攻击。
LV7  魔法增效   0  状态  0    ✦自己获得魔攻+70%。
LV16 棘突       3  魔攻  100  ✦对敌方精灵造成魔法伤害。
LV42 过曝       3  魔攻  60   ✦造成魔伤，每使用过1个其他系别技能，本技能威力永久+30。

特殊技能:
离子震荡  3  魔攻  90  ✦造成魔伤，本技能位于3号位时威力+40，传动1。
```

**示例 - 水蓝蓝（水系）**：

```
008 水蓝蓝 - 水
种族值: 372
生命:75 物攻:35 魔攻:76 物防:56 魔防:79 速度:51

特性: 浸润
    使用水系技能后，全技能能耗-1。
```

**示例 - 火神（火系）**：

```
007 火神 - 火
种族值: 613
生命:117 物攻:139 魔攻:61 物防:94 魔防:72 速度:130

特性: 助燃
    使用火系技能后，获得双攻+20%。
```

### 2.2 技能字段定义

从 BWIKI 提取的技能字段：

| 字段 | 说明 | 示例值 |
|------|------|--------|
| name | 技能名称 | 抓挠, 升龙咆哮, 防御 |
| unlock_level | 解锁等级（特殊技能为 0 或 null） | 1, 16, 42 |
| **energy_cost** | **能耗（0-7）** | 0, 1, 2, 3, 4, 5, 6, 7 |
| **damage_type** | **伤害类型** | 物攻, 魔攻, 防御, 状态 |
| power | 威力（状态/防御技能为 0） | 0-240 |
| effect | 效果描述 | ✦造成物伤，自己回复1能量。 |
| element | 技能属性 | 火, 水, 光, 草, 普通, ... |

**能耗分布统计**（基于 BWIKI 数据）：

| 能耗 | 占比 | 典型技能 | 说明 |
|------|------|---------|------|
| 0 | ~20% | 抓挠(35), 魔法增效, 借用 | 免费使用，部分回复能量 |
| 1 | ~30% | 龙吼(60), 防御, 怒火 | 低能耗，日常频繁使用 |
| 2 | ~25% | 锐利眼神, 扫尾(90), 假寐 | 中等能耗 |
| 3 | ~15% | 升龙咆哮(200), 棘突(100) | 较高能耗 |
| 4+ | ~10% | 光刃(120), 天洪(150), 吞噬(150) | 高能耗，需积攒 |

### 2.3 特殊机制汇总

| 机制 | 说明 | 示例 |
|------|------|------|
| **能量回复** | 使用后回复能量 | 抓挠: +1, 徒长: +10 |
| **应对** | 对手使用特定类型技能时触发额外效果 | 防御: 应对攻击减伤70% |
| **迸发** | 满足条件时额外效果 | 超导: 能耗-1 |
| **蓄力** | 需要 1 回合准备 | 升龙咆哮 |
| **传动** | 影响队伍中其他精灵 | 离子震荡: 传动1 |
| **位置效果** | 在特定栏位有加成 | 离子震荡(3号位): 威力+40 |
| **永久加成** | 战斗中持续生效 | 过曝: 每用其他系别技能威力+30 |
| **层数状态** | DOT 效果 | 灼烧(10层), 冻结(4层), 中毒(5层) |

---

## 3. 数据库设计（基于 BWIKI 真实数据）

### 3.1 核心表结构

#### 3.1.1 精灵表 (pets)

| 字段名 | 数据类型 | 约束 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| `id` | INTEGER | PK AUTOINCREMENT | - | 唯一标识 |
| `number` | INTEGER | - | NULL | 编号（如 1=迪莫） |
| `name` | VARCHAR(50) | NOT NULL UNIQUE | - | 精灵名称 |
| `element` | VARCHAR(20) | NOT NULL | - | 主属性（18种） |
| `sub_element` | VARCHAR(20) | - | NULL | 副属性（双属性精灵） |
| `base_stat_total` | INTEGER | - | NULL | 种族值总和 |
| `base_hp` | INTEGER | - | NULL | 种族值-生命 |
| `base_atk` | INTEGER | - | NULL | 种族值-物攻 |
| `base_spatk` | INTEGER | - | NULL | 种族值-魔攻 |
| `base_def` | INTEGER | - | NULL | 种族值-物防 |
| `base_spdef` | INTEGER | - | NULL | 种族值-魔防 |
| `base_spd` | INTEGER | - | NULL | 种族值-速度 |
| `trait_name` | VARCHAR(50) | - | NULL | 特性名称 |
| `trait_description` | TEXT | - | NULL | 特性描述 |
| `spawn_location` | VARCHAR(255) | - | NULL | 精灵分布 |
| `description` | TEXT | - | NULL | 精灵描述 |
| `evolution_chain` | TEXT | - | NULL | 进化链 JSON |
| `source_url` | VARCHAR(255) | - | NULL | BWIKI 页面 URL |
| `created_at` | DATETIME | - | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DATETIME | - | CURRENT_TIMESTAMP | 更新时间 |

#### 3.1.2 技能表 (skills)

| 字段名 | 数据类型 | 约束 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| `id` | INTEGER | PK AUTOINCREMENT | - | 唯一标识 |
| `name` | VARCHAR(50) | NOT NULL UNIQUE | - | 技能名称 |
| `element` | VARCHAR(20) | - | NULL | 技能属性 |
| `damage_type` | VARCHAR(20) | - | NULL | 物攻/魔攻/防御/状态 |
| `power` | INTEGER | - | 0 | 威力 |
| `energy_cost` | INTEGER | - | 0 | 能耗（0-7） |
| `has_charge` | BOOLEAN | - | FALSE | 是否蓄力技能 |
| `has_burst` | BOOLEAN | - | FALSE | 是否有迸发效果 |
| `has_counter` | BOOLEAN | - | FALSE | 是否有应对效果 |
| `has_transmission` | BOOLEAN | - | FALSE | 是否有传动效果 |
| `position_effect` | TEXT | - | NULL | 位置效果描述 |
| `permanent_effect` | TEXT | - | NULL | 永久效果描述 |
| `effect_description` | TEXT | - | NULL | 效果描述 |
| `unlock_level` | INTEGER | - | 0 | 解锁等级（0=特殊技能） |
| `created_at` | DATETIME | - | CURRENT_TIMESTAMP | 创建时间 |

#### 3.1.3 精灵-技能关联表 (pet_skills)

| 字段名 | 数据类型 | 约束 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| `id` | INTEGER | PK AUTOINCREMENT | - | 唯一标识 |
| `pet_id` | INTEGER | NOT NULL, FK | - | 精灵 ID |
| `skill_id` | INTEGER | NOT NULL, FK | - | 技能 ID |
| `unlock_level` | INTEGER | - | 0 | 解锁等级 |
| `is_equippable` | BOOLEAN | - | TRUE | 是否可装备 |
| UNIQUE | (pet_id, skill_id) | - | - | 防止重复 |

#### 3.1.4 属性克制表 (type_chart)

| 字段名 | 数据类型 | 约束 | 默认值 | 说明 |
|--------|---------|------|--------|------|
| `id` | INTEGER | PK AUTOINCREMENT | - | 唯一标识 |
| `atk_element` | VARCHAR(20) | NOT NULL | - | 攻击方属性 |
| `def_element` | VARCHAR(20) | NOT NULL | - | 防御方属性 |
| `multiplier` | REAL | NOT NULL | 1.0 | 倍率（2.0/0.5/0.0） |
| UNIQUE | (atk_element, def_element) | - | - | 防止重复 |

---

## 4. 战斗分析系统详细设计

### 4.1 核心问题：4 技能推测

每只精灵可学习的技能很多（如迪莫可学 60+ 个技能），但战斗中**只能携带 4 个**。
我们需要通过观察敌方已使用的技能，逐步缩小范围。

### 4.2 敌方技能推测算法

```
┌─────────────────────────────────────────────────────────────────┐
│                    敌方 4 技能推测算法                            │
│                                                                 │
│  Phase 1: 初始假设                                              │
│  ─────────────────                                              │
│  敌方精灵 = 火神                                                 │
│  可学习技能池 = 从数据库查询该精灵所有可装备技能                    │
│       = {火苗, 力量增效, 火焰切割, 防御, 吹火, ...} (约 50+ 个)   │
│                                                                 │
│  Phase 2: 观察与排除                                            │
│  ───────────────────                                            │
│  回合 1: 敌方使用 "火焰切割"                                      │
│    → 确认: 火焰切割 是敌方携带技能之一                             │
│    → 已确认技能: {火焰切割} (1/4)                               │
│                                                                 │
│  回合 2: 敌方使用 "防御"                                         │
│    → 确认: 防御 是敌方携带技能之一                                │
│    → 已确认技能: {火焰切割, 防御} (2/4)                         │
│                                                                 │
│  回合 3: 敌方使用 "锐利眼神"（未在已确认中）                       │
│    → 如果锐利眼神在火神可学习技能池中 → 确认                       │
│    → 已确认技能: {火焰切割, 防御, 锐利眼神} (3/4)               │
│                                                                 │
│  回合 4: 敌方使用 "锐利眼神"（重复）                               │
│    → 不增加新信息                                                 │
│                                                                 │
│  Phase 3: 预测剩余技能                                          │
│  ─────────────────────                                          │
│  已知 3/4 技能，第 4 个技能未知                                   │
│  剩余候选池 = 可学习技能池 - 已确认技能                           │
│                                                                 │
│  评分排序（每个候选技能）:                                         │
│    - 与已确认技能的协同性（如都有火系加成 → 高分）                 │
│    - 是否为该精灵的"热门"技能（可预设）                           │
│    - 是否能克制我方精灵                                           │
│    - 是否填补了技能类型空缺（如缺状态技能 → 高分）                 │
│                                                                 │
│  Phase 4: 行为模式识别                                          │
│  ───────────────────                                            │
│  记录敌方使用技能的频率和顺序:                                    │
│    - 如果敌方总是在高能量时使用高能耗技能 → 爆发型                │
│    - 如果敌方频繁使用状态技能 → 控制型                            │
│    - 如果敌方频繁使用应对技能 → 防守型                            │
│                                                                 │
│  预测下回合行动:                                                 │
│    if 敌方能量 >= 5:                                             │
│      → 可能使用高能耗攻击技能                                    │
│    elif 我方血量低:                                              │
│      → 可能使用击杀技能                                          │
│    elif 敌方有增益:                                              │
│      → 可能继续攻击                                              │
│    else:                                                         │
│      → 可能使用状态技能                                          │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 敌方精灵定位分析

```python
class EnemyAnalyzer:
    """敌方精灵分析器"""
    
    def analyze_position(self, enemy_pet, confirmed_skills):
        """
        分析敌方精灵的战斗定位
        
        定位类型：
        1. 爆发型 - 高能耗高伤害技能为主
        2. 消耗型 - DOT（灼烧/冻结/中毒）+ 防御
        3. 控制型 - 减益 + 状态技能为主
        4. 均衡型 - 攻击/防御/状态均衡搭配
        5. 应对型 - 以应对技能为核心
        """
        atk_skills = [s for s in confirmed_skills if s.damage_type in ('物攻', '魔攻')]
        def_skills = [s for s in confirmed_skills if s.damage_type == '防御']
        status_skills = [s for s in confirmed_skills if s.damage_type == '状态']
        
        total = len(confirmed_skills)
        if total == 0:
            return Position.UNKNOWN
        
        atk_ratio = len(atk_skills) / total
        def_ratio = len(def_skills) / total
        status_ratio = len(status_skills) / total
        
        # 判断定位
        if atk_ratio >= 0.7:
            return Position.AGGRESSIVE
        elif def_ratio >= 0.5:
            return Position.DEFENSIVE
        elif status_ratio >= 0.5:
            return Position.CONTROL
        elif any(s.is_dot for s in status_skills):
            return Position.DOT
        elif any(s.has_counter for s in confirmed_skills):
            return Position.COUNTER
        else:
            return Position.BALANCED
    
    def predict_next_action(self, enemy_pet, battle_state, position):
        """
        预测敌方下回合行动
        
        考虑因素：
        1. 敌方当前能量
        2. 敌方血量百分比
        3. 我方血量百分比
        4. 敌方定位
        5. 已使用技能历史（冷却）
        6. 天气/场地效果
        """
        energy = battle_state.enemy_energy
        enemy_hp = battle_state.enemy_hp_percent
        my_hp = battle_state.my_hp_percent
        position = self.analyze_position(enemy_pet, battle_state.confirmed_skills)
        
        # 候选技能评分
        candidates = []
        for skill in battle_state.confirmed_skills:
            score = 0
            
            # 能量检查
            if skill.energy_cost > energy:
                continue  # 能量不足，不可用
            
            # 基础分：伤害技能看威力，状态技能看价值
            if skill.damage_type in ('物攻', '魔攻'):
                score = skill.power * self._type_mult(skill, enemy_pet, battle_state)
            else:
                score = self._status_value(skill, battle_state)
            
            # 定位加权
            if position == Position.AGGRESSIVE:
                if skill.damage_type in ('物攻', '魔攻'):
                    score *= 1.5
            elif position == Position.DEFENSIVE:
                if skill.damage_type == '防御':
                    score *= 1.5
            elif position == Position.CONTROL:
                if skill.damage_type == '状态':
                    score *= 1.5
            
            # 血量因素
            if enemy_hp < 0.3:
                if skill.is_heal or skill.is_energy_recover:
                    score *= 2.0
            if my_hp < 0.3:
                if skill.damage_type in ('物攻', '魔攻') and skill.power > 100:
                    score *= 2.0  # 可能使用击杀技能
            
            # 能量因素
            if energy >= 5 and skill.energy_cost >= 4:
                score *= 1.3  # 高能量时更可能用高能耗技能
            
            candidates.append((skill, score))
        
        # 按分数排序
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return candidates[0][0]  # 返回最可能的技能
        return None
```

### 4.4 我方决策引擎（策略模式）

```python
# ============================================================
# 策略接口
# ============================================================

class DecisionStrategy(ABC):
    """决策策略基类"""
    
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def decide(self, context: BattleContext) -> DecisionResult:
        """
        做出决策
        
        :param context: 战斗上下文（包含所有状态信息）
        :return: 决策结果（推荐技能 + 原因）
        """
        pass


# ============================================================
# 策略 1: 贪心策略（Greedy）- MVP 默认
# ============================================================

class GreedyStrategy(DecisionStrategy):
    """
    贪心策略：选择当前回合期望收益最高的技能
    
    评分维度：
    1. 属性克制倍率（最重要）
    2. 有效伤害（威力 × 克制倍率 × 命中）
    3. 能量利用效率（威力 / 能耗）
    4. 当前状态需求（低血量回复、高血量输出）
    5. 技能位置效果
    6. 特殊机制（迸发/蓄力/永久加成）
    """
    
    def name(self) -> str:
        return "贪心策略"
    
    def decide(self, ctx: BattleContext) -> DecisionResult:
        best_skill = None
        best_score = -float('inf')
        best_reasons = []
        
        for skill in ctx.my_equipped_skills:
            score = 0
            reasons = []
            
            # --- 1. 能量检查 ---
            effective_cost = self._calc_effective_cost(skill, ctx)
            if effective_cost > ctx.my_energy:
                continue  # 能量不足，跳过
            
            # --- 2. 属性克制（最高权重）---
            type_mult = self._get_type_multiplier(skill.element, ctx.enemy.element)
            if type_mult >= 2.0:
                score += 100 * type_mult
                reasons.append(f"克制 ×{type_mult}")
            elif type_mult <= 0.5:
                score *= 0.3
                reasons.append(f"被抵抗 ×{type_mult}")
            
            # --- 3. 伤害计算 ---
            if skill.damage_type in ('物攻', '魔攻'):
                base_dmg = self._calc_damage(skill, ctx)
                score += base_dmg * type_mult
                reasons.append(f"期望伤害 {base_dmg:.0f}")
            
            # --- 4. 能量效率 ---
            if effective_cost > 0:
                efficiency = (skill.power * type_mult) / effective_cost
                score += efficiency * 5
                reasons.append(f"能量效率 {efficiency:.1f}")
            
            # --- 5. 位置效果 ---
            pos_bonus = self._calc_position_bonus(skill, ctx)
            score += pos_bonus
            if pos_bonus > 0:
                reasons.append(f"位置加成 +{pos_bonus}")
            
            # --- 6. 特殊机制 ---
            # 迸发
            if skill.has_burst:
                burst_bonus = self._calc_burst_bonus(skill, ctx)
                score += burst_bonus
                if burst_bonus > 0:
                    reasons.append(f"迸发 +{burst_bonus}")
            
            # 蓄力
            if skill.has_charge and not ctx.my_is_charging:
                score -= 30  # 蓄力需要等待 1 回合
                reasons.append("需蓄力")
            
            # --- 7. 血量因素 ---
            my_hp_ratio = ctx.my_hp / ctx.my_max_hp
            if my_hp_ratio < 0.3:
                if skill.is_heal or skill.is_energy_recover:
                    score *= 2.0
                    reasons.append("低血量优先回复")
            
            # --- 8. 应对预判 ---
            counter_value = self._calc_counter_value(skill, ctx)
            score += counter_value
            if counter_value > 0:
                reasons.append(f"应对价值 +{counter_value}")
            
            # --- 9. 敌方行为预测 ---
            # 如果预测敌方下回合用高伤害技能 → 优先防御/应对
            predicted_enemy = ctx.enemy_prediction
            if predicted_enemy and predicted_enemy.damage_type in ('物攻', '魔攻'):
                if skill.damage_type == '防御':
                    score *= 1.5
                    reasons.append("应对敌方攻击")
            
            # --- 10. 永久加成 ---
            permanent_value = self._calc_permanent_value(skill, ctx)
            score += permanent_value
            if permanent_value > 0:
                reasons.append(f"永久加成 +{permanent_value}")
            
            if score > best_score:
                best_score = score
                best_skill = skill
                best_reasons = reasons
        
        return DecisionResult(
            skill=best_skill,
            score=best_score,
            reasons=best_reasons,
            strategy=self.name()
        )
    
    def _calc_damage(self, skill, ctx) -> float:
        """计算期望伤害"""
        # 简化版伤害公式
        atk_stat = ctx.my_atk if skill.damage_type == '物攻' else ctx.my_spatk
        def_stat = ctx.enemy_def if skill.damage_type == '物攻' else ctx.enemy_spdef
        
        base_dmg = skill.power * (atk_stat / max(def_stat, 1))
        
        # 随机波动 0.85-1.0
        base_dmg *= 0.925
        
        # 状态修正
        if ctx.my_atk_buff > 0 and skill.damage_type == '物攻':
            base_dmg *= (1 + ctx.my_atk_buff * 0.2)
        if ctx.enemy_def_debuff > 0:
            base_dmg *= (1 + ctx.enemy_def_debuff * 0.2)
        
        return base_dmg
    
    def _calc_position_bonus(self, skill, ctx) -> float:
        """计算位置效果加成"""
        pos = ctx.my_skill_positions.get(skill.name)
        if not pos:
            return 0
        
        # 离子震荡: 3号位威力+40
        if skill.name == '离子震荡' and pos == 3:
            return 40
        
        # 械斗: 1号位威力+60
        if skill.name == '械斗' and pos == 1:
            return 60
        
        # 啮合传递: 1号或3号位物攻+60%
        if skill.name == '啮合传递' and pos in (1, 3):
            return ctx.my_atk * 0.6
        
        return 0
    
    def _calc_burst_bonus(self, skill, ctx) -> float:
        """计算迸发加成"""
        # 超导: 能耗-1 → 提高能量效率
        if skill.name == '超导':
            return skill.power * 0.1
        
        # 电弧: 威力+40
        if skill.name == '电弧':
            return 40
        
        # 天旋地转: 威力+30
        if skill.name == '天旋地转':
            return 30
        
        return 0
    
    def _calc_counter_value(self, skill, ctx) -> float:
        """计算应对价值"""
        if not skill.has_counter:
            return 0
        
        # 预测敌方攻击 → 应对技能价值高
        if ctx.enemy_prediction and ctx.enemy_prediction.damage_type in ('物攻', '魔攻'):
            return 50
        
        # 预测敌方状态 → 应对状态技能价值高
        if ctx.enemy_prediction and ctx.enemy_prediction.damage_type == '状态':
            return 30
        
        return 10  # 基础分


# ============================================================
# 策略 2: 保守策略（Conservative）
# ============================================================

class ConservativeStrategy(DecisionStrategy):
    """
    保守策略：优先保证存活，次优输出
    
    特点：
    - 血量低于 50% 时优先防御/回复
    - 优先使用低能耗技能保持灵活性
    - 只有在优势明显时才使用高能耗技能
    """
    
    def name(self) -> str:
        return "保守策略"
    
    def decide(self, ctx: BattleContext) -> DecisionResult:
        my_hp_ratio = ctx.my_hp / ctx.my_max_hp
        
        if my_hp_ratio < 0.3:
            # 危急状态：优先回复/防御
            return self._survival_mode(ctx)
        elif my_hp_ratio < 0.5:
            # 危险状态：保守输出
            return self._cautious_attack(ctx)
        else:
            # 安全状态：正常输出
            return GreedyStrategy().decide(ctx)
    
    def _survival_mode(self, ctx):
        # 找回复/防御技能
        for skill in ctx.my_equipped_skills:
            if skill.is_heal or skill.damage_type == '防御':
                if skill.energy_cost <= ctx.my_energy:
                    return DecisionResult(
                        skill=skill,
                        score=999,
                        reasons=["危急状态，优先保命"],
                        strategy=self.name()
                    )
        # 没有回复技能，用最低能耗
        return self._lowest_cost_skill(ctx)
    
    def _cautious_attack(self, ctx):
        # 优先低能耗克制技能
        best = None
        best_score = 0
        for skill in ctx.my_equipped_skills:
            if skill.damage_type in ('物攻', '魔攻') and skill.energy_cost <= 2:
                if skill.energy_cost <= ctx.my_energy:
                    score = skill.power * self._type_mult(skill, ctx)
                    if score > best_score:
                        best_score = score
                        best = skill
        if best:
            return DecisionResult(skill=best, score=best_score,
                                reasons=["危险状态，低能耗克制攻击"],
                                strategy=self.name())
        return GreedyStrategy().decide(ctx)
    
    def _lowest_cost_skill(self, ctx):
        min_cost = float('inf')
        best = None
        for skill in ctx.my_equipped_skills:
            if skill.energy_cost <= ctx.my_energy and skill.energy_cost < min_cost:
                min_cost = skill.energy_cost
                best = skill
        return DecisionResult(skill=best, score=0,
                            reasons=["使用最低能耗技能"],
                            strategy=self.name())


# ============================================================
# 策略 3: 激进策略（Aggressive）
# ============================================================

class AggressiveStrategy(DecisionStrategy):
    """
    激进策略：优先最大化伤害输出
    
    特点：
    - 优先使用最高伤害技能
    - 不考虑能量保留
    - 低血量时反而更激进（赌博式输出）
    """
    
    def name(self) -> str:
        return "激进策略"
    
    def decide(self, ctx: BattleContext) -> DecisionResult:
        best_skill = None
        best_score = -float('inf')
        reasons = []
        
        for skill in ctx.my_equipped_skills:
            if skill.energy_cost > ctx.my_energy:
                continue
            
            score = skill.power * self._type_mult(skill, ctx)
            
            # 激进加成：高伤害优先
            if skill.power >= 100:
                score *= 1.5
                reasons.append("高伤害优先")
            
            # 暴击期望
            if skill.has_burst:
                score *= 1.3
            
            if score > best_score:
                best_score = score
                best_skill = skill
                reasons = ["激进策略：最大化输出"]
        
        return DecisionResult(skill=best_skill, score=best_score,
                            reasons=reasons, strategy=self.name())


# ============================================================
# 策略管理器（支持运行时切换）
# ============================================================

class StrategyManager:
    """策略管理器"""
    
    def __init__(self):
        self.strategies = {
            'greedy': GreedyStrategy(),
            'conservative': ConservativeStrategy(),
            'aggressive': AggressiveStrategy(),
        }
        self.current_strategy = 'greedy'
    
    def set_strategy(self, name: str):
        if name not in self.strategies:
            raise ValueError(f"未知策略: {name}")
        self.current_strategy = name
        logger.info(f"切换策略: {name}")
    
    def decide(self, ctx: BattleContext) -> DecisionResult:
        return self.strategies[self.current_strategy].decide(ctx)
    
    def list_strategies(self) -> list:
        return [
            {'name': k, 'display': v.name()}
            for k, v in self.strategies.items()
        ]
```

---

## 5. 决策算法详解

### 5.1 决策流程图

```
┌──────────────────────────────────────────────────────────────────┐
│                      决策流程（每回合）                            │
│                                                                  │
│  1. 截图 → 识别战斗状态                                           │
│     ├─ 我方精灵: 名称、属性、血量、能量                            │
│     ├─ 敌方精灵: 名称、属性、血量百分比                            │
│     └─ 技能栏: 4 个技能的名称/位置                                │
│                                                                  │
│  2. 更新敌方信息                                                  │
│     ├─ 记录敌方本回合使用的技能                                    │
│     ├─ 更新已确认技能列表（1/4, 2/4, 3/4, 4/4）                  │
│     └─ 更新敌方精灵定位（爆发/消耗/控制/均衡/应对）                │
│                                                                  │
│  3. 预测敌方行动                                                  │
│     ├─ 输入: 敌方能量、血量、定位、已确认技能                       │
│     ├─ 输出: 最可能使用的技能                                     │
│     └─ 置信度: 高/中/低                                           │
│                                                                  │
│  4. 评估我方每个可选技能                                          │
│     ├─ 检查能量是否足够                                            │
│     ├─ 计算属性克制倍率                                           │
│     ├─ 计算期望伤害                                               │
│     ├─ 计算能量效率                                               │
│     ├─ 检查位置效果                                               │
│     ├─ 检查迸发/蓄力/应对等特殊机制                               │
│     ├─ 考虑血量因素                                               │
│     └─ 考虑永久加成                                               │
│                                                                  │
│  5. 选择最佳技能                                                  │
│     ├─ 按当前策略评分                                             │
│     ├─ 排序 → 选择最高分                                          │
│     └─ 生成推荐原因                                               │
│                                                                  │
│  6. 展示结果                                                      │
│     ├─ 推荐技能名称                                               │
│     ├─ 推荐理由列表                                               │
│     ├─ 克制信息                                                   │
│     └─ 敌方预测信息                                               │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 评分公式（贪心策略）

```
技能评分 = 基础分 + 加成分

基础分：
  - 属性克制: power × type_multiplier × 10
  - 期望伤害: calc_damage() × 1
  - 能量效率: (power × type_multiplier / energy_cost) × 5

加成分：
  - 位置效果: +position_bonus
  - 迸发效果: +burst_bonus
  - 应对价值: +counter_value
  - 永久加成: +permanent_value
  - 低血量回复: ×2.0
  - 敌方攻击预测 → 防御: ×1.5

惩罚项：
  - 被抵抗: ×0.3
  - 需要蓄力: -30

最终评分 = 基础分 + 加成分 - 惩罚项
```

---

## 6. 战斗状态跟踪

### 6.1 战斗上下文

```python
@dataclass
class BattleContext:
    """战斗上下文 - 包含所有决策需要的信息"""
    
    # === 我方状态 ===
    my_pet: Pet                    # 我方精灵
    my_hp: int                     # 当前血量
    my_max_hp: int                 # 最大血量
    my_energy: int                 # 当前能量
    my_atk: int                    # 当前物攻（含 buff）
    my_spatk: int                  # 当前魔攻（含 buff）
    my_def: int                    # 当前物防（含 buff）
    my_spdef: int                  # 当前魔防（含 buff）
    my_spd: int                    # 当前速度（含 buff）
    my_atk_buff: int               # 物攻增益层数
    my_spatk_buff: int             # 魔攻增益层数
    my_def_debuff: int             # 防御减益层数
    my_equipped_skills: list       # 我方携带的 4 个技能
    my_skill_positions: dict       # 技能位置 {技能名: 位置}
    my_is_charging: bool           # 是否在蓄力中
    my_permanent_bonuses: dict     # 永久加成
    
    # === 敌方状态 ===
    enemy_pet: Pet                 # 敌方精灵
    enemy_hp_percent: float        # 血量百分比
    enemy_energy: int              # 推测能量
    enemy_element: str             # 属性
    enemy_def: int                 # 物防
    enemy_spdef: int               # 魔防
    enemy_atk: int                 # 物攻
    enemy_spatk: int               # 魔攻
    enemy_spd: int                 # 速度
    
    # === 敌方技能推测 ===
    enemy_confirmed_skills: list   # 已确认的敌方携带技能
    enemy_remaining_candidates: list  # 剩余候选技能
    enemy_position: Position       # 敌方定位
    enemy_prediction: Skill        # 预测敌方下回合使用的技能
    enemy_prediction_confidence: float  # 预测置信度
    
    # === 战斗历史 ===
    battle_log: list               # 本战斗历史记录
    turn_number: int               # 当前回合数
    my_last_skill: str             # 我上次使用的技能
    enemy_last_skill: str          # 敌方上次使用的技能
    
    # === 环境 ===
    weather: str                   # 天气
    field_effect: str              # 场地效果
```

### 6.2 敌方技能追踪

```python
class EnemySkillTracker:
    """敌方技能追踪器"""
    
    def __init__(self, enemy_pet: Pet):
        self.enemy_pet = enemy_pet
        self.confirmed_skills = []        # 已确认携带的技能
        self.usage_history = []           # 使用历史 [(skill_name, turn), ...]
        self.skill_usage_count = {}       # 每个技能使用次数
        
    def record_skill(self, skill_name: str, turn: int):
        """记录敌方使用的技能"""
        self.usage_history.append((skill_name, turn))
        self.skill_usage_count[skill_name] = \
            self.skill_usage_count.get(skill_name, 0) + 1
        
        # 确认这是敌方携带的技能
        if skill_name not in [s.name for s in self.confirmed_skills]:
            # 从数据库查询该技能
            skill = self._get_skill_from_db(skill_name)
            if skill:
                self.confirmed_skills.append(skill)
    
    @property
    def confirmed_count(self) -> int:
        return len(self.confirmed_skills)
    
    @property
    def is_complete(self) -> bool:
        return self.confirmed_count >= 4
    
    def get_candidates(self) -> list:
        """获取第 N+1 个技能的候选列表"""
        if self.is_complete:
            return []
        
        # 所有可学习技能 - 已确认技能
        all_skills = self.enemy_pet.learnable_skills
        confirmed_names = {s.name for s in self.confirmed_skills}
        return [s for s in all_skills if s.name not in confirmed_names]
    
    def analyze_position(self) -> Position:
        """分析敌方定位"""
        if not self.confirmed_skills:
            return Position.UNKNOWN
        
        atk = [s for s in self.confirmed_skills if s.damage_type in ('物攻', '魔攻')]
        defense = [s for s in self.confirmed_skills if s.damage_type == '防御']
        status = [s for s in self.confirmed_skills if s.damage_type == '状态']
        
        total = len(self.confirmed_skills)
        if total >= 3:
            if len(atk) / total >= 0.7:
                return Position.AGGRESSIVE
            elif len(defense) / total >= 0.5:
                return Position.DEFENSIVE
            elif len(status) / total >= 0.5:
                return Position.CONTROL
            elif any(s.has_counter for s in self.confirmed_skills):
                return Position.COUNTER
        
        return Position.BALANCED
    
    def predict_next(self, battle_state) -> Skill:
        """预测敌方下回合使用的技能"""
        if not self.confirmed_skills:
            return None
        
        energy = battle_state.enemy_energy
        candidates = []
        
        for skill in self.confirmed_skills:
            if skill.energy_cost > energy:
                continue  # 能量不足
            
            score = 0
            
            # 基础分
            if skill.damage_type in ('物攻', '魔攻'):
                score = skill.power
            elif skill.is_heal:
                score = 50
            
            # 定位加权
            position = self.analyze_position()
            if position == Position.AGGRESSIVE and skill.damage_type in ('物攻', '魔攻'):
                score *= 1.5
            elif position == Position.DEFENSIVE and skill.damage_type == '防御':
                score *= 1.5
            
            # 低血量时倾向回复
            if battle_state.enemy_hp_percent < 0.3:
                if skill.is_heal or skill.is_energy_recover:
                    score *= 2.0
            
            # 能量充足时用高能耗技能
            if energy >= 5 and skill.energy_cost >= 4:
                score *= 1.3
            
            candidates.append((skill, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0] if candidates else None
```

---

## 7. 识别模块设计

### 7.1 需要识别的 UI 元素

| 元素 | 识别方法 | 说明 |
|------|---------|------|
| 战斗状态 | 模板匹配 | 检测技能栏、血条等战斗 UI |
| 敌方精灵名 | OCR | 识别精灵名称文本 |
| 敌方属性 | 模板匹配 | 属性图标/颜色 |
| 敌方血量 | 图像处理 | 血条长度比例 |
| 我方精灵名 | OCR | 识别精灵名称文本 |
| 我方能量 | 图像处理 | 能量条长度/数字识别 |
| 我方 4 个技能 | OCR + 模板匹配 | 技能名称文本 |
| 敌方使用技能 | OCR | 战斗日志/动画文字 |

### 7.2 技能栏识别

```
技能栏 UI 结构（假设）：
┌─────────────────────────────────────────┐
│  [技能1]    [技能2]    [技能3]    [技能4]  │
│   位置1      位置2      位置3      位置4   │
│                                         │
│  坐标示例（1920×1080）：                  │
│  (800, 900) (950, 900) (1100, 900) (1250, 900) │
└─────────────────────────────────────────┘

识别步骤：
1. 裁剪技能栏区域 ROI
2. 对每个技能按钮：
   a. OCR 识别技能名称文本
   b. 模板匹配确认技能图标（辅助验证）
   c. 记录技能名称和栏位位置
3. 返回 {1: "技能名", 2: "技能名", 3: "技能名", 4: "技能名"}
```

---

## 8. 项目文件结构（MVP）

```
lockbot/
├── core/
│   ├── capture.py           # 屏幕捕获
│   ├── recognizer.py        # 图像识别（OCR + 模板匹配）
│   ├── controller.py        # 输入控制（预留，MVP 不自动点击）
│   └── database.py          # 数据库管理
│
├── battle/
│   ├── context.py           # 战斗上下文定义
│   ├── tracker.py           # 敌方技能追踪器
│   ├── analyzer.py          # 敌方定位分析器
│   └── decision.py          # 决策引擎（策略模式）
│       ├── __init__.py
│       ├── base.py          # 策略基类
│       ├── greedy.py        # 贪心策略
│       ├── conservative.py  # 保守策略
│       └── aggressive.py    # 激进策略
│
├── data/
│   ├── lockbot.db           # SQLite 数据库
│   ├── export/              # 爬虫导出
│   └── templates/           # 识别模板
│       ├── hp_bar/          # 血条模板
│       ├── energy_bar/      # 能量条模板
│       ├── skill_slots/     # 技能栏模板
│       └── elements/        # 属性图标
│
├── ui/
│   └── decision_panel.py    # 决策展示面板（Phase 1 预留）
│
├── utils/
│   ├── anti_detect.py       # 反检测
│   └── logger.py            # 日志
│
├── scripts/
│   ├── bwiki_crawler.py     # BWIKI 数据爬虫
│   └── init_db.py           # 数据库初始化
│
├── config.yaml
├── requirements.txt
└── main.py                  # 主入口
```

---

## 9. 开发计划

### Phase 1 - MVP（1-2 周）

| 优先级 | 任务 | 预估工时 | 说明 |
|--------|------|---------|------|
| P0 | 数据库模型重写 | 4h | 基于 BWIKI 真实数据结构 |
| P0 | 爬虫数据导入 | 2h | 导入已爬取的 475 宠物 + 485 技能 |
| P0 | 战斗上下文定义 | 4h | BattleContext 数据类 |
| P0 | 敌方技能追踪器 | 6h | EnemySkillTracker |
| P0 | 决策引擎框架 | 4h | StrategyManager + 策略基类 |
| P0 | 贪心策略实现 | 8h | GreedyStrategy 完整实现 |
| P0 | 保守策略实现 | 4h | ConservativeStrategy |
| P0 | 激进策略实现 | 2h | AggressiveStrategy |
| P1 | 屏幕捕获模块 | 6h | 战斗状态检测 |
| P1 | 技能栏识别 | 8h | OCR 识别技能名称 |
| P1 | 敌方精灵识别 | 6h | 名称 + 属性识别 |
| P1 | 血量/能量识别 | 6h | 血条/能量条图像处理 |
| P2 | 决策展示 UI | 8h | 显示推荐结果 |
| P2 | 策略切换 UI | 2h | 运行时切换策略 |

---

## 10. 需要用户确认的问题

| # | 问题 | 我的假设 |
|---|------|---------|
| 1 | 精灵初始能量是多少？ | 大部分精灵默认 10 能量，幔尾兽等特殊精灵 5 能量 |
| 2 | 每回合恢复多少能量？ | 2-3 能量（需要实测确认精确值） |
| 3 | 能量上限是多少？ | 约 10-12（需要实测） |
| 4 | 先后手判定公式是什么？ | 技能能耗高的先手？还是速度优先？ |
| 5 | 敌方使用技能时能看到技能名吗？ | 战斗动画中显示 |
| 6 | 技能栏的 OCR 识别是否可行？ | 需要用户提供游戏截图验证 |
| 7 | 双属性精灵存在吗？ | BWIKI 中部分精灵有副属性 |

---

**文档版本**: v1.0  
**创建日期**: 2026-05-13  
**数据来源**: BWIKI 洛克王国世界 (https://wiki.biligame.com/rocom/)  
**数据协议**: CC BY-NC-SA 4.0
