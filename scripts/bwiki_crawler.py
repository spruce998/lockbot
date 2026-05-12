#!/usr/bin/env python3
"""
洛克王国世界 BWIKI 数据爬虫 v2
============================
数据源：https://wiki.biligame.com/rocom/
目标：爬取宠物数据、技能数据、属性克制表，导入 SQLite 数据库

v2 变更：
- 使用 DOM 结构化解析（不再依赖正则）
- 修复属性提取 bug
- 修复技能解析（从 skill_box DOM 直接提取）
- 修复链接过滤（移除导航页）
"""

import requests
import time
import random
import json
import re
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
from urllib.parse import unquote

# ============================================================
# 配置区
# ============================================================

WIKI_BASE = "https://wiki.biligame.com/rocom/"
WIKI_API = "https://wiki.biligame.com/rocom/api.php"

MIN_DELAY = 2.0
MAX_DELAY = 5.0
MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 3
REQUEST_TIMEOUT = 30
BATCH_SIZE = 20
BATCH_REST_MIN = 10
BATCH_REST_MAX = 30
UA_ROTATE_INTERVAL = 50

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
EXPORT_DIR = DATA_DIR / "export"
CHECKPOINT_DIR = DATA_DIR / ".checkpoint"
DB_PATH = DATA_DIR / "lockbot.db"
LOG_DIR = PROJECT_DIR / "logs"

for d in [EXPORT_DIR, CHECKPOINT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# 日志
# ============================================================

logger = logging.getLogger("bwiki_crawler")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-7s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(ch)

fh = logging.FileHandler(LOG_DIR / f"crawler_{datetime.now().strftime('%Y%m%d')}.log", encoding='utf-8')
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-7s] %(message)s'))
logger.addHandler(fh)

# ============================================================
# User-Agent 池
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

ELEMENTS = ["普通", "草", "火", "水", "光", "地", "冰", "龙", "电",
            "毒", "虫", "武", "翼", "萌", "幽", "恶", "机械", "幻"]


# ============================================================
# 防封 HTTP 会话
# ============================================================

class AntiBanSession:
    def __init__(self):
        self.session = requests.Session()
        self.request_count = 0
        self.last_request_time = 0
        self.current_ua_idx = 0
        self._set_ua()

    def _set_ua(self):
        ua = USER_AGENTS[self.current_ua_idx]
        self.session.headers.update({
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        })

    def rotate_ua(self):
        self.current_ua_idx = (self.current_ua_idx + 1) % len(USER_AGENTS)
        self._set_ua()
        logger.debug(f"UA 轮换 → #{self.current_ua_idx + 1}")

    def _delay(self):
        self.request_count += 1
        if self.request_count % UA_ROTATE_INTERVAL == 0:
            self.rotate_ua()
            logger.info(f"🔄 UA 自动轮换（#{self.request_count} 次请求后）")
        if self.last_request_time > 0:
            elapsed = time.time() - self.last_request_time
            needed = MIN_DELAY + random.random()
            if elapsed < needed:
                sleep_time = needed - elapsed + random.uniform(0.5, MAX_DELAY - MIN_DELAY)
                logger.debug(f"⏱ 限速延迟 {sleep_time:.1f}s")
                time.sleep(sleep_time)
        self.last_request_time = time.time()

    def request(self, url: str, **kwargs) -> Optional[requests.Response]:
        self._delay()
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.session.get(url, **kwargs)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code == 429:
                    wait = RETRY_BACKOFF_BASE ** (attempt + 1) + random.uniform(1, 5)
                    logger.warning(f"🚫 429 限速！等待 {wait:.0f}s 后重试 ({attempt+1}/{MAX_RETRIES})")
                    time.sleep(wait)
                    self.rotate_ua()
                elif resp.status_code == 503:
                    wait = RETRY_BACKOFF_BASE ** (attempt + 2) + random.uniform(2, 8)
                    logger.warning(f"⚠️  503 服务不可用，等待 {wait:.0f}s ({attempt+1}/{MAX_RETRIES})")
                    time.sleep(wait)
                elif resp.status_code == 403:
                    logger.warning(f"🔒 403 禁止访问，轮换 UA 并重试")
                    self.rotate_ua()
                    time.sleep(RETRY_BACKOFF_BASE ** (attempt + 2))
                else:
                    logger.warning(f"HTTP {resp.status_code}: {url}")
                    return resp
            except requests.exceptions.ConnectionError as e:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.error(f"❌ 连接失败: {e}，{wait:.0f}s 后重试")
                time.sleep(wait)
            except requests.exceptions.Timeout:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.error(f"⏰ 请求超时，{wait:.0f}s 后重试")
                time.sleep(wait)
            except Exception as e:
                logger.error(f"💥 未知错误: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None
        logger.error(f"❌ 请求失败（{MAX_RETRIES} 次重试后）: {url}")
        return None


# ============================================================
# 断点续传
# ============================================================

class Checkpoint:
    def __init__(self, name: str):
        self.file = CHECKPOINT_DIR / f"{name}.json"
        self.data = self._load()

    def _load(self) -> dict:
        if self.file.exists():
            with open(self.file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"completed": [], "failed": [], "updated_at": None}

    def save(self):
        self.data["updated_at"] = datetime.now().isoformat()
        with open(self.file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def mark_done(self, item_id: str):
        if item_id not in self.data["completed"]:
            self.data["completed"].append(item_id)
            self.save()

    def mark_fail(self, item_id: str, error: str = ""):
        self.data["failed"].append({"id": item_id, "error": error, "time": datetime.now().isoformat()})
        self.save()

    def is_done(self, item_id: str) -> bool:
        return item_id in self.data["completed"]

    @property
    def done_count(self) -> int:
        return len(self.data["completed"])

    @property
    def fail_count(self) -> int:
        return len(self.data["failed"])


# ============================================================
# 爬虫核心（v2 - DOM 结构化解析）
# ============================================================

class BwikiCrawler:
    def __init__(self):
        self.http = AntiBanSession()
        self.pet_cp = Checkpoint("pets")
        self.skill_cp = Checkpoint("skills")
        self.pets = []
        self.skills = []
        self.type_chart = []

    def get_page(self, title: str) -> Optional[BeautifulSoup]:
        url = f"{WIKI_BASE}{title}"
        logger.debug(f"GET {url}")
        resp = self.http.request(url)
        if resp:
            resp.encoding = 'utf-8'
            return BeautifulSoup(resp.text, 'html.parser')
        return None

    # --------------------------------------------------------
    # 1. 提取宠物列表
    # --------------------------------------------------------

    def extract_pet_list(self) -> List[dict]:
        logger.info("=" * 60)
        logger.info("📋 步骤 1：从精灵图鉴页提取宠物列表")
        logger.info("=" * 60)

        # 方法 1：MediaWiki API
        pets = self._api_get_category_members("精灵")
        if pets:
            logger.info(f"✅ 通过 API 获取 {len(pets)} 个宠物")
            return pets

        # 方法 2：HTML 解析
        logger.info("API 获取失败，降级到 HTML 解析...")
        soup = self.get_page("精灵图鉴")
        if not soup:
            logger.error("❌ 无法获取精灵图鉴页面")
            return []

        pets = []
        seen = set()
        skip_keywords = [
            "首页", "特殊:", "Special:", "MediaWiki", "编辑", "帮助", "沙盒",
            "参数设置", "最近更改", "文件列表", "随机页面", "分类索引",
            "创建新页面", "上传文件", "个人设置", "配置", "刷新",
            "图鉴", "筛选", "计算器", "阵容", "地图", "任务",
            "邮件", "副本", "服装", "家具", "地区", "道具",
            "蛋", "果实", "经验", "贡献者", "WIKI", "通知", "攻略",
            "我的消息", "关于本站", "游戏详情", "游戏官网", "招募",
            "工具", "扩展", "异色传递", "孵蛋", "伤害计算", "性格计算",
        ]

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if '/rocom/' not in href:
                continue
            title = unquote(href.split('/rocom/')[-1].split('?')[0].split('#')[0])
            if not title or title in seen:
                continue
            if any(kw in title or kw in text for kw in skip_keywords):
                continue
            seen.add(title)
            pets.append({"title": title, "name": text, "url": f"{WIKI_BASE}{title}"})

        logger.info(f"✅ HTML 解析提取到 {len(pets)} 个宠物")
        return pets

    def _api_get_category_members(self, category: str) -> List[dict]:
        pets = []
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": "500",
            "cmtype": "page",
            "format": "json",
        }
        try:
            resp = self.http.session.get(WIKI_API, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("query", {}).get("categorymembers", []):
                    title = m.get("title", "")
                    if any(kw in title for kw in ["精灵图鉴", "首页", "特殊"]):
                        continue
                    pets.append({"title": title, "name": title, "url": f"{WIKI_BASE}{title}"})
        except Exception as e:
            logger.debug(f"API 获取分类成员失败: {e}")
        return pets

    # --------------------------------------------------------
    # 2. 解析宠物详情（v2 - DOM 结构化）
    # --------------------------------------------------------

    def parse_pet_detail(self, title: str) -> Optional[dict]:
        soup = self.get_page(title)
        if not soup:
            return None

        pet = {
            "title": title,
            "source_url": f"{WIKI_BASE}{title}",
            "crawled_at": datetime.now().isoformat(),
        }

        # --- 编号 ---
        number_match = re.match(r'^(\d+)\s*(.+)', title)
        if number_match:
            pet["number"] = int(number_match.group(1))
            pet["name"] = number_match.group(2).strip()
        else:
            pet["name"] = title

        # --- 属性（从 rocom_sprite_grament_attributes 提取）---
        attr_div = soup.find('div', class_='rocom_sprite_grament_attributes')
        if attr_div:
            attr_text = attr_div.get_text(strip=True)
            if attr_text in ELEMENTS:
                pet["element"] = attr_text
                logger.debug(f"  属性: {attr_text}")

        # 备用：从 attributes_text 提取
        if "element" not in pet:
            attr_text_div = soup.find('div', class_='rocom_sprite_grament_attributes_text')
            if attr_text_div:
                attr_text = attr_text_div.get_text(strip=True)
                if attr_text in ELEMENTS:
                    pet["element"] = attr_text

        # --- 种族值（从 rocom_sprite_info_title 提取）---
        info_title = soup.find('div', class_='rocom_sprite_info_title')
        if info_title:
            total_text = info_title.get_text(strip=True)
            total_match = re.search(r'(\d+)', total_text)
            if total_match:
                pet["base_stat_total"] = int(total_match.group(1))

        # --- 六维（从 rocom_sprite_info_qualification 提取）---
        qual_div = soup.find('div', class_='rocom_sprite_info_qualification')
        if qual_div:
            qual_text = qual_div.get_text(strip=True)
            stat_map = {
                "生命": "base_hp", "物攻": "base_atk", "魔攻": "base_spatk",
                "物防": "base_def", "魔防": "base_spdef", "速度": "base_spd",
            }
            for cn_name, db_field in stat_map.items():
                match = re.search(rf'{cn_name}(\d+)', qual_text)
                if match:
                    pet[db_field] = int(match.group(1))

        # --- 特性 ---
        trait_content = soup.find('div', class_='rocom_sprite_info_characteristic_content')
        if trait_content:
            trait_text = trait_content.get_text(strip=True)
            # 格式："超聚能蓄力时，聚能变为积蓄。"
            # 第一个词是特性名，后面是描述
            pet["trait_name"] = trait_text[:3]  # 取前3个字作为名称
            pet["trait_description"] = trait_text

        # --- 身高体重（从 rocom_sprite_info_physique 提取）---
        phys_div = soup.find('div', class_='rocom_sprite_info_physique')
        if phys_div:
            phys_text = phys_div.get_text(strip=True)
            height_match = re.search(r'([\d.]+)-([\d.]+)M', phys_text)
            if height_match:
                pet["height_min"] = float(height_match.group(1))
                pet["height_max"] = float(height_match.group(2))
            weight_match = re.search(r'([\d.]+)-([\d.]+)KG', phys_text)
            if weight_match:
                pet["weight_min"] = float(weight_match.group(1))
                pet["weight_max"] = float(weight_match.group(2))

        # --- 精灵分布 ---
        bgcontent = soup.find('div', class_='rocom_sprite_bgcontent_box')
        if bgcontent:
            text = bgcontent.get_text(strip=True)
            spawn_match = re.search(r'精灵分布\s*[:：]\s*(.+)', text)
            if spawn_match:
                pet["spawn_location"] = spawn_match.group(1).strip()

        # --- 描述 ---
        desc_div = soup.find('div', class_='rocom_sprite_info_content')
        if desc_div:
            pet["description"] = desc_div.get_text(strip=True)

        # --- 技能列表（从 rocom_sprite_skill_box DOM 提取）---
        skills = []
        for skill_box in soup.find_all('div', class_='rocom_sprite_skill_box'):
            skill = self._parse_skill_box(skill_box)
            if skill:
                skills.append(skill)

        pet["skills"] = skills

        logger.debug(
            f"  📊 {pet['name']} | 属性:{pet.get('element', '?')} | "
            f"种族:{pet.get('base_stat_total', '?')} | 技能:{len(skills)}"
        )
        return pet

    def _parse_skill_box(self, skill_box) -> Optional[dict]:
        """
        从单个 skill_box DOM 提取技能数据

        HTML 结构：
        <div class="rocom_sprite_skill_box">
            <div class="rocom_sprite_skillName">技能名</div>
            <div class="rocom_sprite_skillDamage">能耗</div>
            <div class="rocom_sprite_skillType">物攻/魔攻/防御/状态</div>
            <div class="rocom_sprite_skill_power">威力</div>
            <div class="rocom_sprite_skillContent">✦效果描述</div>
        </div>
        """
        name_div = skill_box.find('div', class_='rocom_sprite_skillName')
        if not name_div:
            return None

        name = name_div.get_text(strip=True)
        if not name or name.startswith("文件:"):
            return None

        skill = {"name": name}

        # 能耗（skillDamage 实际存储的是能耗值）
        damage_div = skill_box.find('div', class_='rocom_sprite_skillDamage')
        if damage_div:
            energy_text = damage_div.get_text(strip=True)
            try:
                skill["energy_cost"] = int(energy_text)
            except ValueError:
                skill["energy_cost"] = 0

        # 伤害类型
        type_div = skill_box.find('div', class_='rocom_sprite_skillType')
        if type_div:
            skill["damage_type"] = type_div.get_text(strip=True)

        # 威力
        power_div = skill_box.find('div', class_='rocom_sprite_skill_power')
        if power_div:
            power_text = power_div.get_text(strip=True)
            try:
                skill["power"] = int(power_text)
            except ValueError:
                skill["power"] = 0

        # 效果描述
        content_div = skill_box.find('div', class_='rocom_sprite_skillContent')
        if content_div:
            effect = content_div.get_text(strip=True)
            skill["effect"] = effect

        return skill

    def crawl_pets(self, limit: int = None, skip_done: bool = True):
        pet_list = self.extract_pet_list()
        if not pet_list:
            return
        if skip_done:
            pet_list = [p for p in pet_list if not self.pet_cp.is_done(p["title"])]
        if limit:
            pet_list = pet_list[:limit]

        logger.info(f"📦 待爬取：{len(pet_list)} 个宠物（已完成：{self.pet_cp.done_count}）")
        if not pet_list:
            logger.info("✅ 所有宠物已爬取完成")
            return

        batch_num = 0
        for i in range(0, len(pet_list), BATCH_SIZE):
            batch = pet_list[i:i + BATCH_SIZE]
            batch_num += 1
            logger.info(f"🔄 批次 {batch_num}：爬取 {len(batch)} 个宠物")

            for idx, pet_info in enumerate(batch, 1):
                title = pet_info["title"]
                logger.info(f"  [{idx}/{len(batch)}] {title}")
                try:
                    pet = self.parse_pet_detail(title)
                    if pet:
                        self.pets.append(pet)
                        self.pet_cp.mark_done(title)
                    else:
                        self.pet_cp.mark_fail(title, "解析返回空")
                except Exception as e:
                    self.pet_cp.mark_fail(title, str(e))
                    logger.error(f"  ❌ 异常: {e}")

            self._save_json("pets.json", self.pets)
            if i + BATCH_SIZE < len(pet_list):
                rest = random.uniform(BATCH_REST_MIN, BATCH_REST_MAX)
                logger.info(f"☕ 批次休息 {rest:.0f} 秒...")
                time.sleep(rest)

        logger.info(f"✅ 宠物爬取完成！共 {len(self.pets)} 个")

    # --------------------------------------------------------
    # 3. 技能爬取
    # --------------------------------------------------------

    def crawl_skills(self, limit: int = None, skip_done: bool = True):
        logger.info("=" * 60)
        logger.info("📋 步骤 2：从技能图鉴页提取技能列表")
        logger.info("=" * 60)

        soup = self.get_page("技能图鉴")
        if not soup:
            logger.error("❌ 无法获取技能图鉴页面")
            return

        skills = []
        seen = set()
        skip_keywords = [
            "首页", "图鉴", "筛选", "计算器", "阵容", "地图",
            "任务", "邮件", "副本", "服装", "特殊:", "Special:",
            "精灵", "道具", "蛋", "经验", "编辑", "帮助",
            "MediaWiki", "参数", "文件", "分类", "贡献者",
            "刷新", "创建", "测试", "配置", "WIKI", "通知",
            "异色传递", "工具", "攻略", "扩展",
        ]

        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            if '/rocom/' not in href or len(text) < 2:
                continue
            title = unquote(href.split('/rocom/')[-1].split('?')[0].split('#')[0])
            if not title or title in seen:
                continue
            if any(kw in title or kw in text for kw in skip_keywords):
                continue
            seen.add(title)
            skills.append({"title": title, "name": text})

        if skip_done:
            skills = [s for s in skills if not self.skill_cp.is_done(s["title"])]
        if limit:
            skills = skills[:limit]

        logger.info(f"📦 待爬取：{len(skills)} 个技能（已完成：{self.skill_cp.done_count}）")
        if not skills:
            logger.info("✅ 所有技能已爬取完成")
            return

        batch_num = 0
        for i in range(0, len(skills), BATCH_SIZE):
            batch = skills[i:i + BATCH_SIZE]
            batch_num += 1
            logger.info(f"🔄 批次 {batch_num}：爬取 {len(batch)} 个技能")

            for idx, skill_info in enumerate(batch, 1):
                title = skill_info["title"]
                logger.info(f"  [{idx}/{len(batch)}] {title}")
                try:
                    soup = self.get_page(title)
                    if soup:
                        skill = {"title": title, "source_url": f"{WIKI_BASE}{title}"}
                        page_text = soup.get_text()
                        for elem in ELEMENTS:
                            if re.search(rf'属性\s*[\n：:]\s*{elem}', page_text) or \
                               re.search(rf'-\s*{elem}\s*\n', page_text):
                                skill["element"] = elem
                                break
                        type_match = re.search(r'(物理|魔法|防御|变化|物攻|魔攻)', page_text)
                        if type_match:
                            skill["damage_type"] = type_match.group(1)
                        self.skills.append(skill)
                        self.skill_cp.mark_done(title)
                    else:
                        self.skill_cp.mark_fail(title, "页面获取失败")
                except Exception as e:
                    self.skill_cp.mark_fail(title, str(e))
                    logger.error(f"  ❌ 异常: {e}")

            self._save_json("skills.json", self.skills)
            if i + BATCH_SIZE < len(skills):
                rest = random.uniform(BATCH_REST_MIN, BATCH_REST_MAX)
                logger.info(f"☕ 批次休息 {rest:.0f} 秒...")
                time.sleep(rest)

        logger.info(f"✅ 技能爬取完成！共 {len(self.skills)} 个")

    # --------------------------------------------------------
    # 4. 属性克制表
    # --------------------------------------------------------

    def crawl_type_chart(self):
        logger.info("=" * 60)
        logger.info("📋 步骤 3：解析属性克制关系")
        logger.info("=" * 60)

        relations = [
            ("火", "草", 2.0), ("火", "冰", 2.0), ("火", "虫", 2.0), ("火", "机械", 2.0),
            ("火", "火", 0.5), ("火", "水", 0.5), ("火", "地", 0.5), ("火", "龙", 0.5),
            ("水", "火", 2.0), ("水", "地", 2.0), ("水", "岩", 2.0),
            ("水", "水", 0.5), ("水", "草", 0.5), ("水", "龙", 0.5),
            ("草", "水", 2.0), ("草", "地", 2.0), ("草", "岩", 2.0),
            ("草", "火", 0.5), ("草", "草", 0.5), ("草", "毒", 0.5),
            ("草", "翼", 0.5), ("草", "虫", 0.5), ("草", "龙", 0.5), ("草", "机械", 0.5),
            ("电", "水", 2.0), ("电", "翼", 2.0),
            ("电", "电", 0.5), ("电", "草", 0.5), ("电", "龙", 0.5), ("电", "地", 0.0),
            ("冰", "草", 2.0), ("冰", "地", 2.0), ("冰", "翼", 2.0), ("冰", "龙", 2.0),
            ("冰", "火", 0.5), ("冰", "水", 0.5), ("冰", "冰", 0.5), ("冰", "机械", 0.5),
            ("龙", "龙", 2.0),
            ("幽", "萌", 2.0),
            ("萌", "毒", 2.0), ("萌", "武", 2.0),
            ("毒", "草", 2.0),
            ("恶", "幽", 2.0), ("恶", "萌", 2.0),
            ("武", "普通", 2.0), ("武", "冰", 2.0), ("武", "恶", 2.0), ("武", "机械", 2.0),
            ("翼", "草", 2.0), ("翼", "武", 2.0), ("翼", "虫", 2.0),
            ("地", "火", 2.0), ("地", "电", 2.0), ("地", "毒", 2.0), ("地", "机械", 2.0),
            ("虫", "草", 2.0), ("虫", "萌", 2.0), ("虫", "恶", 2.0),
            ("机械", "冰", 2.0),
        ]

        self.type_chart = [
            {"atk_element": atk, "def_element": def_, "multiplier": mult}
            for atk, def_, mult in relations
        ]

        logger.info(f"✅ 属性克制关系：{len(self.type_chart)} 条")
        logger.info("⚠️  注意：克制关系需要根据游戏内实际数据验证！")
        self._save_json("type_chart.json", self.type_chart)

    # --------------------------------------------------------
    # 保存 & 导入
    # --------------------------------------------------------

    def _save_json(self, filename: str, data: list):
        filepath = EXPORT_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"💾 保存 {filename} ({len(data)} 条)")

    def save_all(self):
        logger.info("=" * 60)
        logger.info("💾 保存所有爬取数据")
        logger.info("=" * 60)

        self._save_json("pets.json", self.pets)
        self._save_json("skills.json", self.skills)
        self._save_json("type_chart.json", self.type_chart)

        report = {
            "crawl_time": datetime.now().isoformat(),
            "stats": {
                "pets": len(self.pets),
                "skills": len(self.skills),
                "type_chart": len(self.type_chart),
            },
            "checkpoints": {
                "pets": {"done": self.pet_cp.done_count, "failed": self.pet_cp.fail_count},
                "skills": {"done": self.skill_cp.done_count, "failed": self.skill_cp.fail_count},
            },
        }
        report_file = EXPORT_DIR / "crawl_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 数据保存完成！")
        logger.info(f"   宠物：{len(self.pets)} 条")
        logger.info(f"   技能：{len(self.skills)} 条")
        logger.info(f"   克制：{len(self.type_chart)} 条")

    def import_to_db(self):
        logger.info("=" * 60)
        logger.info("🗄️  导入数据到 SQLite 数据库")
        logger.info("=" * 60)

        if not DB_PATH.exists():
            logger.error(f"❌ 数据库不存在：{DB_PATH}")
            return

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")

        imported_pets = 0
        imported_skills = 0

        try:
            for pet in self.pets:
                cursor.execute("""
                    INSERT OR REPLACE INTO pets (
                        name, number, element, base_hp, base_atk, base_spatk,
                        base_def, base_spdef, base_spd, base_stat_total,
                        trait_name, trait_description, description,
                        spawn_location, source_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pet.get("name", pet.get("title", "")),
                    pet.get("number"),
                    pet.get("element", ""),
                    pet.get("base_hp"),
                    pet.get("base_atk"),
                    pet.get("base_spatk"),
                    pet.get("base_def"),
                    pet.get("base_spdef"),
                    pet.get("base_spd"),
                    pet.get("base_stat_total"),
                    pet.get("trait_name", ""),
                    pet.get("trait_description", ""),
                    pet.get("description", ""),
                    pet.get("spawn_location", ""),
                    pet.get("source_url", ""),
                ))
                imported_pets += 1

                for skill in pet.get("skills", []):
                    skill_name = skill.get("name", "")
                    if not skill_name:
                        continue
                    cursor.execute("""
                        INSERT OR REPLACE INTO skills (
                            name, damage_type, power, energy_cost, effect_description
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        skill_name,
                        skill.get("damage_type", ""),
                        skill.get("power", 0),
                        skill.get("energy_cost"),
                        skill.get("effect", ""),
                    ))
                    imported_skills += 1

                    cursor.execute("""
                        INSERT OR IGNORE INTO pet_skills (pet_id, skill_id)
                        VALUES (
                            (SELECT id FROM pets WHERE name = ?),
                            (SELECT id FROM skills WHERE name = ?)
                        )
                    """, (pet.get("name", ""), skill_name))

            logger.info(f"  宠物：{imported_pets} 条")
            logger.info(f"  技能：{imported_skills} 条")

            for relation in self.type_chart:
                cursor.execute("""
                    INSERT OR REPLACE INTO type_chart (atk_element, def_element, multiplier)
                    VALUES (?, ?, ?)
                """, (relation["atk_element"], relation["def_element"], relation["multiplier"]))

            logger.info(f"  克制关系：{len(self.type_chart)} 条")
            conn.commit()
            logger.info(f"✅ 数据库导入完成！")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ 数据库导入失败: {e}")
            raise
        finally:
            conn.close()


# ============================================================
# 主程序
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="洛克王国世界 BWIKI 数据爬虫 v2")
    parser.add_argument("--pets", action="store_true", help="爬取宠物数据")
    parser.add_argument("--skills", action="store_true", help="爬取技能数据")
    parser.add_argument("--type-chart", action="store_true", help="爬取属性克制表")
    parser.add_argument("--all", action="store_true", help="爬取所有数据")
    parser.add_argument("--import-db", action="store_true", help="导入到数据库")
    parser.add_argument("--limit", type=int, default=None, help="限制数量（测试用）")
    parser.add_argument("--resume", action="store_true", help="断点续传（默认）")
    parser.add_argument("--reset", action="store_true", help="重置断点")
    parser.add_argument("--test", action="store_true", help="测试模式（limit=5）")
    args = parser.parse_args()

    if args.test:
        args.all = True
        args.limit = 5
        logger.info("🧪 测试模式：每种数据只爬取 5 条")

    if not any([args.pets, args.skills, args.type_chart, args.all]):
        parser.print_help()
        return

    crawler = BwikiCrawler()

    if args.reset:
        logger.info("🗑️  重置所有断点...")
        for f in CHECKPOINT_DIR.glob("*.json"):
            f.unlink()

    if args.pets or args.all:
        crawler.crawl_pets(limit=args.limit, skip_done=args.resume and not args.reset)
    if args.skills or args.all:
        crawler.crawl_skills(limit=args.limit, skip_done=args.resume and not args.reset)
    if args.type_chart or args.all:
        crawler.crawl_type_chart()

    crawler.save_all()
    if args.import_db:
        crawler.import_to_db()


if __name__ == "__main__":
    main()
