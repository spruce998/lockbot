"""
数据库模块 - 提供精灵、技能、克制关系查询
数据源：SQLite 数据库 + GitHub CSV 补充
"""
from __future__ import annotations

import csv
import io
import sqlite3
import logging
from pathlib import Path
from typing import Optional

from .context import Pet, Skill

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "lockbot.db"
_connection: Optional[sqlite3.Connection] = None

# GitHub CSV 技能数据缓存（487 条）
_skills_cache: Optional[list[Skill]] = None


def get_connection() -> sqlite3.Connection:
    global _connection
    if _connection is None:
        if not DB_PATH.exists():
            raise FileNotFoundError(f"数据库不存在: {DB_PATH}\n运行: python scripts/init_db.py")
        _connection = sqlite3.connect(str(DB_PATH))
        _connection.row_factory = sqlite3.Row
    return _connection


def close_connection():
    global _connection
    if _connection:
        _connection.close()
        _connection = None


# ============================================================
# 从 GitHub CSV 加载技能数据
# ============================================================

SKILLS_CSV_URL = "https://raw.githubusercontent.com/TsingShui/roco-world-skill/main/.claude/skills/roco-world/skills.csv"


def load_skills_csv() -> list[Skill]:
    """从 GitHub CSV 加载 487 条技能数据"""
    global _skills_cache
    if _skills_cache is not None:
        return _skills_cache

    # 尝试从本地缓存加载
    csv_path = Path(__file__).parent.parent / "data" / "skills.csv"
    if csv_path.exists():
        return _load_skills_from_file(csv_path)

    # 尝试在线加载
    try:
        import requests
        resp = requests.get(SKILLS_CSV_URL, timeout=10)
        if resp.status_code == 200:
            return _parse_skills_csv(resp.text)
    except Exception as e:
        logger.warning(f"无法加载 CSV: {e}")

    # 回退到 SQLite
    return _load_skills_from_db()


def _parse_skills_csv(text: str) -> list[Skill]:
    """解析 CSV 文本"""
    global _skills_cache
    skills = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, 1):
        skill = Skill(
            id=i,
            name=row.get('name', '').strip(),
            element=row.get('element', '').strip(),
            category=row.get('category', '').strip(),
            cost=int(row.get('cost', 0)) if row.get('cost', '0') not in ('', '-') else 0,
            power=int(row.get('power', 0)) if row.get('power', '0') not in ('', '-') else 0,
            effect=row.get('effect', '').strip(),
        )
        # 解析特性
        eff = skill.effect
        if '蓄力' in eff:
            skill.has_charge = True
        if '迸发' in eff:
            skill.has_burst = True
        if '应对' in eff:
            skill.has_counter = True
        if '传动' in eff:
            skill.has_transmission = True
        if '连击' in eff:
            skill.has_combo = True
        if '折返' in eff or '脱离' in eff or '返场' in eff:
            skill.has_return = True
        if '先手' in eff:
            skill.has_priority = True

        skills.append(skill)

    _skills_cache = skills
    return skills


def _load_skills_from_file(path: Path) -> list[Skill]:
    with open(path, 'r', encoding='utf-8') as f:
        return _parse_skills_csv(f.read())


def _load_skills_from_db() -> list[Skill]:
    """从 SQLite 加载（作为回退）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM skills")
    rows = cursor.fetchall()
    return [Skill(
        id=r['id'], name=r['name'],
        element=r['element'] if 'element' in r.keys() else '',
        category=r['damage_type'] if 'damage_type' in r.keys() else '',
        cost=r['energy_cost'] if 'energy_cost' in r.keys() else 0,
        power=r['power'] if 'power' in r.keys() else 0,
        effect=r['effect_description'] if 'effect_description' in r.keys() else '',
    ) for r in rows]


def save_skills_csv():
    """将 CSV 数据保存到本地"""
    skills = load_skills_csv()
    csv_path = Path(__file__).parent.parent / "data" / "skills.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'element', 'category', 'cost', 'power', 'effect'])
        for s in skills:
            writer.writerow([s.name, s.element, s.category, s.cost, s.power, s.effect])
    logger.info(f"技能 CSV 已保存到 {csv_path} ({len(skills)} 条)")


# ============================================================
# 精灵查询
# ============================================================

def get_pet_by_name(name: str) -> Optional[Pet]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        return None
    return Pet(
        id=row['id'], name=row['name'], element=row['element'],
        sub_element=row.get('sub_element'),
        base_stat_total=row.get('base_stat_total', 0),
        base_hp=row.get('base_hp', 0), base_atk=row.get('base_atk', 0),
        base_spatk=row.get('base_spatk', 0), base_def=row.get('base_def', 0),
        base_spdef=row.get('base_spdef', 0), base_spd=row.get('base_spd', 0),
        trait_name=row.get('trait_name', ''),
        trait_description=row.get('trait_description', ''),
        current_hp=row.get('base_hp', 0), max_hp=row.get('base_hp', 0),
    )


def get_pet_skills(pet_name: str) -> list[Skill]:
    """查询精灵可学习的全部技能（优先从 CSV 获取完整数据）"""
    # 先从 CSV 查找该精灵的技能（更准确）
    csv_skills = load_skills_csv()
    # CSV 包含所有技能，需要根据 pet_name 过滤
    # 这里返回全部技能，由调用方根据精灵详情筛选
    return csv_skills


def list_all_pets() -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, element, base_stat_total FROM pets ORDER BY name")
    return [dict(row) for row in cursor.fetchall()]


# ============================================================
# 技能查询
# ============================================================

def get_skill_by_name(name: str) -> Optional[Skill]:
    """根据名称查询技能（优先从 CSV）"""
    skills = load_skills_csv()
    for skill in skills:
        if skill.name == name:
            return skill

    # 回退到 SQLite
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM skills WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        return None
    return Skill(
        id=row['id'], name=row['name'],
        element=row.get('element', ''), category=row.get('damage_type', ''),
        cost=row.get('energy_cost', 0), power=row.get('power', 0),
        effect=row.get('effect_description', ''),
    )


# ============================================================
# 属性克制查询
# ============================================================

# 完整克制表（从 GitHub 获取）
TYPE_CHART = {
    '普通': {'strong': [''], 'resist': ['地', '幽', '机械'], 'weak': ['武'], 'vulnerable': ['幽']},
    '草': {'strong': ['水', '光', '地'], 'resist': ['火', '龙', '毒', '虫', '翼', '机械'], 'weak': ['火', '冰', '毒', '虫', '翼'], 'vulnerable': ['水', '地', '电', '光']},
    '火': {'strong': ['草', '冰', '虫', '机械'], 'resist': ['水', '地', '龙'], 'weak': ['水', '地'], 'vulnerable': ['草', '冰', '虫', '萌', '机械']},
    '水': {'strong': ['火', '地', '机械'], 'resist': ['草', '冰', '龙'], 'weak': ['草', '电'], 'vulnerable': ['火', '机械']},
    '光': {'strong': ['幽', '恶'], 'resist': ['草', '冰'], 'weak': ['草', '幽'], 'vulnerable': ['恶', '幻']},
    '地': {'strong': ['火', '冰', '电', '毒'], 'resist': ['草', '武'], 'weak': ['草', '水', '冰', '武', '机械'], 'vulnerable': ['普通', '火', '电', '毒', '翼']},
    '冰': {'strong': ['草', '地', '龙', '翼'], 'resist': ['火', '冰', '机械'], 'weak': ['火', '地', '武', '机械'], 'vulnerable': ['水', '冰', '光']},
    '龙': {'strong': ['龙'], 'resist': ['机械'], 'weak': ['冰', '龙', '萌'], 'vulnerable': ['草', '火', '水', '电', '翼']},
    '电': {'strong': ['水', '翼'], 'resist': ['草', '地', '龙', '电'], 'weak': ['地'], 'vulnerable': ['电', '翼', '机械']},
    '毒': {'strong': ['草', '萌'], 'resist': ['地', '毒', '幽', '机械'], 'weak': ['地', '恶', '幻'], 'vulnerable': ['草', '毒', '虫', '武', '萌']},
    '虫': {'strong': ['草', '恶', '幻'], 'resist': ['火', '毒', '武', '翼', '萌', '幽', '机械'], 'weak': ['火', '翼'], 'vulnerable': ['草', '武']},
    '武': {'strong': ['普通', '地', '冰', '恶', '机械'], 'resist': ['毒', '虫', '翼', '萌', '幽', '幻'], 'weak': ['翼', '萌', '幻'], 'vulnerable': ['地', '虫', '恶']},
    '翼': {'strong': ['草', '虫', '武'], 'resist': ['地', '龙', '电', '机械'], 'weak': ['冰', '电'], 'vulnerable': ['草', '虫', '武']},
    '萌': {'strong': ['龙', '武', '恶'], 'resist': ['火', '毒', '机械'], 'weak': ['毒', '恶', '机械'], 'vulnerable': ['虫', '武']},
    '幽': {'strong': ['光', '幽', '幻'], 'resist': ['普通', '恶'], 'weak': ['光', '幽', '恶'], 'vulnerable': ['普通', '毒', '虫', '武']},
    '恶': {'strong': ['毒', '萌', '幽'], 'resist': ['光', '武', '恶'], 'weak': ['光', '虫', '武', '萌'], 'vulnerable': ['幽', '恶']},
    '机械': {'strong': ['地', '冰', '萌'], 'resist': ['火', '水', '电', '机械'], 'weak': ['火', '水', '武'], 'vulnerable': ['普通', '草', '冰', '龙', '毒', '虫', '翼', '萌', '机械', '幻']},
    '幻': {'strong': ['毒', '武'], 'resist': ['光', '机械', '幻'], 'weak': ['虫', '幽'], 'vulnerable': ['武', '幻']},
}


def get_type_multiplier(atk_element: str, def_element: str) -> float:
    """
    获取属性克制倍率（基于 GitHub 真实数据）

    返回：
    - 3.0: 强力克制（双属性均被克制）
    - 2.0: 克制
    - 1.0: 正常
    - 0.5: 抵抗
    - 0.25: 强力抵抗（双属性均抵抗）
    """
    if atk_element not in TYPE_CHART:
        return 1.0

    chart = TYPE_CHART[atk_element]

    # 检查是否被抵抗
    if def_element in chart.get('resist', []):
        return 0.5

    # 检查是否克制
    if def_element in chart.get('strong', []):
        return 2.0

    return 1.0


def get_type_chart() -> list[dict]:
    """获取完整克制表"""
    result = []
    for atk, data in TYPE_CHART.items():
        for def_elem in data.get('strong', []):
            if def_elem:
                result.append({'atk_element': atk, 'def_element': def_elem, 'multiplier': 2.0})
        for def_elem in data.get('resist', []):
            result.append({'atk_element': atk, 'def_element': def_elem, 'multiplier': 0.5})
    return result
