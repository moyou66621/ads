import streamlit as st
import pandas as pd
import requests
import re
import json
import os
import urllib.parse
from datetime import datetime

# =========================================================================
# 0. 核心工程化：本地文件型数据库（确保数据永久保存，重启不丢）
# =========================================================================
USER_DB_FILE = "users_data.json"
COMMENT_DB_FILE = "comments_data.json"
HISTORY_DB_FILE = "history_data.json"

def load_json_db(file_path, default_value):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(default_value, f, ensure_ascii=False, indent=4)
        return default_value
    with open(file_path, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return default_value

def save_json_db(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 初始化底层本地数据库
users_db = load_json_db(USER_DB_FILE, {"admin": {"password": "123456", "name": "核心硬核玩家-老王"}})
comments_db = load_json_db(COMMENT_DB_FILE, {})
history_db = load_json_db(HISTORY_DB_FILE, {})

# 初始化 Session 核心状态机
if "current_user_id" not in st.session_state: st.session_state["current_user_id"] = None
if "auth_page" not in st.session_state: st.session_state["auth_page"] = "login"
if "last_search_result" not in st.session_state: st.session_state["last_search_result"] = None
if "last_search_appid" not in st.session_state: st.session_state["last_search_appid"] = None

# =========================================================================
# 1. 数据科学通道：游戏检索、特征提炼与媒体链接生成
# =========================================================================
def search_steam_appid_by_name(game_name):
    """通过游戏名称模糊检索 Steam 官方商店"""
    search_url = f"https://store.steampowered.com/api/storesearch/?term={game_name}&l=zh-cn&cc=HK"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code == 200 and response.json():
            items = response.json().get("items", [])
            results = []
            for item in items[:5]: # 仅取最相关的前 5 个结果
                results.append({
                    "id": str(item.get("id")),
                    "name": item.get("name")
                })
            return results
    except:
        pass
    return []

def fetch_game_guide_details(app_id):
    """抓取游戏详细介绍、核心特色及横幅资产"""
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=zh-cn"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200 or not response.json(): return None
        data = response.json()
        if str(app_id) not in data or not data[str(app_id)]["success"]: return None
        
        game_data = data[str(app_id)]["data"]
        game_name = game_data.get("name", "未知独立游戏")
        
        # 清洗复杂的 HTML 标签，提炼纯文本简介
        raw_desc = game_data.get("about_the_game", "暂无详细简介")
        clean_desc = re.sub(r'<[^>]+>', '', raw_desc).strip()
        # 截取前 500 字作为精简特色简介
        short_desc = clean_desc if len(clean_desc) <= 500 else clean_desc[:500] + "..."
        
        # 抓取游戏宣传主图
        header_image = game_data.get("header_image", "")
        
        # 抓取标签/分类
        genres = game_data.get("genres", [])
        tags = [g.get("description", "") for g in genres[:8]] or ["新游开荒"]
        
        # 开发商与运营商
        developers = ", ".join(game_data.get("developers", ["未知"]))
        
        return {
            "game_name": game_name,
            "short_desc": short_desc,
            "header_image": header_image,
            "tags": tags,
            "developers": developers
        }
    except:
        return None

# =========================================================================
# 2. 前端工程架构（Steam 游戏全能开荒助手）
# =========================================================================
st.set_page_config(page_title="Steam Game Pioneer Hub", page_icon="🎮", layout="wide")

# 🔒 情况 A：未登录状态 -> 锁定系统
if st.session_state["current_user_id"] is None:
    st.title("🎮 Steam 游戏全能开荒助手 (Game Pioneer Hub)")
    st.caption("香港树仁大学应用数据科学系 · 大数据实验室玩家辅助研发项目")
    st.markdown("---")
    
    _, col_b, _ = st.columns([1, 2, 1])
    with col_b:
        if st.session_state["auth_page"] == "login":
            st.subheader("🔑 玩家/研究员登录后台")
            u_id = st.text_input("账号 ID", placeholder="请输入注册账号")
            u_pwd = st.text_input("登录密码", type="password", placeholder="请输入密码")
            if st.button("进入开荒中心", use_container_width=True):
                if u_id in users_db and users_db[u_id]["password"] == u_pwd:
                    st.session_state["current_user_id"] = u_id
                    st.rerun()
                else: st.error("账号或密码不匹配，请重试。")
            if st.button("新玩家加入？点击一键注册"):
                st.session_state["auth_page"] = "register"; st.rerun()
                
        elif st.session_state["auth_page"] == "register":
            st.subheader("📝 玩家账户注册")
            r_id = st.text_input("设置玩家账号 (英文字母/数字)")
            r_name = st.text_input("游戏圈个性昵称 (展示用)")
            r_pwd = st.text_input("设置密码", type="password")
            if st.button("同步注册信息", use_container_width=True):
                if not r_id or not r_name or not r_pwd: st.error("所有注册字段均不能为空！")
                elif r_id in users_db: st.error("该账号已被注册，请更换玩家 ID。")
                else:
                    users_db[r_id] = {"password": r_pwd, "name": r_name}
                    save_json_db(USER_DB_FILE, users_db)
                    st.success("玩家注册成功！数据已同步，请切换回登录。")
                    st.session_state["auth_page"] = "login"; st.rerun()
            if st.button("返回登录界面"):
                st.session_state["auth_page"] = "login"; st.rerun()

# 🔓 情况 B：登录成功状态
else:
    user_id = st.session_state["current_user_id"]
    user_name = users_db[user_id]["name"]
    
    # 全局顶部状态栏
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.title("🎮 Steam 游戏全能开荒助手 (Pioneer Hub)")
        st.write(f"当前在线玩家：**{user_name}** | 实验室系统节点：`树仁应用数据科学大数据实验室监控中`")
    with col_t2:
        st.write(" ")
        if st.button("⚙️ 安全退出助手", use_container_width=True):
            st.session_state["current_user_id"] = None
            st.session_state["last_search_result"] = None
            st.session_state["last_search_appid"] = None
            st.rerun()
    st.markdown("---")
    
    st.sidebar.header("📁 核心向功能导航")
    app_mode = st.sidebar.radio("请选择核心模块", ["🔍 新游智能开荒检索", "📜 个人探索历史清单", "💬 社区开荒开黑交流区"])
    
    # ---------------------------------------------------------------------
    # 模块 1：新游智能开荒检索（核心功能区）
    # ---------------------------------------------------------------------
    if app_mode == "🔍 新游智能开荒检索":
        st.sidebar.markdown("---")
        st.sidebar.header("📥 游戏大盘检索")
        search_query = st.sidebar.text_input("请输入想了解的游戏名字", value="黑神话")
        
        if st.sidebar.button("🔍 智能检索大盘", use_container_width=True):
            with st.spinner("正在扫描 Steam 官方大盘数据库..."):
                search_results = search_steam_appid_by_name(search_query)
                if search_results:
                    st.session_state["player_search_results"] = search_results
                    st.sidebar.success(f"为您寻获 {len(search_results)} 款关联目标！")
                else:
                    st.sidebar.error("未找到关联游戏，请检查错别字或缩写。")
                    st.session_state["player_search_results"] = None

        # 联动组件：在主面板渲染“游戏确认下拉选择器”
        if "player_search_results" in st.session_state and st.session_state["player_search_results"]:
            st.markdown("### 🎯 请锁定您想要检索的游戏目标")
            options = {f"🎮 {item['name']} (AppID: {item['id']})": item['id'] for item in st.session_state["player_search_results"]}
            selected_label = st.selectbox("请在下方候选大盘列表中选择一项锁定：", list(options.keys()))
            
            if st.button("🚀 锁定并生成全功能开荒红皮书"):
                target_appid = options[selected_label]
                with st.spinner("正在提取该游戏的核心数据资产与特色简介..."):
                    res = fetch_game_guide_details(target_appid)
                    if res:
                        # 记录到探索历史数据库
                        if user_id not in history_db: history_db[user_id] = []
                        history_db[user_id].append({
                            "app_id": target_appid, "game_name": res["game_name"], "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        save_json_db(HISTORY_DB_FILE, history_db)
                        
                        # 锁定至数据守卫缓存
                        st.session_state["last_search_result"] = res
                        st.session_state["last_search_appid"] = target_appid
                        st.session_state["player_search_results"] = None
                        st.rerun()
            st.markdown("---")
        
        # 🌟 数据守卫渲染引擎：渲染游戏特色、简介、以及一键教学视频直达
        if st.session_state["last_search_result"] is not None:
            game_info = st.session_state["last_search_result"]
            current_appid = st.session_state["last_search_appid"]
            
            # 分栏布局展现：左边图片，右边简介与标签
            col_img, col_txt = st.columns([1, 2])
            with col_img:
                if game_info["header_image"]:
                    st.image(game_info["header_image"], use_container_width=True)
                st.markdown(f"**🏢 开发商：** `{game_info['developers']}`")
                st.markdown(f"**🔢 官方 AppID：** `{current_appid}`")
            with col_txt:
                st.subheader(f"🎮 游戏名称：{game_info['game_name']}")
                # 动态生成标签云
                tags_html = "".join([f"<span style='background-color:#007bff;color:white;padding:3px 8px;margin-right:5px;border-radius:3px;font-size:12px;'>{t}</span>" for t in game_info["tags"]])
                st.markdown(f"**🏷️ 核心特色分类：** {tags_html}", unsafe_allow_html=True)
                st.markdown(" ")
                st.markdown(f"**📖 游戏官方简介与背景：** \n{game_info['short_desc']}")
            
            # 🚀 【震撼重头戏】：动态跳转教学视频平台链接生成区
            st.markdown("---")
            st.markdown("### 📺 玩家速成快捷键：一键空降全网保姆级教学视频平台")
            st.write("系统已为您基于当前游戏名称，智能动态编码封装了最佳开荒搜索矩阵。点击下方平台按钮即可跳转学习：")
            
            # 对游戏名进行 URL 安全编码，防止中文字符或特殊符号导致链接断裂
            encoded_game_name = urllib.parse.quote(game_info['game_name'])
            
            # 构建智能检索矩阵链接
            bilibili_url = f"https://search.bilibili.com/all?keyword={encoded_game_name}%20%E6%95%99%E5%AD%A6%E6%94%BB%E7%95%A5"
            youtube_url = f"https://www.youtube.com/results?search_query={encoded_game_name}+guide+walkthrough"
            
            v_col1, v_col2 = st.columns(2)
            with v_col1:
                st.markdown(f"""
                <a href="{bilibili_url}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #fb7299; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; cursor: pointer; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                        📺 哔哩哔哩 (Bilibili) | 调取国内【{game_info['game_name']}】保姆级新手开荒/全收集攻略
                    </div>
                </a>
                """, unsafe_allow_html=True)
            with v_col2:
                st.markdown(f"""
                <a href="{youtube_url}" target="_blank" style="text-decoration: none;">
                    <div style="background-color: #ff0000; color: white; padding: 15px; border-radius: 8px; text-align: center; font-weight: bold; cursor: pointer; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
                        🎬 YouTube Global | 调取全球【{game_info['game_name']}'] 100% 极限速通与机制拆解
                    </div>
                </a>
                """, unsafe_allow_html=True)
            
            # 🌟 玩家评论互动专区
            st.markdown("---")
            st.subheader(f"💬 【{game_info['game_name']}】玩家互助、开黑与踩坑反馈区")
            
            game_comments = comments_db.get(str(current_appid), [])
            if not game_comments:
                st.caption("当前暂无玩家留言，欢迎发布首条逃坑/组队指南！")
            else:
                for c in game_comments:
                    st.markdown(f"**👤 玩家: {c['user']}** (`{c['time']}`):  \n> {c['text']}")
            
            with st.form("comment_form", clear_on_submit=True):
                new_comment = st.text_area("发布你的通关心得、联机暗号或避雷经验：")
                if st.form_submit_button("发布到该游戏开荒板") and new_comment.strip():
                    if str(current_appid) not in comments_db: comments_db[str(current_appid)] = []
                    comments_db[str(current_appid)].append({
                        "user": user_name, "text": new_comment, "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    save_json_db(COMMENT_DB_FILE, comments_db)
                    st.success("心得发布成功，已实时同步！")
                    st.rerun()
        else:
            if "player_search_results" not in st.session_state or not st.session_state["player_search_results"]:
                st.info("💡 开荒助手已就绪。请在左侧侧边栏输入任何你想玩的游戏名称（支持中文/英文，如：黑神话、艾尔登法环、Hades），开启全新玩家红皮书。")

    # ---------------------------------------------------------------------
    # 模块 2：个人探索历史清单
    # ---------------------------------------------------------------------
    elif app_mode == "📜 个人探索历史清单":
        st.subheader("📜 您的专属游戏探索足迹清单")
        user_history = history_db.get(user_id, [])
        if not user_history:
            st.info("您当前还没有检索过任何游戏，快去左侧输入名字开启探索吧！")
        else:
            df = pd.DataFrame(user_history)
            df.columns = ["游戏 AppID", "被搜索游戏名称", "探索解锁时间"]
            st.dataframe(df, use_container_width=True)
            st.metric(label="已解锁探索游戏总数", value=f"{len(user_history)} 款")

    # ---------------------------------------------------------------------
    # 模块 3：社区开荒开黑交流区（全站论坛）
    # ---------------------------------------------------------------------
    elif app_mode == "💬 社区开荒开黑交流区":
        st.subheader("💬 大数据实验室 · 全能玩家开荒综合讨论广场")
        st.write("在这里发布联机暗号、硬件配置探讨或全站动态。")
        st.markdown("---")
        
        global_comments = comments_db.get("global_forum", [])
        if not global_comments:
            st.caption("大广场空空如也，留下你的第一条组队邀请吧！")
        else:
            for c in global_comments:
                st.markdown(f"**👤 玩家: {c['user']}** (`{c['time']}`):  \n{c['text']}")
                st.markdown("---")
                
        with st.form("global_form", clear_on_submit=True):
            g_text = st.text_input("广播一条组队/求助动态：", placeholder="例如：有人来连深岩银河吗？带带萌新...")
            if st.form_submit_button("全站广播推送") and g_text.strip():
                if "global_forum" not in comments_db: comments_db["global_forum"] = []
                comments_db["global_forum"].append({
                    "user": user_name, "text": g_text, "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_json_db(COMMENT_DB_FILE, comments_db)
                st.success("全站动态广播成功！")
                st.rerun()
