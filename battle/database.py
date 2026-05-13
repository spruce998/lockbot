"""
数据库模块 - 提供精灵、技能、克制关系查询
"""
from __future__ import annotations

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional

from .context import Pet, Skill

logger = logging.getLogger(__name__)

# 数据库路径（相对于 lockbot/ 目录）
DB_PATH = Path(__file__).parent.parent / "data" / "lockbot.db"

# 全局连接池
_connection: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    global _connection
    if _connection is None or _connection.closed:
        if not DB_PATH.exists():
            raise FileNotFoundError(f"数据库不存在: {DB_PATH}\n请先运行: python scripts/init_db.py")
        _connection = sqlite3.connect(str(DB_PATH))
        _connection.row_factory = sqlite3.Row
    return _connection


def close_connection():
    """关闭数据库连接"""
    global _connection
    if _connection:
        _connection.close()
        _connection = None


# ============================================================
# 精灵查询
# ============================================================

def get_pet_by_name(name: str) -> Optional[Pet]:
    """根据名称查询精灵"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pets WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        return None

    return Pet(
        id=row['id'],
        name=row['name'],
        element=row['element'],
        sub_element=row.get('sub_element'),
        base_stat_total=row.get('base_stat_total', 0),
        base_hp=row.get('base_hp', 0),
        base_atk=row.get('base_atk', 0),
        base_spatk=row.get('base_spatk', 0),
        base_def=row.get('base_def', 0),
        base_spdef=row.get('base_spdef', 0),
        base_spd=row.get('base_spd', 0),
        trait_name=row.get('trait_name', ''),
        trait_description=row.get('trait_description', ''),
        current_hp=row.get('base_hp', 0),
        max_hp=row.get('base_hp', 0),
    )


def get_pet_skills(pet_name: str) -> list[Skill]:
    """查询精灵可学习的全部技能"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.* FROM skills s
        JOIN pet_skills ps ON s.id = ps.skill_id
        JOIN pets p ON ps.pet_id = p.id
        WHERE p.name = ?
        ORDER BY ps.unlock_level, s.energy_cost
    """, (pet_name,))

    return [Skill(
        id=row['id'],
        name=row['name'],
        element=row.get('element', ''),
        damage_type=row.get('damage_type', ''),
        power=row.get('power', 0),
        energy_cost=row.get('energy_cost', 0),
        effect_description=row.get('effect_description', ''),
        unlock_level=row.get('unlock_level', 0),
    ) for row in cursor.fetchall()]


def list_all_pets() -> list[dict]:
    """列出所有精灵"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, element, base_stat_total FROM pets ORDER BY name")
    return [dict(row) for row in cursor.fetchall()]


# ============================================================
# 技能查询
# ============================================================

def get_skill_by_name(name: str) -> Optional[Skill]:
    """根据名称查询技能"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM skills WHERE name = ?", (name,))
    row = cursor.fetchone()
    if not row:
        return None

    return Skill(
        id=row['id'],
        name=row['name'],
        element=row.get('element', ''),
        damage_type=row.get('damage_type', ''),
        power=row.get('power', 0),
        energy_cost=row.get('energy_cost', 0),
        has_charge=row.get('has_charge', False),
        has_burst=row.get('has_burst', False),
        has_counter=row.get('has_counter', False),
        has_transmission=row.get('has_transmission', False),
        position_effect=row.get('position_effect', ''),
        permanent_effect=row.get('permanent_effect', ''),
        effect_description=row.get('effect_description', ''),
        unlock_level=row.get('unlock_level', 0),
    )


# ============================================================
# 属性克制查询
# ============================================================

def get_type_multiplier(atk_element: str, def_element: str) -> float:
    """获取属性克制倍率"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT multiplier FROM type_chart
        WHERE atk_element = ? AND def_element = ?
    """, (atk_element, def_element))
    row = cursor.fetchone()
    if row:
        return row['multiplier']
    return 1.0  # 默认正常伤害


def get_type_chart() -> list[dict]:
    """获取完整克制表"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM type_chart ORDER BY atk_element, def_element")
    return [dict(row) for row in cursor.fetchall()]
