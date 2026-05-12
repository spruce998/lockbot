#!/usr/bin/env python3
"""
数据库初始化脚本
创建所有表和初始数据
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "lockbot.db"


def init_database(db_path=DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    print("创建数据表...")
    for sql in CREATE_TABLES:
        cursor.execute(sql)
    
    print("创建索引...")
    for sql in CREATE_INDEXES:
        cursor.execute(sql)
    
    print("插入默认配置...")
    for key, value, vtype, category, desc in DEFAULT_SETTINGS:
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value, value_type, category, description) VALUES (?, ?, ?, ?, ?)",
            (key, value, vtype, category, desc)
        )
    
    print("插入属性克制关系...")
    for atk_elem, def_elem, mult in DEFAULT_TYPE_CHART:
        cursor.execute(
            "INSERT OR REPLACE INTO type_chart (atk_element, def_element, multiplier) VALUES (?, ?, ?)",
            (atk_elem, def_elem, mult)
        )
    
    conn.commit()
    conn.close()
    print(f"✅ 数据库初始化完成：{db_path}")


# ============================================================
# 建表语句
# ============================================================

CREATE_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) NOT NULL UNIQUE,
        number INTEGER,
        element VARCHAR(20),
        sub_element VARCHAR(20),
        base_stat_total INTEGER,
        base_hp INTEGER,
        base_atk INTEGER,
        base_spatk INTEGER,
        base_def INTEGER,
        base_spdef INTEGER,
        base_spd INTEGER,
        height_min REAL,
        height_max REAL,
        weight_min REAL,
        weight_max REAL,
        trait_name VARCHAR(50),
        trait_description TEXT,
        spawn_location VARCHAR(100),
        description TEXT,
        rarity VARCHAR(20) DEFAULT 'common',
        is_owned BOOLEAN DEFAULT FALSE,
        source_url VARCHAR(255),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) NOT NULL UNIQUE,
        element VARCHAR(20),
        damage_type VARCHAR(20),
        power INTEGER DEFAULT 0,
        accuracy REAL DEFAULT 1.0,
        pp INTEGER DEFAULT 10,
        energy_cost INTEGER,
        priority INTEGER DEFAULT 0,
        cooldown INTEGER DEFAULT 0,
        effect_description TEXT,
        target VARCHAR(20) DEFAULT 'enemy',
        category VARCHAR(20) DEFAULT 'normal',
        unlock_level INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS pet_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pet_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        unlock_level INTEGER DEFAULT 1,
        is_default BOOLEAN DEFAULT FALSE,
        slot_position INTEGER,
        FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE,
        FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
        UNIQUE(pet_id, skill_id)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS type_chart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        atk_element VARCHAR(20) NOT NULL,
        def_element VARCHAR(20) NOT NULL,
        multiplier REAL NOT NULL DEFAULT 1.0,
        UNIQUE(atk_element, def_element)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS battle_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id VARCHAR(36) NOT NULL UNIQUE,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        battle_type VARCHAR(20) DEFAULT 'pvp',
        map_name VARCHAR(50),
        my_pet_id INTEGER,
        my_pet_level INTEGER DEFAULT 1,
        enemy_pet_id INTEGER,
        enemy_pet_name VARCHAR(50),
        enemy_pet_level INTEGER DEFAULT 1,
        my_skill_id INTEGER,
        skill_damage INTEGER,
        damage_received INTEGER,
        is_critical BOOLEAN DEFAULT FALSE,
        is_effective BOOLEAN,
        turn_count INTEGER DEFAULT 0,
        duration_sec INTEGER DEFAULT 0,
        result VARCHAR(10),
        rating_change INTEGER DEFAULT 0,
        opponent_name VARCHAR(50),
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (my_pet_id) REFERENCES pets(id),
        FOREIGN KEY (enemy_pet_id) REFERENCES pets(id),
        FOREIGN KEY (my_skill_id) REFERENCES skills(id)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS battle_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        battle_id VARCHAR(36) NOT NULL,
        turn_number INTEGER NOT NULL,
        my_pet_hp_before INTEGER,
        my_pet_hp_after INTEGER,
        enemy_pet_hp_before INTEGER,
        enemy_pet_hp_after INTEGER,
        my_skill_id INTEGER,
        my_skill_damage INTEGER,
        enemy_skill_name VARCHAR(50),
        enemy_skill_damage INTEGER,
        is_my_turn_first BOOLEAN,
        weather_effect VARCHAR(20),
        field_effect VARCHAR(20),
        notes TEXT,
        FOREIGN KEY (battle_id) REFERENCES battle_log(battle_id),
        FOREIGN KEY (my_skill_id) REFERENCES skills(id),
        UNIQUE(battle_id, turn_number)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key VARCHAR(50) NOT NULL UNIQUE,
        value TEXT,
        value_type VARCHAR(20) DEFAULT 'string',
        category VARCHAR(30) DEFAULT 'general',
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) NOT NULL UNIQUE,
        category VARCHAR(20) DEFAULT 'ui',
        file_path VARCHAR(255) NOT NULL,
        width INTEGER,
        height INTEGER,
        confidence_threshold REAL DEFAULT 0.8,
        is_active BOOLEAN DEFAULT TRUE,
        version INTEGER DEFAULT 1,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS sys_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        level VARCHAR(10) NOT NULL,
        module VARCHAR(30),
        message TEXT NOT NULL,
        stack_trace TEXT,
        context TEXT
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE NOT NULL UNIQUE,
        total_battles INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        win_rate REAL DEFAULT 0.0,
        total_duration_sec INTEGER DEFAULT 0,
        avg_duration_sec REAL DEFAULT 0.0,
        total_skills_used INTEGER DEFAULT 0,
        effective_hits INTEGER DEFAULT 0,
        critical_hits INTEGER DEFAULT 0,
        total_actions INTEGER DEFAULT 0,
        session_count INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_pets_element ON pets(element)",
    "CREATE INDEX IF NOT EXISTS idx_pets_number ON pets(number)",
    "CREATE INDEX IF NOT EXISTS idx_skills_element ON skills(element)",
    "CREATE INDEX IF NOT EXISTS idx_skills_damage_type ON skills(damage_type)",
    "CREATE INDEX IF NOT EXISTS idx_pet_skills_pet ON pet_skills(pet_id)",
    "CREATE INDEX IF NOT EXISTS idx_pet_skills_skill ON pet_skills(skill_id)",
    "CREATE INDEX IF NOT EXISTS idx_type_chart_atk ON type_chart(atk_element)",
    "CREATE INDEX IF NOT EXISTS idx_type_chart_def ON type_chart(def_element)",
    "CREATE INDEX IF NOT EXISTS idx_battle_log_pet ON battle_log(my_pet_id)",
    "CREATE INDEX IF NOT EXISTS idx_battle_log_result ON battle_log(result)",
    "CREATE INDEX IF NOT EXISTS idx_battle_log_timestamp ON battle_log(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_sys_log_level ON sys_log(level)",
    "CREATE INDEX IF NOT EXISTS idx_sys_log_timestamp ON sys_log(timestamp)",
]


DEFAULT_SETTINGS = [
    ("game.window_title", "洛克王国世界", "string", "general", "游戏窗口标题"),
    ("game.fps", "10", "int", "general", "截图帧率"),
    ("pvp.enabled", "true", "bool", "pvp", "是否启用 PVP 功能"),
    ("pvp.confidence_threshold", "0.8", "float", "pvp", "识别置信度阈值"),
    ("pvp.decision_timeout", "25", "int", "pvp", "决策时间限制（秒）"),
    ("anti_detect.enabled", "true", "bool", "anti_detect", "是否启用反检测"),
    ("anti_detect.random_delay_min", "0.1", "float", "anti_detect", "随机延迟最小值（秒）"),
    ("anti_detect.random_delay_max", "0.5", "float", "anti_detect", "随机延迟最大值（秒）"),
    ("anti_detect.mouse_smooth", "true", "bool", "anti_detect", "是否平滑鼠标移动"),
    ("anti_detect.active_hours_start", "8", "int", "anti_detect", "活跃时间开始（小时）"),
    ("anti_detect.active_hours_end", "23", "int", "anti_detect", "活跃时间结束（小时）"),
    ("logging.level", "INFO", "string", "logging", "日志级别"),
]


DEFAULT_TYPE_CHART = [
    # 火系
    ("火", "草", 2.0), ("火", "冰", 2.0), ("火", "虫", 2.0), ("火", "机械", 2.0),
    ("火", "火", 0.5), ("火", "水", 0.5), ("火", "地", 0.5), ("火", "龙", 0.5),
    # 水系
    ("水", "火", 2.0), ("水", "地", 2.0), ("水", "岩", 2.0),
    ("水", "水", 0.5), ("水", "草", 0.5), ("水", "龙", 0.5),
    # 草系
    ("草", "水", 2.0), ("草", "地", 2.0), ("草", "岩", 2.0),
    ("草", "火", 0.5), ("草", "草", 0.5), ("草", "毒", 0.5),
    ("草", "翼", 0.5), ("草", "虫", 0.5), ("草", "龙", 0.5), ("草", "机械", 0.5),
    # 电系
    ("电", "水", 2.0), ("电", "翼", 2.0),
    ("电", "电", 0.5), ("电", "草", 0.5), ("电", "龙", 0.5), ("电", "地", 0.0),
    # 冰系
    ("冰", "草", 2.0), ("冰", "地", 2.0), ("冰", "翼", 2.0), ("冰", "龙", 2.0),
    ("冰", "火", 0.5), ("冰", "水", 0.5), ("冰", "冰", 0.5), ("冰", "机械", 0.5),
    # 龙系
    ("龙", "龙", 2.0),
    # 幽系
    ("幽", "萌", 2.0),
    # 萌系
    ("萌", "毒", 2.0), ("萌", "武", 2.0),
    # 毒系
    ("毒", "草", 2.0),
    # 恶系
    ("恶", "幽", 2.0), ("恶", "萌", 2.0),
    # 武系
    ("武", "普通", 2.0), ("武", "冰", 2.0), ("武", "恶", 2.0), ("武", "机械", 2.0),
    # 翼系
    ("翼", "草", 2.0), ("翼", "武", 2.0), ("翼", "虫", 2.0),
    # 地系
    ("地", "火", 2.0), ("地", "电", 2.0), ("地", "毒", 2.0), ("地", "机械", 2.0),
    # 虫系
    ("虫", "草", 2.0), ("虫", "萌", 2.0), ("虫", "恶", 2.0),
    # 机械系
    ("机械", "冰", 2.0),
]


if __name__ == "__main__":
    init_database()
