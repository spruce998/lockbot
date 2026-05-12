"""
PVP 决策引擎
基于属性克制和技能库的决策系统
"""
import json
from pathlib import Path
from enum import Enum
from typing import List, Dict, Optional


class ElementType(Enum):
    """宠物属性"""
    FIRE = "fire"      # 火
    WATER = "water"    # 水
    GRASS = "grass"    # 草
    ELECTRIC = "electric"  # 电
    ICE = "ice"        # 冰
    ROCK = "rock"      # 岩石
    GROUND = "ground"  # 地面
    FLYING = "flying"  # 飞行
    PSYCHIC = "psychic"  # 超能
    GHOST = "ghost"    # 幽灵
    DRAGON = "dragon"  # 龙
    DARK = "dark"      # 黑暗
    STEEL = "steel"    # 钢
    FAIRY = "fairy"    # 妖精
    NORMAL = "normal"  # 普通
    BUG = "bug"        # 虫
    POISON = "poison"  # 毒
    FIGHTING = "fighting"  # 格斗


# 属性克制关系 (攻击方 -> 防御方 -> 倍率)
TYPE_CHART = {
    ElementType.FIRE: {
        ElementType.GRASS: 2.0, ElementType.ICE: 2.0, ElementType.BUG: 2.0, ElementType.STEEL: 2.0,
        ElementType.FIRE: 0.5, ElementType.WATER: 0.5, ElementType.ROCK: 0.5, ElementType.DRAGON: 0.5,
    },
    ElementType.WATER: {
        ElementType.FIRE: 2.0, ElementType.GROUND: 2.0, ElementType.ROCK: 2.0,
        ElementType.WATER: 0.5, ElementType.GRASS: 0.5, ElementType.DRAGON: 0.5,
    },
    ElementType.GRASS: {
        ElementType.WATER: 2.0, ElementType.GROUND: 2.0, ElementType.ROCK: 2.0,
        ElementType.FIRE: 0.5, ElementType.GRASS: 0.5, ElementType.POISON: 0.5,
        ElementType.FLYING: 0.5, ElementType.BUG: 0.5, ElementType.DRAGON: 0.5, ElementType.STEEL: 0.5,
    },
    ElementType.ELECTRIC: {
        ElementType.WATER: 2.0, ElementType.FLYING: 2.0,
        ElementType.ELECTRIC: 0.5, ElementType.GRASS: 0.5, ElementType.DRAGON: 0.5, ElementType.GROUND: 0.0,
    },
    ElementType.ICE: {
        ElementType.GRASS: 2.0, ElementType.GROUND: 2.0, ElementType.FLYING: 2.0, ElementType.DRAGON: 2.0,
        ElementType.FIRE: 0.5, ElementType.WATER: 0.5, ElementType.ICE: 0.5, ElementType.STEEL: 0.5,
    },
    # ... 其他属性克制关系可根据游戏实际设定补充
}


class Skill:
    """技能类"""
    def __init__(self, name: str, element: ElementType, power: int, accuracy: float = 1.0, 
                 priority: int = 0, effect: Optional[str] = None):
        self.name = name
        self.element = element
        self.power = power
        self.accuracy = accuracy
        self.priority = priority  # 先手度
        self.effect = effect  # 特殊效果
    
    def get_effective_power(self, target_element: ElementType) -> float:
        """计算对目标属性的有效威力"""
        base_power = self.power
        type_multiplier = TYPE_CHART.get(self.element, {}).get(target_element, 1.0)
        return base_power * type_multiplier
    
    def __repr__(self):
        return f"Skill({self.name}, {self.element.value}, power={self.power})"


class Pet:
    """宠物类"""
    def __init__(self, name: str, element: ElementType, hp: int, max_hp: int, 
                 skills: List[Skill], speed: int = 0):
        self.name = name
        self.element = element
        self.hp = hp
        self.max_hp = max_hp
        self.skills = skills
        self.speed = speed
    
    @property
    def hp_percent(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0
    
    def get_best_skill(self, target: 'Pet') -> Skill:
        """选择对目标最有效的技能"""
        if not self.skills:
            return None
        
        best_skill = None
        best_score = -float('inf')
        
        for skill in self.skills:
            # 评分 = 有效威力 + 先手度奖励 + 命中率惩罚
            effective_power = skill.get_effective_power(target.element)
            priority_bonus = skill.priority * 10
            accuracy_penalty = (1 - skill.accuracy) * 20
            
            # 低血量时优先高威力技能
            hp_factor = 1.0 if self.hp_percent > 0.5 else 1.2
            
            score = effective_power * hp_factor + priority_bonus - accuracy_penalty
            
            if score > best_score:
                best_score = score
                best_skill = skill
        
        return best_skill
    
    def __repr__(self):
        return f"Pet({self.name}, {self.element.value}, HP={self.hp}/{self.max_hp})"


class PVPDecisionEngine:
    """PVP 决策引擎"""
    def __init__(self, pet_db_path="data/pet_db.json", skill_db_path="data/skill_db.json"):
        self.pet_db_path = Path(pet_db_path)
        self.skill_db_path = Path(skill_db_path)
        self.pet_db = {}
        self.skill_db = {}
        self._load_databases()
        
        self.my_pet: Optional[Pet] = None
        self.enemy_pet: Optional[Pet] = None
    
    def _load_databases(self):
        """加载数据库"""
        if self.pet_db_path.exists():
            with open(self.pet_db_path, 'r', encoding='utf-8') as f:
                self.pet_db = json.load(f)
            print(f"加载宠物数据库：{len(self.pet_db)} 只宠物")
        
        if self.skill_db_path.exists():
            with open(self.skill_db_path, 'r', encoding='utf-8') as f:
                self.skill_db = json.load(f)
            print(f"加载技能数据库：{len(self.skill_db)} 个技能")
    
    def set_my_pet(self, name: str, hp: int, max_hp: int, skills: List[str]):
        """设置我方宠物"""
        pet_info = self.pet_db.get(name, {})
        element = ElementType(pet_info.get("element", "normal"))
        speed = pet_info.get("speed", 0)
        
        pet_skills = []
        for skill_name in skills:
            skill_info = self.skill_db.get(skill_name, {})
            skill = Skill(
                name=skill_name,
                element=ElementType(skill_info.get("element", "normal")),
                power=skill_info.get("power", 50),
                accuracy=skill_info.get("accuracy", 1.0),
                priority=skill_info.get("priority", 0)
            )
            pet_skills.append(skill)
        
        self.my_pet = Pet(name, element, hp, max_hp, pet_skills, speed)
        print(f"设置我方宠物：{self.my_pet}")
    
    def set_enemy_pet(self, name: str, hp: int, max_hp: int):
        """设置敌方宠物（根据识别结果）"""
        pet_info = self.pet_db.get(name, {})
        element = ElementType(pet_info.get("element", "normal"))
        self.enemy_pet = Pet(name, element, hp, max_hp, [], 0)
        print(f"识别敌方宠物：{self.enemy_pet}")
    
    def decide(self) -> Dict:
        """
        做出决策
        :return: 决策结果 {"action": "skill", "skill_name": xxx, "reason": xxx}
        """
        if not self.my_pet or not self.enemy_pet:
            return {"action": "wait", "reason": "信息不完整"}
        
        best_skill = self.my_pet.get_best_skill(self.enemy_pet)
        
        if not best_skill:
            return {"action": "wait", "reason": "没有可用技能"}
        
        # 计算克制倍率
        multiplier = TYPE_CHART.get(best_skill.element, {}).get(self.enemy_pet.element, 1.0)
        
        reason = f"{best_skill.name} 对 {self.enemy_pet.name} 造成 {multiplier}x 伤害"
        if multiplier > 1.5:
            reason += " (克制!)"
        elif multiplier < 0.7:
            reason += " (被抵抗)"
        
        return {
            "action": "skill",
            "skill_name": best_skill.name,
            "skill_index": self.my_pet.skills.index(best_skill),
            "reason": reason,
            "confidence": min(1.0, multiplier / 2.0)
        }
    
    def get_counter_pets(self, enemy_element: ElementType) -> List[str]:
        """推荐克制敌方属性的宠物"""
        counters = []
        for pet_name, pet_info in self.pet_db.items():
            pet_element = ElementType(pet_info.get("element", "normal"))
            effectiveness = TYPE_CHART.get(pet_element, {}).get(enemy_element, 1.0)
            if effectiveness > 1.5:
                counters.append((pet_name, effectiveness))
        
        counters.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in counters[:5]]


# 使用示例
if __name__ == "__main__":
    engine = PVPDecisionEngine()
    
    # 示例：设置我方宠物
    engine.set_my_pet("火花", hp=80, max_hp=100, skills=["火焰冲击", "火花", "抓挠"])
    
    # 示例：设置敌方宠物
    engine.set_enemy_pet("喵喵", hp=60, max_hp=90)
    
    # 获取决策
    decision = engine.decide()
    print(f"决策结果：{decision}")
