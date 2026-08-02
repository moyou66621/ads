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
# 2. 游戏推荐引擎（连接 Steam）
# ==========================================

def fetch_steam_hot_games(limit=20):
    """从 Steam 获取热门游戏列表"""
    try:
        url = "https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            return None
        
        data = response.json()
        all_apps = data['applist']['apps']
        all_apps = [app for app in all_apps if app.get('name', '').strip()]
        
        selected = all_apps[:limit]
        
        games = []
        for app in selected:
            app_id = app['appid']
            name = app['name']
            
            detail_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cn&l=zh"
            try:
                detail_resp = requests.get(detail_url, timeout=10)
                if detail_resp.status_code == 200:
                    detail_data = detail_resp.json()
                    if detail_data.get(str(app_id), {}).get('success'):
                        data = detail_data[str(app_id)]['data']
                        
                        genres = [g['description'] for g in data.get('genres', [])][:2]
                        tags = list(data.get('tags', {}).keys())[:3] if 'tags' in data else []
                        header_img = data.get('header_image', '')
                        short_desc = data.get('short_description', '')[:150]
                        
                        games.append({
                            "name": name,
                            "appid": app_id,
                            "types": genres,
                            "tags": tags,
                            "steam_url": f"https://store.steampowered.com/app/{app_id}/",
                            "cover_url": header_img,
                            "short_desc": short_desc,
                            "tutorial_count": 0
                        })
            except:
                continue
        
        return games
    except Exception as e:
        print(f"⚠️ 获取Steam热门游戏失败: {e}")
        return None

# ==========================================
# 备选游戏数据库（当 Steam API 失败时使用）
# ==========================================
GAME_DATABASE = [
    {
        "name": "黑神话：悟空",
        "types": ["动作", "角色扮演"],
        "tags": ["动作", "冒险", "中国神话"],
        "steam_url": "https://store.steampowered.com/app/2358720/Black_Myth_Wukong/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/2358720/header.jpg",
        "short_desc": "这是一款以中国神话为背景的动作角色扮演游戏。"
    },
    {
        "name": "艾尔登法环",
        "types": ["动作", "角色扮演"],
        "tags": ["动作", "开放世界", "魂系"],
        "steam_url": "https://store.steampowered.com/app/1245620/Elden_Ring/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg",
        "short_desc": "充满挑战的开放世界动作RPG。"
    },
    {
        "name": "赛博朋克2077",
        "types": ["角色扮演", "射击"],
        "tags": ["RPG", "科幻", "开放世界"],
        "steam_url": "https://store.steampowered.com/app/1091500/Cyberpunk_2077/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1091500/header.jpg",
        "short_desc": "在夜之城中书写你的传奇故事。"
    },
    {
        "name": "星露谷物语",
        "types": ["模拟", "休闲"],
        "tags": ["模拟", "休闲", "农场"],
        "steam_url": "https://store.steampowered.com/app/413150/Stardew_Valley/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/413150/header.jpg",
        "short_desc": "经营你的农场，享受乡村生活。"
    },
    {
        "name": "空洞骑士",
        "types": ["动作", "冒险"],
        "tags": ["动作", "平台跳跃", "手绘风"],
        "steam_url": "https://store.steampowered.com/app/367520/Hollow_Knight/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/367520/header.jpg",
        "short_desc": "探索一个被遗忘的王国。"
    },
    {
        "name": "巫师3：狂猎",
        "types": ["角色扮演", "动作"],
        "tags": ["RPG", "开放世界", "剧情"],
        "steam_url": "https://store.steampowered.com/app/292030/The_Witcher_3_Wild_Hunt/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/292030/header.jpg",
        "short_desc": "狩魔猎人的史诗冒险。"
    },
    {
        "name": "只狼：影逝二度",
        "types": ["动作"],
        "tags": ["动作", "魂系", "日本战国"],
        "steam_url": "https://store.steampowered.com/app/814380/Sekiro_Shadows_Die_Twice/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/814380/header.jpg",
        "short_desc": "在战国时代展开生死对决。"
    },
    {
        "name": "文明6",
        "types": ["策略", "模拟"],
        "tags": ["策略", "回合制", "历史"],
        "steam_url": "https://store.steampowered.com/app/289070/Sid_Meiers_Civilization_VI/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/289070/header.jpg",
        "short_desc": "建立你的帝国，引领人类文明。"
    },
    {
        "name": "双人成行",
        "types": ["动作", "冒险"],
        "tags": ["合作", "双人", "创意"],
        "steam_url": "https://store.steampowered.com/app/1426210/It_Takes_Two/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1426210/header.jpg",
        "short_desc": "双人合作冒险，体验独特的游戏世界。"
    },
    {
        "name": "死亡搁浅",
        "types": ["冒险", "模拟"],
        "tags": ["冒险", "送货", "小岛秀夫"],
        "steam_url": "https://store.steampowered.com/app/1190460/Death_Stranding/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1190460/header.jpg",
        "short_desc": "在破碎的世界中重建连接。"
    },
    {
        "name": "CS:GO",
        "types": ["射击", "竞技"],
        "tags": ["射击", "竞技", "多人"],
        "steam_url": "https://store.steampowered.com/app/730/CounterStrike_Global_Offensive/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/730/header.jpg",
        "short_desc": "经典的第一人称射击竞技游戏。"
    },
    {
        "name": "DOTA2",
        "types": ["策略", "竞技"],
        "tags": ["MOBA", "竞技", "多人"],
        "steam_url": "https://store.steampowered.com/app/570/DOTA_2/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/570/header.jpg",
        "short_desc": "最具深度的MOBA竞技游戏。"
    },
    {
        "name": "地平线5",
        "types": ["赛车", "竞速"],
        "tags": ["赛车", "开放世界", "竞速"],
        "steam_url": "https://store.steampowered.com/app/1551360/Forza_Horizon_5/",
        "cover_url": "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1551360/header.jpg",
        "short_desc": "在墨西哥体验极速竞速的乐趣。"
    },
    {
        "name": "我的世界",
        "types": ["模拟", "冒险"],
        "tags": ["沙盒", "创造", "生存"],
        "steam_url": "https://www.minecraft.net/zh-hans",
        "cover_url": "https://www.minecraft.net/content/dam/games/minecraft/key-art/GamesSubkey_Minecraft_003.jpg",
        "short_desc": "无限创造和探索的沙盒世界。"
    }
]

def get_steam_games_for_recommendation():
    """获取用于推荐的游戏列表（优先从 Steam 获取，失败时使用备选）"""
    games = fetch_steam_hot_games(20)
    if games and len(games) >= 5:
        return games
    return GAME_DATABASE

def get_recommendations(user_data):
    """根据用户问卷数据生成个性化游戏推荐（连接 Steam）"""
    user_types = user_data.get("game_types", [])
    user_skill = user_data.get("gaming_skill", 5)
    quit_reasons = user_data.get("quit_reason", [])
    social_preference = user_data.get("social_preference", 5)
    
    games = get_steam_games_for_recommendation()
    
    if not games:
        return []
    
    strategy_db = load_json_db(STRATEGY_DB_FILE)
    tutorial_games = {}
    for sid, item in strategy_db.items():
        game_name = item.get('game_name', '')
        if game_name:
            tutorial_games[game_name] = tutorial_games.get(game_name, 0) + 1
    
    recommendations = []
    
    for game in games:
        score = 0
        reasons = []
        
        game_name = game.get('name', '')
        game_types = game.get('types', [])
        game_tags = game.get('tags', [])
        game_tutorial_count = 0
        
        for key in tutorial_games:
            if game_name.lower() in key.lower() or key.lower() in game_name.lower():
                game_tutorial_count = tutorial_games[key]
                break
        
        # 1. 类型匹配
        matched_types = [t for t in user_types if t in game_types or any(t in gt or gt in t for gt in game_types)]
        if matched_types:
            score += 30
            reasons.append(f"符合你喜欢的 {', '.join(matched_types[:2])} 类型")
        else:
            for ut in user_types:
                for gt in game_types:
                    if ut in gt or gt in ut:
                        score += 10
                        reasons.append(f"与 {gt} 类型相关")
                        break
                else:
                    continue
                break
        
        # 2. 难度估算
        difficulty = 5
        if any(t in ['魂系', '硬核', '竞技', '困难'] for t in game_tags):
            difficulty = 8
        elif any(t in ['休闲', '轻松', '治愈'] for t in game_tags):
            difficulty = 3
        
        if user_skill <= 3:
            if difficulty <= 4:
                score += 20
                reasons.append("难度适中，适合新手入门")
            elif difficulty <= 6:
                score += 10
                reasons.append("有一定挑战性，但新手也能玩")
        elif user_skill <= 6:
            if 4 <= difficulty <= 7:
                score += 20
                reasons.append("难度平衡，适合中等水平玩家")
            elif difficulty <= 4:
                score += 10
                reasons.append("操作简单，适合放松游玩")
        else:
            if difficulty >= 7:
                score += 20
                reasons.append("极具挑战性，适合高水平玩家")
            elif difficulty >= 5:
                score += 10
                reasons.append("有一定难度，值得挑战")
        
        # 3. 弃坑原因适配
        if quit_reasons:
            if "没时间" in quit_reasons:
                if difficulty <= 5:
                    score += 10
                    reasons.append("学习成本低，适合碎片化时间游玩")
            
            if "太难了" in quit_reasons:
                if difficulty <= 5:
                    score += 15
                    reasons.append("难度友好，不用担心卡关")
            
            if "没朋友一起玩" in quit_reasons:
                if any(t in ['多人', '合作', '联机'] for t in game_tags):
                    score += 15
                    reasons.append("支持多人联机，可以和朋友一起玩")
                elif any(t in ['单人', '单机'] for t in game_tags):
                    score += 8
                    reasons.append("纯单人游戏，不需要朋友也能玩")
            
            if "剧情无聊" in quit_reasons:
                if any(t in ['剧情', '角色扮演', 'RPG'] for t in game_tags + game_types):
                    score += 15
                    reasons.append("剧情深度优秀，故事引人入胜")
        
        # 4. 社区教程加成
        if game_tutorial_count >= 2:
            score += 10
            reasons.append(f"社区有 {game_tutorial_count} 篇教程可供参考")
        elif game_tutorial_count >= 1:
            score += 5
            reasons.append(f"社区有 {game_tutorial_count} 篇教程")
        
        # 5. 社交偏好
        if social_preference >= 7:
            if any(t in ['多人', '合作', '联机'] for t in game_tags):
                score += 10
                reasons.append("适合联机/社交，能认识新朋友")
        else:
            if any(t in ['单人', '单机', '剧情'] for t in game_tags):
                score += 8
                reasons.append("适合独自享受，沉浸感强")
        
        reasons = list(set(reasons))
        
        if reasons or score > 10:
            recommendations.append({
                "game": game,
                "score": score,
                "reasons": reasons[:3],
                "tutorial_count": game_tutorial_count
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
            gaming_skill = st.slider("技术水平", 1, 10, 5)
        with col2:
            social_preference = st.slider("社交偏好", 1, 10, 5)
        with col3:
            completionist = st.slider("成就追求", 1, 10, 5)

        submitted = st.form_submit_button("🚀 加入 Compass")

        if submitted:
            if not username.strip():
                st.error("请输入昵称！")
                return None

            user_data = {
                "username": username.strip(),
                "gender": gender,
                "age": age,
                "game_types": game_types,
                "play_time": play_time,
                "gaming_years": gaming_years,
                "weekly_frequency": weekly_frequency,
                "quit_reason": quit_reason,
                "purchase_factor": purchase_factor,
                "gaming_skill": gaming_skill,
                "social_preference": social_preference,
                "completionist": completionist,
                "register_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            db = load_json_db(USER_DATA_FILE)
            db[username.strip()] = user_data
            save_json_db(USER_DATA_FILE, db)
            log_activity(username.strip(), "注册")

            st.success(f"✅ 欢迎来到 Compass，{username}！")
            
            st.markdown("---")
            st.subheader("🎯 根据你的游戏偏好，Compass 为你推荐：")
            st.caption("基于你的游戏类型偏好、技术水平、弃坑原因生成的个性化推荐")
            
            recommendations = get_recommendations(user_data)
            
            if recommendations:
                cols = st.columns(3)
                for idx, rec in enumerate(recommendations):
                    game = rec["game"]
                    with cols[idx % 3]:
                        with st.container(border=True):
                            st.markdown(f"**🎮 {game.get('name', '未知游戏')}**")
                            if game.get('cover_url'):
                                st.image(game['cover_url'], use_container_width=True)
                            st.caption(f"🏷️ {', '.join(game.get('tags', [])[:2])}")
                            if game.get('steam_url'):
                                st.markdown(f"[查看 Steam]({game['steam_url']})")
                            st.markdown("---")
                            st.caption("💡 **推荐理由：**")
                            for reason in rec["reasons"]:
                                st.write(f"• {reason}")
                            
                            if rec.get("tutorial_count", 0) > 0:
                                st.caption(f"📚 社区有 {rec['tutorial_count']} 篇教程")
            else:
                st.info("暂未找到匹配的游戏推荐，试试在搜索页面查找你喜欢的游戏吧！")
            
            st.balloons()
            return username
    return None

# ==========================================
# 4. 数据科学看板
# ==========================================
def show_deep_data_insights():
    st.subheader("📊 Compass 数据科学看板")
    user_db = load_json_db(USER_DATA_FILE)

    if len(user_db) == 0:
        st.info("📭 暂无玩家数据")
        return

    df = pd.DataFrame(user_db).T.reset_index().rename(columns={"index": "用户名"})
    st.success(f"📌 基于 {len(user_db)} 位玩家的数据分析")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        gender_counts = df["gender"].value_counts().reset_index()
        gender_counts.columns = ["性别", "人数"]
        fig1 = px.pie(gender_counts, values="人数", names="性别", color_discrete_sequence=px.colors.qualitative.Set2)
        fig1.update_layout(height=280, title="性别分布")
        st.plotly_chart(fig1, use_container_width=True)

        time_counts = df["play_time"].value_counts().reset_index()
        time_counts.columns = ["时长", "人数"]
        time_order = ["<1小时", "1-3小时", "3-5小时", "5-8小时", "8小时以上"]
        time_counts["时长"] = pd.Categorical(time_counts["时长"], categories=time_order, ordered=True)
        time_counts = time_counts.sort_values("时长")
        fig2 = px.bar(time_counts, x="时长", y="人数", color="时长", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(height=280, title="游戏时长分布", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        all_types = []
        for types in df["game_types"]:
            if isinstance(types, list):
                all_types.extend(types)
        if all_types:
            type_counts = pd.Series(all_types).value_counts().reset_index()
            type_counts.columns = ["游戏类型", "人数"]
            fig3 = px.bar(type_counts, x="人数", y="游戏类型", orientation="h", color="人数", color_continuous_scale="Blues")
            fig3.update_layout(height=280, title="热门游戏类型", showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

        all_reasons = []
        for reasons in df["quit_reason"]:
            if isinstance(reasons, list):
                all_reasons.extend(reasons)
        if all_reasons:
            reason_counts = pd.Series(all_reasons).value_counts().reset_index()
            reason_counts.columns = ["弃坑原因", "人数"]
            fig4 = px.bar(reason_counts, x="人数", y="弃坑原因", orientation="h", color="人数", color_continuous_scale="Oranges")
            fig4.update_layout(height=280, title="弃坑原因", showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 游戏类型 × 弃坑原因")
    if len(user_db) >= 5:
        cross_data = []
        for _, row in df.iterrows():
            types = row["game_types"] if isinstance(row["game_types"], list) else []
            reasons = row["quit_reason"] if isinstance(row["quit_reason"], list) else []
            for t in types:
                for r in reasons:
                    cross_data.append({"游戏类型": t, "弃坑原因": r})
        if cross_data:
            cross_df = pd.DataFrame(cross_data)
            cross_tab = pd.crosstab(cross_df["游戏类型"], cross_df["弃坑原因"])
            fig5 = px.imshow(cross_tab, text_auto=True, color_continuous_scale="RdBu_r", aspect="auto")
            fig5.update_layout(height=380)
            st.plotly_chart(fig5, use_container_width=True)
            st.caption("💡 颜色越深表示该类型玩家更容易因该原因弃坑")

    st.markdown("---")
    st.subheader("🧩 玩家智能分群")
    if len(user_db) >= 8:
        try:
            cluster_features = []
            for _, row in df.iterrows():
                time_map = {"<1小时": 0.5, "1-3小时": 2, "3-5小时": 4, "5-8小时": 6.5, "8小时以上": 9}
                freq_map = {"偶尔（1-2天）": 1.5, "经常（3-4天）": 3.5, "频繁（5-6天）": 5.5, "几乎每天": 7}
                features = [
                    time_map.get(row.get("play_time", "1-3小时"), 2),
                    freq_map.get(row.get("weekly_frequency", "经常（3-4天）"), 3.5),
                    row.get("gaming_years", 5),
                    row.get("gaming_skill", 5),
                    row.get("social_preference", 5),
                    row.get("completionist", 5),
                    len(row.get("game_types", [])),
                    len(row.get("quit_reason", []))
                ]
                cluster_features.append(features)

            scaler = StandardScaler()
            scaled = scaler.fit_transform(cluster_features)
            kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
            df["分群"] = kmeans.fit_predict(scaled)

            cluster_names = {}
            for cid in df["分群"].unique():
                subset = df[df["分群"] == cid]
                avg_social = subset["social_preference"].mean()
                avg_time = subset["play_time"].apply(lambda x: {"<1小时": 0.5, "1-3小时": 2, "3-5小时": 4, "5-8小时": 6.5, "8小时以上": 9}.get(x, 2)).mean()
                if avg_social > 6 and avg_time > 4:
                    name = "🎮 社交硬核玩家"
                elif avg_social > 6:
                    name = "🤝 社交休闲玩家"
                elif avg_time > 4:
                    name = "🏆 独狼硬核玩家"
                else:
                    name = "🌿 休闲探索玩家"
                cluster_names[cid] = name

            df["分群名称"] = df["分群"].map(cluster_names)

            col1, col2 = st.columns(2)
            with col1:
                counts = df["分群名称"].value_counts().reset_index()
                counts.columns = ["类型", "人数"]
                fig6 = px.pie(counts, values="人数", names="类型", color_discrete_sequence=px.colors.qualitative.Set3)
                fig6.update_layout(height=300, title="玩家分群")
                st.plotly_chart(fig6, use_container_width=True)

            with col2:
                radar_data = []
                for cid in sorted(df["分群"].unique()):
                    subset = df[df["分群"] == cid]
                    radar_data.append({
                        "群组": cluster_names[cid],
                        "技术水平": subset["gaming_skill"].mean(),
                        "社交偏好": subset["social_preference"].mean(),
                        "成就追求": subset["completionist"].mean(),
                        "游戏龄": subset["gaming_years"].mean()
                    })
                if radar_data:
                    radar_df = pd.DataFrame(radar_data)
                    fig7 = go.Figure()
                    for _, row in radar_df.iterrows():
                        fig7.add_trace(go.Scatterpolar(
                            r=[row["技术水平"], row["社交偏好"], row["成就追求"], row["游戏龄"]],
                            theta=["技术水平", "社交偏好", "成就追求", "游戏龄"],
                            fill='toself',
                            name=row["群组"]
                        ))
                    fig7.update_layout(height=300, polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
                    st.plotly_chart(fig7, use_container_width=True)
        except Exception as e:
            st.warning(f"聚类分析需要更多数据")

    with st.expander("📋 查看数据汇总"):
        st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🧠 数据洞察报告")
    st.caption("基于以上数据的自动分析，为社区运营提供数据支撑")

    total_users = len(df)
    top_genre = "未知"
    top_genre_count = 0
    if all_types:
        type_counts = pd.Series(all_types).value_counts()
        top_genre = type_counts.index[0]
        top_genre_count = type_counts.iloc[0]

    top_reason = "未知"
    top_reason_count = 0
    if all_reasons:
        reason_counts = pd.Series(all_reasons).value_counts()
        top_reason = reason_counts.index[0]
        top_reason_count = reason_counts.iloc[0]

    male_pct = len(df[df["gender"] == "男"]) / total_users * 100 if total_users > 0 else 0
    female_pct = len(df[df["gender"] == "女"]) / total_users * 100 if total_users > 0 else 0

    age_counts = df["age"].value_counts()
    top_age = age_counts.index[0] if len(age_counts) > 0 else "未知"

    time_counts = df["play_time"].value_counts()
    top_time = time_counts.index[0] if len(time_counts) > 0 else "未知"

    cluster_names_list = []
    if "分群名称" in df.columns:
        cluster_names_list = df["分群名称"].value_counts().index.tolist()

    report_lines = []

    report_lines.append(f"📊 **社区概览**")
    report_lines.append(f"- 社区当前共有 **{total_users}** 位注册玩家。")

    if male_pct > 0 or female_pct > 0:
        report_lines.append(f"- 性别比例：男性 {male_pct:.1f}%，女性 {female_pct:.1f}%。")

    report_lines.append(f"- 核心玩家年龄段为 **{top_age}**（{age_counts[top_age]} 人，占比 {age_counts[top_age]/total_users*100:.1f}%）。")

    if all_types:
        report_lines.append("")
        report_lines.append(f"🎯 **热门游戏类型分析**")
        report_lines.append(f"- **{top_genre}** 是最受欢迎的游戏类型，被 {top_genre_count} 位玩家提及（{top_genre_count/total_users*100:.1f}%）。")
        report_lines.append(f"- 排名前五的类型：{', '.join(type_counts.head(5).index.tolist())}。")
        report_lines.append(f"- 💡 **运营建议**：优先增加 **{top_genre}** 类游戏的教程内容，该品类覆盖了超过 {top_genre_count/total_users*100:.0f}% 的玩家。")

    if all_reasons:
        report_lines.append("")
        report_lines.append(f"⚠️ **弃坑风险分析**")
        report_lines.append(f"- **{top_reason}** 是玩家弃坑的首要原因（{top_reason_count} 人，{top_reason_count/total_users*100:.1f}%）。")
        report_lines.append(f"- 主要弃坑原因 Top 3：{', '.join(reason_counts.head(3).index.tolist())}。")
        
        if top_reason == "没时间":
            report_lines.append(f"- 💡 **运营建议**：创作更多 **碎片化内容**（3-5分钟可读完的微攻略），降低玩家的时间门槛。")
        elif top_reason == "太难了":
            report_lines.append(f"- 💡 **运营建议**：重点制作 **新手入门教程** 和 **避坑指南**，帮助玩家跨过初始难度障碍。")
        elif top_reason == "没朋友一起玩":
            report_lines.append(f"- 💡 **运营建议**：强化社区互动功能，组织 **联机活动** 和 **组队匹配**，帮助玩家找到玩伴。")

    report_lines.append("")
    report_lines.append(f"⏰ **玩家活跃度分析**")
    report_lines.append(f"- 最主流的游戏时长区间是 **{top_time}**，占比 {time_counts[top_time]/total_users*100:.1f}%。")
    if top_time in ["3-5小时", "5-8小时", "8小时以上"]:
        report_lines.append(f"- 社区以 **中度至重度玩家** 为主，建议提供更多 **深度攻略** 和 **进阶内容**。")
    else:
        report_lines.append(f"- 社区以 **轻度至中度玩家** 为主，建议提供更多 **快速上手指南** 和 **碎片化内容**。")

    if cluster_names_list:
        report_lines.append("")
        report_lines.append(f"👥 **玩家分群洞察**")
        report_lines.append(f"- 通过 K-Means 聚类，玩家分为 {len(cluster_names_list)} 个典型群体：{', '.join(cluster_names_list)}。")
        report_lines.append(f"- 💡 **运营建议**：针对不同群体定制内容策略——")
        for name in cluster_names_list:
            if "社交" in name:
                report_lines.append(f"  - {name}：重点推送 **联机活动** 和 **组队招募** 内容。")
            elif "硬核" in name:
                report_lines.append(f"  - {name}：重点推送 **深度攻略**、**速通技巧** 和 **高难度挑战** 内容。")
            elif "休闲" in name:
                report_lines.append(f"  - {name}：重点推送 **轻松向内容**、**剧情解析** 和 **入门指南**。")
            else:
                report_lines.append(f"  - {name}：根据其游戏偏好推送个性化内容。")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("📌 **一句话总结**")
    
    if top_reason == "没时间":
        summary = f"Compass 社区的玩家以 **{top_genre}** 类游戏爱好者为主，最大痛点是 **时间不足**。建议打造 **碎片化知识库**，让玩家在有限时间内高效获取游戏信息。"
    elif top_reason == "太难了":
        summary = f"Compass 社区的玩家以 **{top_genre}** 类游戏爱好者为主，最大痛点是 **游戏难度过高**。建议建立 **分级教程体系**，从入门到精通，帮助玩家逐步成长。"
    elif top_reason == "没朋友一起玩":
        summary = f"Compass 社区的玩家以 **{top_genre}** 类游戏爱好者为主，最大痛点是 **缺少玩伴**。建议强化 **社区社交功能**，将 Compass 打造为玩家的 **联机枢纽**。"
    else:
        summary = f"Compass 社区的玩家以 **{top_genre}** 类游戏爱好者为主。建议围绕该品类持续产出内容，同时关注玩家反馈动态调整内容策略。"
    
    report_lines.append(f"> {summary}")

    if total_users < 10:
        report_lines.append("")
        report_lines.append("⚠️ **注意**：当前数据样本较少（< 10 人），以上洞察仅供参考。建议持续招募更多玩家，以获得更可靠的统计结论。")

    for line in report_lines:
        if line.startswith("---"):
            st.markdown("---")
        elif line.startswith("> "):
            st.info(line[2:])
        elif line.startswith("📌"):
            st.markdown(line)
        else:
            st.write(line)

    st.caption(f"📅 报告自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ==========================================
# 5. 教程功能
# ==========================================
def show_publish_strategy():
    st.subheader("✍️ 发布游戏教程/心得")
    st.caption("分享你的经验，帮助其他玩家")

    with st.form("strategy_form"):
        game_name = st.text_input("游戏名称")
        title = st.text_input("教程标题")
        tags = st.multiselect("标签", ["新手向", "进阶", "避坑指南", "速通", "全收集", "剧情解析", "职业攻略"])
        content = st.text_area("教程内容（支持Markdown）", height=300)
        steam_url = st.text_input("Steam 链接（可选）", placeholder="https://store.steampowered.com/app/xxxxx/")
        submitted = st.form_submit_button("📤 发布")

        if submitted and game_name and title and content:
            db = load_json_db(STRATEGY_DB_FILE)
            sid = f"strategy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            db[sid] = {
                "game_name": game_name,
                "title": title,
                "tags": tags,
                "content": content,
                "author": st.session_state.get("username", "匿名"),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "steam_url": steam_url if steam_url else ""
            }
            save_json_db(STRATEGY_DB_FILE, db)
            log_activity(st.session_state.get("username", "匿名"), "发布教程")
            st.success("🎉 教程发布成功！")
            st.balloons()

def show_strategy_list():
    st.subheader("📚 教程库")
    st.caption("每一位玩家的经验，都是新手的指南针")

    db = load_json_db(STRATEGY_DB_FILE)
    if not db:
        st.info("📭 暂无教程，快来发布第一篇吧！")
        return

    search = st.text_input("🔍 搜索游戏", placeholder="输入游戏名称...")

    found = False
    for sid, item in db.items():
        if search and search.lower() not in item.get("game_name", "").lower():
            continue
        found = True
        with st.expander(f"🎯 {item['game_name']} - {item['title']} (by {item.get('author', '匿名')})"):
            st.caption(f"🏷️ 标签: {', '.join(item.get('tags', []))} | 📅 {item.get('time', '')}")

            if item.get("steam_url"):
                st.markdown(f"🔗 **Steam 链接:** [点击访问 {item['game_name']}]({item['steam_url']})")

            st.markdown("---")
            st.markdown(item["content"])

    if search and not found:
        st.info(f"未找到 '{search}' 相关的教程，去发布一篇吧！")

# ==========================================
# 6. 用户画像
# ==========================================
def show_user_profile():
    username = st.session_state.get("username", "")
    if not username:
        st.warning("请先注册")
        return

    db = load_json_db(USER_DATA_FILE)
    if username not in db:
        st.warning("用户数据未找到")
        return

    user_data = db[username]
    st.subheader(f"🧭 {username} 的玩家档案")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("性别", user_data.get("gender", "-"))
    with col2:
        st.metric("年龄段", user_data.get("age", "-"))
    with col3:
        st.metric("游戏龄", f"{user_data.get('gaming_years', '-')} 年")
    with col4:
        st.metric("日均时长", user_data.get("play_time", "-"))

    st.write("**🎯 喜欢的游戏类型**")
    st.write(", ".join(user_data.get("game_types", [])))
    st.write("**⚠️ 弃坑主因**")
    st.write(", ".join(user_data.get("quit_reason", [])))

    st.markdown("---")
    st.subheader("🎯 根据你的游戏偏好，Compass 为你推荐：")
    st.caption("基于你的游戏类型偏好、技术水平、弃坑原因生成的个性化推荐")
    
    recommendations = get_recommendations(user_data)
    
    if recommendations:
        cols = st.columns(3)
        for idx, rec in enumerate(recommendations):
            game = rec["game"]
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"**🎮 {game.get('name', '未知游戏')}**")
                    if game.get('cover_url'):
                        st.image(game['cover_url'], use_container_width=True)
                    st.caption(f"🏷️ {', '.join(game.get('tags', [])[:2])}")
                    if game.get('steam_url'):
                        st.markdown(f"[查看 Steam]({game['steam_url']})")
                    st.markdown("---")
                    st.caption("💡 **推荐理由：**")
                    for reason in rec["reasons"]:
                        st.write(f"• {reason}")
                    
                    if rec.get("tutorial_count", 0) > 0:
                        st.caption(f"📚 社区有 {rec['tutorial_count']} 篇教程")
    else:
        st.info("暂未找到匹配的游戏推荐，试试在搜索页面查找你喜欢的游戏吧！")
    
    if st.button("🔄 刷新推荐"):
        st.rerun()

# ==========================================
# 7. 管理员面板
# ==========================================
def show_admin_panel():
    st.subheader("🔐 管理员面板")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 加载演示数据", use_container_width=True):
            if generate_demo_users():
                st.success("✅ 演示数据加载成功")
                st.rerun()
    with col2:
        if st.button("🗑️ 清除所有数据", use_container_width=True):
            if clear_demo_data():
                st.success("✅ 数据已清除")
                st.rerun()

    user_db = load_json_db(USER_DATA_FILE)
    strategy_db = load_json_db(STRATEGY_DB_FILE)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 注册玩家", len(user_db))
    with col2:
        st.metric("📝 教程数量", len(strategy_db))
    with col3:
        st.metric("📋 活动日志", len(load_json_db(ACTIVITY_LOG_FILE)))
    st.caption("管理员密码: admin123")

# ==========================================
# 8. 主程序
# ==========================================
def main():
    st.set_page_config(page_title="Compass · 游戏社区", page_icon="🧭", layout="wide")

    if "username" not in st.session_state:
        st.session_state.username = None
    if "registered" not in st.session_state:
        st.session_state.registered = False
    if "admin_mode" not in st.session_state:
        st.session_state.admin_mode = False

    with st.sidebar:
        st.title("🧭 Compass")
        st.caption("用数据指引你的游戏之路")
        st.markdown("---")

        with st.expander("🔐 管理员入口"):
            pwd = st.text_input("密码", type="password", placeholder="admin123")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 进入", use_container_width=True):
                    if pwd == "admin123":
                        st.session_state.admin_mode = True
                        generate_demo_users()
                        st.success("✅ 管理员模式已开启")
                        st.rerun()
            with col2:
                if st.button("🚪 退出", use_container_width=True):
                    st.session_state.admin_mode = False
                    st.rerun()
            st.caption("🟢 管理员模式" if st.session_state.admin_mode else "⚪ 普通模式")

        st.markdown("---")

        if not st.session_state.registered:
            username = show_registration_survey()
            if username:
                st.session_state.username = username
                st.session_state.registered = True
                st.rerun()
        else:
            st.success(f"👋 {st.session_state.username}")
            if st.button("🚪 切换账号"):
                st.session_state.registered = False
                st.session_state.username = None
                st.rerun()

            user_db = load_json_db(USER_DATA_FILE)
            st.metric("👥 社区人数", len(user_db))

    if st.session_state.registered:
        if st.session_state.admin_mode:
            tabs = st.tabs([
                "🔍 搜索游戏",
                "📚 教程库",
                "✍️ 发布教程",
                "📊 数据看板",
                "👤 我的档案",
                "🔐 管理"
            ])
            with tabs[0]:
                show_game_search()
            with tabs[1]:
                show_strategy_list()
            with tabs[2]:
                show_publish_strategy()
            with tabs[3]:
                show_deep_data_insights()
            with tabs[4]:
                show_user_profile()
            with tabs[5]:
                show_admin_panel()
        else:
            tabs = st.tabs([
                "🔍 搜索游戏",
                "📚 教程库",
                "✍️ 发布教程",
                "👤 我的档案"
            ])
            with tabs[0]:
                show_game_search()
            with tabs[1]:
                show_strategy_list()
            with tabs[2]:
                show_publish_strategy()
            with tabs[3]:
                show_user_profile()
    else:
        st.info("👈 请先注册加入 Compass")

if __name__ == "__main__":
    main()
