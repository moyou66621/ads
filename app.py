import streamlit as st
import pandas as pd
import requests
import re
import json
import os
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
users_db = load_json_db(USER_DB_FILE, {"admin": {"password": "123456", "name": "实验室特约专家-老王"}})
comments_db = load_json_db(COMMENT_DB_FILE, {})
history_db = load_json_db(HISTORY_DB_FILE, {})

# 初始化 Session 核心状态机（防止刷新死循环和数据丢失）
if "current_user_id" not in st.session_state: st.session_state["current_user_id"] = None
if "auth_page" not in st.session_state: st.session_state["auth_page"] = "login"
if "last_diag_result" not in st.session_state: st.session_state["last_diag_result"] = None
if "last_diag_appid" not in st.session_state: st.session_state["last_diag_appid"] = None

# =========================================================================
# 1. 后端数据科学通道：Steam 官方 API 异步对接
# =========================================================================
def fetch_steam_game_features_final(app_id):
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=zh-cn"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200 or not response.json(): return None
        data = response.json()
        if str(app_id) not in data or not data[str(app_id)]["success"]: return None
        
        game_data = data[str(app_id)]["data"]
        game_name = game_data.get("name", "未知独立游戏")
        screenshot_count = len(game_data.get("screenshots", []))
        video_count = len(game_data.get("movies", []))
        clean_text = re.sub(r'<[^>]+>', '', game_data.get("about_the_game", "")).strip()
        
        genres = game_data.get("genres", [])
        tags = [g.get("description", "") for g in genres[:10]] or ["独立开发", "策略"]
            
        return {
            "game_name": game_name, "screenshot_count": screenshot_count, 
            "video_count": video_count, "desc_length": len(clean_text), "tags": tags
        }
    except: return None

# =========================================================================
# 2. 诊断算法规则引擎逻辑
# =========================================================================
def diagnose_game(features):
    score = 100
    suggestions = []
    if features["video_count"] == 0:
        score -= 50
        suggestions.append({
            "element": "🎬 商店顶部缺失核心宣传视频",
            "status": "当前 0 个视频 (行业标准: 至少 1 个高清实机 PV)",
            "action": "极度危险！没有视频预告的游戏页面转化率会暴跌 80% 以上。请立刻制作并上传包含实际核心玩法、打击感或核心机制的实机 PV。",
            "image_url": "https://images.unsplash.com/photo-1407845944202-3010d846b904?q=80&w=600&auto=format&fit=crop",
            "image_caption": "💡 优秀示例：轮播图第一位必须放置实机宣传片，前 5 秒就要切入核心玩法或高燃画面。"
        })
    if features["screenshot_count"] < 9:
        score -= int(((9 - features["screenshot_count"]) / 9) * 30)
        suggestions.append({
            "element": "📸 游戏截图数量或排版不足",
            "status": f"当前 {features['screenshot_count']} 张 (标杆均值: 9 张以上)",
            "action": "建议补齐至少 9 张带有真实 UI 的高清截图。玩家需要通过截图了解游戏内的真实 UI 布局、画风和画面品质，切忌全是播片和纯概念 CG。",
            "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=600&auto=format&fit=crop", 
            "image_caption": "💡 优秀示例：展示清晰的 UI、战斗/核心反馈激烈的真实截图，能让玩家快速建立玩法预期。"
        })
    if features["desc_length"] < 600:
        score -= 20
        suggestions.append({
            "element": "📝 详细描述篇幅过短或缺乏排版",
            "status": f"当前 {features['desc_length']} 字 (标杆均值: 850 字左右)",
            "action": "丰富你的游戏详细介绍。建议使用加粗标题、分栏符号、彩色图形小图标等可视化排版技术，明确分块列出游戏核心特色、玩法机制、世界观简述，让玩家快速建立信任感。",
            "image_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=600&auto=format&fit=crop", 
            "image_caption": "💡 优秀示例：多用小标题分块，利用图形化、列表化展现游戏卖点，避免大段枯燥密集的文字堆砌。"
        })
    return {"score": max(score, 0), "suggestions": suggestions}

# =========================================================================
# 3. 前端工程架构（带状态守卫的多页面 SaaS 路由系统）
# =========================================================================
st.set_page_config(page_title="Steam CRO Full-Stack SaaS", page_icon="🚀", layout="wide")

# 🔒 情况 A：未登录状态 -> 锁定系统，强制弹出注册/登录表单
if st.session_state["current_user_id"] is None:
    st.title("🚀 Steam 商店页面转化率优化 SaaS 平台 (CRO Engine)")
    st.caption("香港树仁大学应用数据科学系 · 大数据实验室研发项目")
    st.markdown("---")
    
    _, col_b, _ = st.columns([1, 2, 1])
    with col_b:
        if st.session_state["auth_page"] == "login":
            st.subheader("🔑 开发者登录后台")
            u_id = st.text_input("账号 ID", placeholder="请输入注册账号")
            u_pwd = st.text_input("登录密码", type="password", placeholder="请输入密码")
            if st.button("进入系统", use_container_width=True):
                if u_id in users_db and users_db[u_id]["password"] == u_pwd:
                    st.session_state["current_user_id"] = u_id
                    st.rerun()
                else: st.error("账号或密码不匹配，请重试。")
            if st.button("新晋开发者？去注册账号"):
                st.session_state["auth_page"] = "register"; st.rerun()
                
        elif st.session_state["auth_page"] == "register":
            st.subheader("📝 开发者账户注册")
            r_id = st.text_input("设置登录账号 (英文字母/数字)")
            r_name = st.text_input("团队/制作人昵称 (展示用)")
            r_pwd = st.text_input("设置密码", type="password")
            if st.button("提交注册并同步至实验室数据库", use_container_width=True):
                if not r_id or not r_name or not r_pwd: st.error("所有注册字段均不能为空！")
                elif r_id in users_db: st.error("该账号已被注册，请更换账号 ID。")
                else:
                    users_db[r_id] = {"password": r_pwd, "name": r_name}
                    save_json_db(USER_DB_FILE, users_db) # 持久化存盘
                    st.success("注册成功！数据已写入本地数据库，请切换回登录。")
                    st.session_state["auth_page"] = "login"; st.rerun()
            if st.button("返回登录界面"):
                st.session_state["auth_page"] = "login"; st.rerun()

# 🔓 情况 B：登录成功状态 -> 解锁进入全功能分布式后台
else:
    user_id = st.session_state["current_user_id"]
    user_name = users_db[user_id]["name"]
    
    # 全局顶部状态栏
    col_t1, col_t2 = st.columns([4, 1])
    with col_t1:
        st.title("🚀 Steam 商店页面转化率优化 SaaS 平台")
        st.write(f"当前在线研究员：**{user_name}** (`ID: {user_id}`) | 节点状态：`树仁大学大数据实验室公网授权节点`")
    with col_t2:
        st.write(" ")
        if st.button("⚙️ 安全退出系统", use_container_width=True):
            st.session_state["current_user_id"] = None
            st.session_state["last_diag_result"] = None
            st.session_state["last_diag_appid"] = None
            st.rerun()
    st.markdown("---")
    
    # 侧边栏多维导航路由
    st.sidebar.header("📁 功能导航后台")
    app_mode = st.sidebar.radio("请选择核心模块", ["📊 商店页面自动化诊断", "📜 个人历史记录看板", "💬 游戏发行公共交流区"])
    
    # ---------------------------------------------------------------------
    # 模块 1：自动化诊断与评论区联动（带数据守卫）
    # ---------------------------------------------------------------------
    if app_mode == "📊 商店页面自动化诊断":
        st.sidebar.markdown("---")
        st.sidebar.header("📥 诊断输入")
        input_appid = st.sidebar.text_input("请输入 Steam 游戏 AppID", value="548430")
        
        if st.sidebar.button("📊 开始全方位诊断", use_container_width=True):
            with st.spinner("正在安全调取官方API数据资产通道..."):
                res = fetch_steam_game_features_final(input_appid)
                if res:
                    report = diagnose_game(res)
                    # 1. 拦截并写入持久化历史数据库
                    if user_id not in history_db: history_db[user_id] = []
                    history_db[user_id].append({
                        "app_id": input_appid, "game_name": res["game_name"],
                        "score": report["score"], "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    save_json_db(HISTORY_DB_FILE, history_db)
                    
                    # 2. 【核心复杂化改造】写入状态守卫，防止刷新被冲掉
                    st.session_state["last_diag_result"] = report
                    st.session_state["last_diag_appid"] = input_appid
                    st.session_state["last_game_features"] = res
                else:
                    st.error("无法调取此 AppID 的数据，请检查该游戏是否存在或已被 Steam 锁区。")
        
        # 🌟 状态守卫渲染引擎：只要缓存里有数据，就强行保持显示，不受页面刷新和表单提交干扰
        if st.session_state["last_diag_result"] is not None:
            saved_report = st.session_state["last_diag_result"]
            saved_appid = st.session_state["last_diag_appid"]
            saved_features = st.session_state["last_game_features"]
            
            # 渲染诊断抬头与得分
            c1, c2 = st.columns([1, 2])
            with c1:
                st.markdown("### 🎯 转化潜力综合评分")
                scr = saved_report["score"]
                if scr >= 80: st.success(f"<h1>{scr}分</h1> 质量优秀！", unsafe_allow_html=True)
                elif scr >= 50: st.warning(f"<h1>{scr}分</h1> 亟待优化！", unsafe_allow_html=True)
                else: st.error(f"<h1>{scr}分</h1> 转化潜力极低！", unsafe_allow_html=True)
            with c2:
                st.subheader(f"🎮 游戏：{saved_features['game_name']} (AppID: {saved_appid})")
                st.write(f"**分类标签：** {' | '.join(saved_features['tags'])}")
                st.write(f"**数据快照：** 预告片: {saved_features['video_count']}个 | 高清截图: {saved_features['screenshot_count']}张 | 详情字数: {saved_features['desc_length']}字")
            
            # 渲染改进药方
            st.markdown("### 🛠️ 转化率像素级改进药方")
            if not saved_report["suggestions"]:
                st.balloons()
                st.success("完美！该游戏页面各要素已达到大数据标杆发行标准。")
            else:
                for item in saved_report["suggestions"]:
                    with st.expander(item["element"], expanded=True):
                        tx_col, im_col = st.columns([3, 2])
                        with tx_col:
                            st.markdown(f"**🔴 触发痛点：** {item['status']}")
                            st.info(f"**💡 专家级解决方案：** {item['action']}")
                        with im_col: 
                            st.image(item["image_url"], caption=item["image_caption"], use_container_width=True)
            
            # 🌟 联动功能：本 AppID 游戏专属公共评论区
            st.markdown("---")
            st.subheader(f"💬 关于【{saved_features['game_name']}】的发行运营专项讨论区")
            
            # 读取当前游戏的评论流
            game_comments = comments_db.get(str(saved_appid), [])
            if not game_comments:
                st.caption("当前暂无针对该游戏的运营讨论，欢迎发布首条专家建议！")
            else:
                for c in game_comments:
                    st.markdown(f"**👤 研究员: {c['user']}** (`{c['time']}`):  \n> {c['text']}")
            
            # 提交评论表单（因为有上面的状态守卫，点击提交不会导致诊断结果消失）
            with st.form("comment_form", clear_on_submit=True):
                new_comment = st.text_area("添加你的商业调优建议或避雷分析：", placeholder="例如：此游戏建议将宣传视频的战斗高潮剪辑到前3秒...")
                if st.form_submit_button("发布到该游戏讨论板") and new_comment.strip():
                    if str(saved_appid) not in comments_db: comments_db[str(saved_appid)] = []
                    comments_db[str(saved_appid)].append({
                        "user": user_name, "text": new_comment, "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    save_json_db(COMMENT_DB_FILE, comments_db)
                    st.success("评论已成功同步至该游戏主板！")
                    st.rerun()
        else:
            st.info("💡 系统就绪。请在左侧侧边栏输入任意 Steam 游戏 AppID（例如：黑神话悟空、Cyberpunk 2077），并点击开始全方位诊断。")

    # ---------------------------------------------------------------------
    # 模块 2：个人历史记录看板
    # ---------------------------------------------------------------------
    elif app_mode == "📜 个人历史记录看板":
        st.subheader("📜 您的专属诊断历史病历本")
        st.write("本面板自动从本地持久化数据库中检索您过去执行过的所有资产体检记录。")
        
        user_history = history_db.get(user_id, [])
        if not user_history:
            st.info("您当前账号还没有诊断过任何游戏，快去执行第一次自动化诊断吧！")
        else:
            # 转化为 DataFrame 展示
            df = pd.DataFrame(user_history)
            df.columns = ["游戏 AppID", "游戏名称", "诊断得分", "诊断执行时间"]
            
            st.dataframe(df, use_container_width=True)
            
            # 增加趣味性数据科学指标
            st.markdown("### 📊 我的数据追踪审计")
            st.metric(label="总诊断游戏批次", value=f"{len(user_history)} 次")

    # ---------------------------------------------------------------------
    # 模块 3：游戏发行公共交流区（大广场）
    # ---------------------------------------------------------------------
    elif app_mode == "💬 游戏发行公共交流区":
        st.subheader("💬 大数据实验室 · 独立游戏发行综合全站论坛")
        st.write("这里是全站公共大广场。所有注册的开发者和实习研究员都可以在这里发布全站广播动态。")
        st.markdown("---")
        
        # 渲染全站大广场留言
        global_comments = comments_db.get("global_forum", [])
        if not global_comments:
            st.caption("大广场空空如也，发布第一条全站广播吧！")
        else:
            for c in global_comments:
                st.markdown(f"**👤 {c['user']}** (`{c['time']}`):  \n{c['text']}")
                st.markdown("---")
                
        with st.form("global_form", clear_on_submit=True):
            g_text = st.text_input("广播一条全新行业动态/心得：", placeholder="分享一下你今天发现的Steam流量机制...")
            if st.form_submit_button("全站广播推送") and g_text.strip():
                if "global_forum" not in comments_db: comments_db["global_forum"] = []
                comments_db["global_forum"].append({
                    "user": user_name, "text": g_text, "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_json_db(COMMENT_DB_FILE, comments_db)
                st.success("全站广播发布成功！")
                st.rerun()
