import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import random
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import scipy.stats as stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import warnings
import requests
from bs4 import BeautifulSoup
import re
import time
warnings.filterwarnings('ignore')

# ==========================================
# 0. 数据存储配置
# ==========================================
USER_DATA_FILE = "user_data.json"
STRATEGY_DB_FILE = "strategies_db.json"
ACTIVITY_LOG_FILE = "activity_log.json"
DEMO_DATA_FLAG = "demo_data_loaded.flag"

def load_json_db(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json_db(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_activity(username, action):
    db = load_json_db(ACTIVITY_LOG_FILE)
    log_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{username}"
    db[log_id] = {
        "username": username,
        "action": action,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json_db(ACTIVITY_LOG_FILE, db)

# ==========================================
# 0.5 演示数据生成器
# ==========================================
def generate_demo_users():
    try:
        if os.path.exists(DEMO_DATA_FLAG):
            return

        demo_users = {}
        genders = ["男", "女", "不愿透露"]
        ages = ["18岁以下", "18-24岁", "25-30岁", "31-35岁", "36岁以上"]
        game_types_pool = ["动作", "角色扮演", "策略", "射击", "模拟", "体育", "休闲", "恐怖", "解谜", "竞速"]
        play_times = ["<1小时", "1-3小时", "3-5小时", "5-8小时", "8小时以上"]
        frequencies = ["偶尔（1-2天）", "经常（3-4天）", "频繁（5-6天）", "几乎每天"]
        quit_reasons_pool = ["太难了", "没时间", "没朋友一起玩", "剧情无聊", "内容太少", "优化差/卡顿", "其他"]
        purchase_factors_pool = ["画面", "玩法", "价格", "朋友推荐", "媒体评分", "Steam评价", "开发者口碑"]

        for i in range(30):
            username = f"Demo_Player_{i+1:02d}"
            demo_users[username] = {
                "username": username,
                "gender": random.choice(genders),
                "age": random.choice(ages),
                "game_types": random.sample(game_types_pool, k=random.randint(2, 5)),
                "play_time": random.choice(play_times),
                "gaming_years": random.randint(1, 20),
                "weekly_frequency": random.choice(frequencies),
                "quit_reason": random.sample(quit_reasons_pool, k=random.randint(1, 3)),
                "purchase_factor": random.sample(purchase_factors_pool, k=random.randint(1, 3)),
                "gaming_skill": random.randint(3, 9),
                "social_preference": random.randint(2, 9),
                "completionist": random.randint(2, 9),
                "register_time": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S")
            }

        save_json_db(USER_DATA_FILE, demo_users)

        demo_strategies = {}
        sample_games = {
            "艾尔登法环": "https://store.steampowered.com/app/1245620/Elden_Ring/",
            "赛博朋克2077": "https://store.steampowered.com/app/1091500/Cyberpunk_2077/",
            "星露谷物语": "https://store.steampowered.com/app/413150/Stardew_Valley/",
            "空洞骑士": "https://store.steampowered.com/app/367520/Hollow_Knight/",
            "巫师3": "https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/",
            "只狼": "https://store.steampowered.com/app/814380/Sekiro_Shadows_Die_Twice/",
            "文明6": "https://store.steampowered.com/app/289070/Sid_Meiers_Civilization_VI/",
            "我的世界": "https://www.minecraft.net/zh-hans"
        }
        for i, (game, url) in enumerate(sample_games.items()):
            sid = f"demo_strategy_{i}"
            demo_strategies[sid] = {
                "game_name": game,
                "title": f"【新手向】{game} 完整入门指南",
                "tags": ["新手向", "避坑指南", "全收集"],
                "content": f"""## {game} 新手入门指南

### 第一步：基础操作
- 熟悉《{game}》的基本操作和界面
- 了解核心玩法和游戏目标

### 第二步：进阶技巧
- 掌握关键系统和机制
- 学习高效通关策略

### 第三步：专家建议
- 高级技巧和隐藏内容
- 常见问题解答

### 相关资源
- 欢迎在评论区交流心得
- 更多攻略请查看其他玩家分享
""",
                "author": f"Demo_Player_{random.randint(1,30):02d}",
                "time": (datetime.now() - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d %H:%M"),
                "steam_url": url
            }
        save_json_db(STRATEGY_DB_FILE, demo_strategies)

        with open(DEMO_DATA_FLAG, "w") as f:
            f.write("loaded")
        return True
    except Exception as e:
        print(f"⚠️ 演示数据生成失败: {e}")
        return False

def clear_demo_data():
    try:
        files = [USER_DATA_FILE, STRATEGY_DB_FILE, ACTIVITY_LOG_FILE, DEMO_DATA_FLAG]
        for f in files:
            if os.path.exists(f):
                os.remove(f)
        return True
    except Exception as e:
        print(f"⚠️ 清除数据失败: {e}")
        return False

# ==========================================
# 1. 备选游戏列表（当 Steam API 无法访问时使用）
# ==========================================
FALLBACK_GAME_LIST = [
    {"name": "黑神话：悟空", "appid": 2358720},
    {"name": "艾尔登法环", "appid": 1245620},
    {"name": "赛博朋克2077", "appid": 1091500},
    {"name": "星露谷物语", "appid": 413150},
    {"name": "空洞骑士", "appid": 367520},
    {"name": "巫师3", "appid": 292030},
    {"name": "只狼", "appid": 814380},
    {"name": "文明6", "appid": 289070},
    {"name": "CS:GO", "appid": 730},
    {"name": "DOTA2", "appid": 570},
    {"name": "PUBG", "appid": 578080},
    {"name": "GTA5", "appid": 271590},
    {"name": "荒野大镖客2", "appid": 1174180},
    {"name": "死亡搁浅", "appid": 1190460},
    {"name": "双人成行", "appid": 1426210},
]

def get_steam_app_list():
    """获取 Steam 游戏列表，失败时返回备选列表"""
    if "steam_app_list" in st.session_state and st.session_state.steam_app_list is not None:
        return st.session_state.steam_app_list
    
    try:
        list_url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        response = requests.get(list_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            app_list = data['applist']['apps']
            app_list = [app for app in app_list if app.get('name', '').strip()]
            st.session_state.steam_app_list = app_list
            return app_list
    except Exception as e:
        print(f"⚠️ 获取Steam列表失败: {e}")
    
    st.session_state.steam_app_list = FALLBACK_GAME_LIST
    return FALLBACK_GAME_LIST

def fetch_steam_game_features(app_id):
    url = f"https://store.steampowered.com/app/{app_id}/"
    cookies = {
        "birthtime": "946656000",
        "lastagecheckage": "1-0-2000",
        "wants_mature_content": "1",
        "data_mature_allowed": "1",
        "browserid": "2858114536252114536",
        "Steam_Language": "schinese"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "lxml")
        if "store.steampowered.com/#" in response.url or not soup.find("div", class_="apphub_AppName"):
            return None
        game_name = soup.find("div", class_="apphub_AppName").text.strip()
        html_source = response.text
        screenshot_matches = re.findall(r'g_rgScreenshotData\s*=\s*(\[.*?\]);', html_source, re.DOTALL)
        if screenshot_matches:
            screenshot_count = screenshot_matches[0].count('"filename"')
        else:
            screenshot_count = len(soup.find_all("div", class_=lambda x: x and 'highlight_screenshot' in x))
        desc_area = soup.find("div", id="game_area_description")
        desc_text = desc_area.text.strip() if desc_area else ""
        desc_length = len(desc_text)
        gif_count = 0
        if desc_area:
            gif_matches = re.findall(r'src="([^"]+?\.gif[^"]*?)"', str(desc_area), re.IGNORECASE)
            gif_count = len(gif_matches)
        tags = [tag_el.text.strip() for tag_el in soup.find_all("a", class_="app_tag")[:10]]
        
        # ===== 额外抓取封面图和简介 =====
        cover_url = ""
        short_desc = ""
        try:
            cover_img = soup.find("img", class_="game_header_image_full")
            if cover_img and cover_img.get("src"):
                cover_url = cover_img["src"]
            desc_short = soup.find("div", class_="game_description_snippet")
            if desc_short:
                short_desc = desc_short.text.strip()
            if not short_desc:
                if desc_area:
                    short_desc = desc_area.text.strip()[:300] + "..."
        except:
            pass
        
        return {
            "game_name": game_name,
            "screenshot_count": screenshot_count,
            "desc_length": desc_length,
            "has_gif": 1 if gif_count > 0 else 0,
            "tags": tags,
            "steam_url": url,
            "cover_url": cover_url,
            "short_desc": short_desc
        }
    except:
        return None

def show_game_search():
    st.subheader("🔍 搜索 Steam 游戏")
    st.caption("输入游戏名称或 AppID，获取游戏信息和相关教程")

    search_input = st.text_input("请输入游戏名称或 Steam AppID", placeholder="例如: 赛博朋克2077 或 1091500")

    if search_input:
        with st.spinner("正在搜索..."):
            app_id = None
            game_name_found = None
            
            if search_input.strip().isdigit():
                app_id = search_input.strip()
            else:
                try:
                    apps = get_steam_app_list()
                    search_lower = search_input.strip().lower()
                    matches = []
                    for app in apps:
                        if app.get('name') and search_lower in app['name'].lower():
                            matches.append(app)
                    
                    if not matches:
                        st.error(f"未找到名为 '{search_input}' 的游戏")
                        st.info("💡 提示：如果游戏名称是中文，请尝试使用英文名搜索（如 'Elden Ring'）")
                        return
                    
                    if len(matches) > 1:
                        st.info(f"找到 {len(matches)} 个匹配的游戏，请选择：")
                        options = [f"{m['name']} (AppID: {m['appid']})" for m in matches[:10]]
                        selected = st.selectbox("选择游戏", options)
                        if selected:
                            match = re.search(r'AppID: (\d+)', selected)
                            if match:
                                app_id = match.group(1)
                                game_name_found = selected.split(" (AppID:")[0]
                    else:
                        app_id = str(matches[0]['appid'])
                        game_name_found = matches[0]['name']
                except Exception as e:
                    st.error(f"搜索失败: {e}")
                    return
            
            if app_id and app_id != "0":
                game_info = fetch_steam_game_features(app_id)
                if game_info:
                    if game_name_found:
                        game_info['game_name'] = game_name_found
                    
                    st.success(f"✅ 找到游戏: {game_info['game_name']}")

                    # 布局：左侧封面图 + 右侧信息
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        if game_info.get('cover_url'):
                            st.image(game_info['cover_url'], use_container_width=True)
                        else:
                            st.info("📷 暂无封面图")

                    with col2:
                        st.markdown(f"### 🎮 {game_info['game_name']}")
                        if game_info.get('short_desc'):
                            st.markdown(f"**简介：** {game_info['short_desc']}")
                        else:
                            st.markdown("暂无简介")

                        if game_info.get('tags'):
                            st.markdown(f"**标签：** {', '.join(game_info['tags'][:5])}")

                        st.markdown(f"**Steam 页面：** [点击访问]({game_info['steam_url']})")

                        st.markdown("---")
                        st.markdown("**📺 在以下平台搜索教程：**")

                        search_name = game_info['game_name'].replace(" ", "+")
                        platform_links = {
                            "Bilibili": f"https://search.bilibili.com/all?keyword={search_name}+攻略",
                            "YouTube": f"https://www.youtube.com/results?search_query={search_name}+gameplay+guide",
                            "小黑盒": f"https://www.xiaoheihe.cn/games/search?q={search_name}",
                            "Steam 社区": f"https://steamcommunity.com/app/{app_id}/guides/"
                        }

                        cols = st.columns(4)
                        for idx, (platform, url) in enumerate(platform_links.items()):
                            with cols[idx]:
                                st.markdown(f"[{platform}]({url})")

                    st.markdown("---")

                    strategy_db = load_json_db(STRATEGY_DB_FILE)
                    related_strategies = []
                    for sid, item in strategy_db.items():
                        if game_info['game_name'].lower() in item.get('game_name', '').lower():
                            related_strategies.append(item)

                    if related_strategies:
                        st.subheader(f"📚 《{game_info['game_name']}》社区教程")
                        for item in related_strategies:
                            with st.expander(f"🎯 {item['title']} (by {item.get('author', '匿名')})"):
                                st.caption(f"🏷️ 标签: {', '.join(item.get('tags', []))}")
                                if item.get("steam_url"):
                                    st.markdown(f"🔗 [Steam 链接]({item['steam_url']})")
                                st.markdown(item["content"])
                    else:
                        st.info(f"📭 暂无《{game_info['game_name']}》的社区教程，成为第一个分享者吧！")
                        if st.button("📝 发布此游戏教程"):
                            st.session_state['publish_game'] = game_info['game_name']
                            st.rerun()
                else:
                    st.error("无法获取游戏详情，请检查 AppID 是否正确")

# ==========================================
# 2. 游戏推荐引擎
# ==========================================
GAME_DATABASE = [
    {
        "name": "黑神话：悟空",
        "types": ["动作", "角色扮演"],
        "difficulty": 8,
        "steam_url": "https://store.steampowered.com/app/2358720/Black_Myth_Wukong/",
        "tags": ["动作", "冒险", "中国神话"],
        "reason_easy": "虽然有一定难度，但战斗系统设计精妙，新手也能快速上手",
        "reason_hard": "极具挑战性的 Boss 战，适合喜欢硬核动作的玩家",
        "reason_social": "游戏内无联机，适合享受单人沉浸式体验的玩家",
        "reason_solo": "单人剧情体验极佳，适合独自探索",
        "tutorial_count": 3,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/2358720/header.jpg"
    },
    {
        "name": "艾尔登法环",
        "types": ["动作", "角色扮演"],
        "difficulty": 9,
        "steam_url": "https://store.steampowered.com/app/1245620/Elden_Ring/",
        "tags": ["动作", "开放世界", "魂系"],
        "reason_easy": "开放世界设计让玩家可以自由探索，遇到困难时可以选择绕路",
        "reason_hard": "魂系游戏的巅峰之作，极具挑战性",
        "reason_social": "支持联机合作，可以和好友一起挑战",
        "reason_solo": "单人探索体验极佳，沉浸感十足",
        "tutorial_count": 5,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg"
    },
    {
        "name": "赛博朋克2077",
        "types": ["角色扮演", "射击"],
        "difficulty": 6,
        "steam_url": "https://store.steampowered.com/app/1091500/Cyberpunk_2077/",
        "tags": ["RPG", "科幻", "开放世界"],
        "reason_easy": "多种难度可选，剧情驱动型游戏，上手门槛低",
        "reason_hard": "丰富的 Build 系统，为高玩提供了深度研究空间",
        "reason_social": "无需联机，单人剧情为主",
        "reason_solo": "优秀的单人剧情体验，沉浸感强",
        "tutorial_count": 4,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1091500/header.jpg"
    },
    {
        "name": "星露谷物语",
        "types": ["模拟", "休闲", "角色扮演"],
        "difficulty": 3,
        "steam_url": "https://store.steampowered.com/app/413150/Stardew_Valley/",
        "tags": ["模拟", "休闲", "农场"],
        "reason_easy": "上手简单，轻松治愈的农场生活",
        "reason_hard": "深度经营系统，追求完美农场需要精心规划",
        "reason_social": "支持多人联机，可以和好友一起经营农场",
        "reason_solo": "单人游玩同样有趣，节奏由你掌控",
        "tutorial_count": 4,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/413150/header.jpg"
    },
    {
        "name": "空洞骑士",
        "types": ["动作", "冒险"],
        "difficulty": 8,
        "steam_url": "https://store.steampowered.com/app/367520/Hollow_Knight/",
        "tags": ["动作", "平台跳跃", "手绘风"],
        "reason_easy": "操作简单易上手，难度曲线平滑",
        "reason_hard": "后期的苦痛之路和神居挑战极具难度",
        "reason_social": "纯单人游戏，专注个人体验",
        "reason_solo": "沉浸式的单人冒险，推荐给喜欢探索的玩家",
        "tutorial_count": 3,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/367520/header.jpg"
    },
    {
        "name": "巫师3：狂猎",
        "types": ["角色扮演", "动作"],
        "difficulty": 6,
        "steam_url": "https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/",
        "tags": ["RPG", "开放世界", "剧情"],
        "reason_easy": "剧情驱动，多种难度可选",
        "reason_hard": "死而无憾难度极具挑战性",
        "reason_social": "纯单人游戏，沉浸式剧情体验",
        "reason_solo": "剧情深度极高，适合喜欢故事驱动型游戏的玩家",
        "tutorial_count": 5,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/292030/header.jpg"
    },
    {
        "name": "只狼：影逝二度",
        "types": ["动作"],
        "difficulty": 9,
        "steam_url": "https://store.steampowered.com/app/814380/Sekiro_Shadows_Die_Twice/",
        "tags": ["动作", "魂系", "日本战国"],
        "reason_easy": "战斗节奏清晰，拼刀系统一旦上手极具爽感",
        "reason_hard": "魂系游戏中最考验反应速度的作品之一",
        "reason_social": "纯单人游戏",
        "reason_solo": "单人挑战，成就感极强",
        "tutorial_count": 3,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/814380/header.jpg"
    },
    {
        "name": "文明6",
        "types": ["策略", "模拟"],
        "difficulty": 7,
        "steam_url": "https://store.steampowered.com/app/289070/Sid_Meiers_Civilization_VI/",
        "tags": ["策略", "回合制", "历史"],
        "reason_easy": "有详细的新手教程，多种难度可选",
        "reason_hard": "神级难度下需要精密的运营和策略规划",
        "reason_social": "支持多人联机，可以和朋友一较高下",
        "reason_solo": "单人模式同样有趣，一局可以玩很久",
        "tutorial_count": 4,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/289070/header.jpg"
    },
    {
        "name": "双人成行",
        "types": ["动作", "冒险"],
        "difficulty": 4,
        "steam_url": "https://store.steampowered.com/app/1426210/It_Takes_Two/",
        "tags": ["合作", "双人", "创意"],
        "reason_easy": "难度适中，适合新手",
        "reason_hard": "部分关卡需要精妙配合，挑战性十足",
        "reason_social": "必须双人合作，是和朋友一起玩的最佳选择",
        "reason_solo": "单人无法游玩，需要找一个朋友一起",
        "tutorial_count": 2,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1426210/header.jpg"
    },
    {
        "name": "死亡搁浅",
        "types": ["冒险", "模拟"],
        "difficulty": 5,
        "steam_url": "https://store.steampowered.com/app/1190460/Death_Stranding/",
        "tags": ["冒险", "送货", "小岛秀夫"],
        "reason_easy": "节奏舒缓，上手门槛低",
        "reason_hard": "高难度下资源管理极具挑战",
        "reason_social": "异步联机系统，可以互相帮助",
        "reason_solo": "单人体验极佳，剧情深刻",
        "tutorial_count": 2,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1190460/header.jpg"
    },
    {
        "name": "CS:GO",
        "types": ["射击", "竞技"],
        "difficulty": 7,
        "steam_url": "https://store.steampowered.com/app/730/CounterStrike_Global_Offensive/",
        "tags": ["射击", "竞技", "多人"],
        "reason_easy": "有休闲模式，新手友好",
        "reason_hard": "竞技模式极具深度，需要团队配合和枪法",
        "reason_social": "和朋友一起开黑的最佳选择",
        "reason_solo": "单人匹配也能玩，但组队体验更佳",
        "tutorial_count": 3,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/730/header.jpg"
    },
    {
        "name": "DOTA2",
        "types": ["策略", "竞技"],
        "difficulty": 8,
        "steam_url": "https://store.steampowered.com/app/570/DOTA_2/",
        "tags": ["MOBA", "竞技", "多人"],
        "reason_easy": "有新手教程和 AI 模式",
        "reason_hard": "竞技深度极高，需要百小时入门",
        "reason_social": "团队游戏，和朋友开黑体验更佳",
        "reason_solo": "单人匹配也能玩，但团队配合是核心",
        "tutorial_count": 4,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/570/header.jpg"
    },
    {
        "name": "地平线5",
        "types": ["赛车", "竞速"],
        "difficulty": 4,
        "steam_url": "https://store.steampowered.com/app/1551360/Forza_Horizon_5/",
        "tags": ["赛车", "开放世界", "竞速"],
        "reason_easy": "上手简单，辅助功能丰富",
        "reason_hard": "高难度下需要精准操控",
        "reason_social": "支持多人竞速，可以和好友飙车",
        "reason_solo": "单人模式内容丰富，探索乐趣十足",
        "tutorial_count": 2,
        "cover": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1551360/header.jpg"
    },
    {
        "name": "我的世界",
        "types": ["模拟", "冒险"],
        "difficulty": 3,
        "steam_url": "https://www.minecraft.net/zh-hans",
        "tags": ["沙盒", "创造", "生存"],
        "reason_easy": "上手简单，自由度极高",
        "reason_hard": "生存模式高难度下充满挑战",
        "reason_social": "支持多人联机，和好友一起建造",
        "reason_solo": "单人模式同样乐趣无穷",
        "tutorial_count": 5,
        "cover": "https://www.minecraft.net/content/dam/games/minecraft/key-art/GamesSubkey_Minecraft_003.jpg"
    },
]

def get_recommendations(user_data):
    """根据用户问卷数据生成个性化游戏推荐"""
    user_types = user_data.get("game_types", [])
    user_skill = user_data.get("gaming_skill", 5)
    quit_reasons = user_data.get("quit_reason", [])
    social_preference = user_data.get("social_preference", 5)
    
    recommendations = []
    
    for game in GAME_DATABASE:
        score = 0
        reasons = []
        
        # 1. 类型匹配（核心权重）
        matched_types = [t for t in user_types if t in game["types"]]
        if matched_types:
            score += 30 * (len(matched_types) / len(game["types"]))
            reasons.append(f"符合你喜欢的 {', '.join(matched_types)} 类型")
        else:
            # 部分匹配：如果有任一类型重合
            for ut in user_types:
                for gt in game["types"]:
                    if ut in gt or gt in ut:
                        score += 10
                        reasons.append(f"与 {gt} 类型相关")
                        break
                else:
                    continue
                break
        
        # 2. 难度适配
        if user_skill <= 3:
            if game["difficulty"] <= 4:
                score += 20
                reasons.append("难度适中，适合新手入门")
            elif game["difficulty"] <= 6:
                score += 10
                reasons.append("有一定挑战性，但新手也能玩")
        elif user_skill <= 6:
            if 4 <= game["difficulty"] <= 7:
                score += 20
                reasons.append("难度平衡，适合中等水平玩家")
            elif game["difficulty"] <= 4:
                score += 10
                reasons.append("操作简单，适合放松游玩")
        else:
            if game["difficulty"] >= 7:
                score += 20
                reasons.append("极具挑战性，适合高水平玩家")
            elif game["difficulty"] >= 5:
                score += 10
                reasons.append("有一定难度，值得挑战")
        
        # 3. 弃坑原因适配
        if quit_reasons:
            if "没时间" in quit_reasons:
                if game["difficulty"] <= 5:
                    score += 10
                    reasons.append("学习成本低，适合碎片化时间游玩")
                if "休闲" in game["types"] or "模拟" in game["types"]:
                    score += 5
                    reasons.append("节奏舒缓，无需长期连续投入")
            
            if "太难了" in quit_reasons:
                if game["difficulty"] <= 5:
                    score += 15
                    reasons.append("难度友好，不用担心卡关")
                elif game["difficulty"] <= 6:
                    score += 8
                    reasons.append("有难度选项，可以自行调整")
            
            if "没朋友一起玩" in quit_reasons:
                if "合作" in game["tags"] or "双人" in game["tags"]:
                    score += 15
                    reasons.append("支持多人联机，可以和朋友一起玩")
                elif "多人" in game["tags"]:
                    score += 10
                    reasons.append("有多人模式，可以和陌生人组队")
                else:
                    score += 8
                    reasons.append("纯单人游戏，不需要朋友也能玩")
            
            if "剧情无聊" in quit_reasons:
                if "剧情" in game["tags"] or "RPG" in game["types"]:
                    score += 15
                    reasons.append("剧情深度优秀，故事引人入胜")
            
            if "内容太少" in quit_reasons:
                if "开放世界" in game["tags"] or "沙盒" in game["tags"]:
                    score += 15
                    reasons.append("内容丰富，可玩性高")
                elif game["tutorial_count"] >= 3:
                    score += 10
                    reasons.append("社区有丰富攻略，不用担心没有内容")
        
        # 4. 社区教程丰富度加成
        if game["tutorial_count"] >= 4:
            score += 5
            reasons.append("社区有大量教程资源可供参考")
        
        # 5. 社交偏好适配
        if social_preference >= 7:
            if "多人" in game["tags"] or "合作" in game["tags"]:
                score += 10
                reasons.append("适合联机/社交，能认识新朋友")
        else:
            if "单人" in game["tags"] or "剧情" in game["tags"]:
                score += 8
                reasons.append("适合独自享受，沉浸感强")
        
        # 避免重复原因
        reasons = list(set(reasons))
        
        recommendations.append({
            "game": game,
            "score": score,
            "reasons": reasons[:3]
        })
    
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:6]

# ==========================================
# 3. 用户注册 + 问卷 + 实时推荐
# ==========================================
def show_registration_survey():
    st.subheader("🧭 欢迎加入 Compass！请完成玩家档案")
    st.caption("用数据指引你的游戏之路")

    with st.form("registration_form"):
        username = st.text_input("玩家昵称*", max_chars=20)

        st.markdown("---")
        st.caption("📊 以下数据将用于 Compass 数据科学分析")

        col1, col2 = st.columns(2)
        with col1:
            gender = st.radio("性别", ["男", "女", "不愿透露"], horizontal=True)
        with col2:
            age = st.selectbox("年龄段", ["18岁以下", "18-24岁", "25-30岁", "31-35岁", "36岁以上"])

        st.markdown("#### 🎯 游戏行为")
        col1, col2 = st.columns(2)
        with col1:
            game_types = st.multiselect(
                "喜欢的游戏类型",
                ["动作", "角色扮演", "策略", "射击", "模拟", "体育", "休闲", "恐怖", "解谜", "竞速"]
            )
            play_time = st.select_slider(
                "每天平均游戏时长",
                options=["<1小时", "1-3小时", "3-5小时", "5-8小时", "8小时以上"]
            )
        with col2:
            gaming_years = st.slider("游戏龄（年）", 1, 30, 5)
            weekly_frequency = st.select_slider(
                "每周游戏频率",
                options=["偶尔（1-2天）", "经常（3-4天）", "频繁（5-6天）", "几乎每天"]
            )

        st.markdown("#### 🧠 游戏态度")
        col1, col2 = st.columns(2)
        with col1:
            quit_reason = st.multiselect(
                "弃坑原因（选1-3个）",
                ["太难了", "没时间", "没朋友一起玩", "剧情无聊", "内容太少", "优化差/卡顿", "其他"]
            )
        with col2:
            purchase_factor = st.multiselect(
                "购买因素（选1-3个）",
                ["画面", "玩法", "价格", "朋友推荐", "媒体评分", "Steam评价", "开发者口碑"]
            )

        st.markdown("#### 📝 主观评分（1-10）")
        col1, col2, col3 = st.columns(3)
        with col1:
            gaming_skill = st.slider("技术水平", 1, 10,
