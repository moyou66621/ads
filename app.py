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
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 0. 数据存储配置
# ==========================================
USER_DATA_FILE = "user_data.json"
COMMENT_DB_FILE = "comments_db.json"
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
# 0.5 演示数据生成器（仅管理员模式调用）
# ==========================================
def generate_demo_users():
    """生成演示用户数据"""
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
        sample_games = ["艾尔登法环", "赛博朋克2077", "星露谷物语", "空洞骑士", "巫师3", "只狼", "文明6", "我的世界"]
        for i in range(10):
            sid = f"demo_strategy_{i}"
            game = random.choice(sample_games)
            demo_strategies[sid] = {
                "game_name": game,
                "title": f"【新手向】{game} 入门指南 {i+1}",
                "tags": ["新手向", "避坑指南"],
                "content": f"这是关于《{game}》的演示攻略内容。",
                "author": f"Demo_Player_{random.randint(1,30):02d}",
                "time": (datetime.now() - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d %H:%M")
            }
        save_json_db(STRATEGY_DB_FILE, demo_strategies)

        demo_activities = {}
        for i in range(50):
            username = f"Demo_Player_{random.randint(1,30):02d}"
            actions = ["注册", "浏览攻略", "发布攻略", "查看数据看板"]
            demo_activities[f"activity_{i}"] = {
                "username": username,
                "action": random.choice(actions),
                "time": (datetime.now() - timedelta(hours=random.randint(1, 720))).strftime("%Y-%m-%d %H:%M:%S")
            }
        save_json_db(ACTIVITY_LOG_FILE, demo_activities)

        with open(DEMO_DATA_FLAG, "w") as f:
            f.write("loaded")

        return True

    except Exception as e:
        print(f"⚠️ 演示数据生成失败: {e}")
        return False

def clear_demo_data():
    """清除演示数据和标志"""
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
# 1. 用户注册 + 问卷
# ==========================================
def show_registration_survey():
    st.subheader("🧭 欢迎加入 Compass！请完成玩家档案")
    st.caption("用数据指引你的游戏之路")

    with st.form("registration_form"):
        username = st.text_input("玩家昵称*", max_chars=20)

        st.markdown("---")
        st.caption("📊 以下数据将用于 Compass 数据科学分析，仅展示统计结果")

        col1, col2 = st.columns(2)
        with col1:
            gender = st.radio("性别", ["男", "女", "不愿透露"], horizontal=True)
        with col2:
            age = st.selectbox("年龄段", ["18岁以下", "18-24岁", "25-30岁", "31-35岁", "36岁以上"])

        st.markdown("#### 🎯 游戏行为")
        col1, col2 = st.columns(2)
        with col1:
            game_types = st.multiselect(
                "喜欢的游戏类型（可多选）",
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
                "你通常是因为什么弃坑一款游戏？（选1-3个）",
                ["太难了", "没时间", "没朋友一起玩", "剧情无聊", "内容太少", "优化差/卡顿", "其他"]
            )
        with col2:
            purchase_factor = st.multiselect(
                "影响你购买游戏的主要因素（选1-3个）",
                ["画面", "玩法", "价格", "朋友推荐", "媒体评分", "Steam评价", "开发者口碑"]
            )

        st.markdown("#### 📝 主观评分（1-10）")
        col1, col2, col3 = st.columns(3)
        with col1:
            gaming_skill = st.slider("游戏技术水平", 1, 10, 5)
        with col2:
            social_preference = st.slider("更喜欢联机/社交", 1, 10, 5)
        with col3:
            completionist = st.slider("全收集/成就追求度", 1, 10, 5)

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
            return username
    return None

# ==========================================
# 2. 数据科学看板（仅管理员可见）
# ==========================================
def show_deep_data_insights():
    st.subheader("📊 Compass 数据科学看板")
    st.caption("基于真实玩家数据的统计建模、聚类分析、关联挖掘与预测")

    user_db = load_json_db(USER_DATA_FILE)

    if len(user_db) == 0:
        st.info("📭 Compass 暂无玩家数据，等待第一位开拓者...")
        return

    df = pd.DataFrame(user_db).T.reset_index().rename(columns={"index": "用户名"})

    st.success(f"📌 当前基于 {len(user_db)} 位玩家的数据进行分析。")
    st.markdown("---")

    # ===== 分析1：基础统计 =====
    st.subheader("📈 社区基础统计画像")

    col1, col2 = st.columns(2)

    with col1:
        gender_counts = df["gender"].value_counts().reset_index()
        gender_counts.columns = ["性别", "人数"]
        fig1 = px.pie(gender_counts, values="人数", names="性别", color_discrete_sequence=px.colors.qualitative.Set2)
        fig1.update_layout(height=300, title="性别分布")
        st.plotly_chart(fig1, use_container_width=True)

        time_counts = df["play_time"].value_counts().reset_index()
        time_counts.columns = ["时长", "人数"]
        time_order = ["<1小时", "1-3小时", "3-5小时", "5-8小时", "8小时以上"]
        time_counts["时长"] = pd.Categorical(time_counts["时长"], categories=time_order, ordered=True)
        time_counts = time_counts.sort_values("时长")
        fig2 = px.bar(time_counts, x="时长", y="人数", color="时长", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(height=300, title="每日游戏时长分布", showlegend=False)
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
            fig3.update_layout(height=300, title="最受欢迎的游戏类型", showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

        all_reasons = []
        for reasons in df["quit_reason"]:
            if isinstance(reasons, list):
                all_reasons.extend(reasons)
        if all_reasons:
            reason_counts = pd.Series(all_reasons).value_counts().reset_index()
            reason_counts.columns = ["弃坑原因", "人数"]
            fig4 = px.bar(reason_counts, x="人数", y="弃坑原因", orientation="h", color="人数", color_continuous_scale="Oranges")
            fig4.update_layout(height=300, title="弃坑主要原因", showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # ===== 分析2：交叉分析热力图 =====
    st.subheader("🔍 交叉分析：游戏类型 × 弃坑原因")

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
            fig5.update_layout(height=400, title="游戏类型 × 弃坑原因 热力图")
            st.plotly_chart(fig5, use_container_width=True)
            st.caption("💡 颜色越深表示该类型玩家更容易因该原因弃坑。")

    st.markdown("---")

    # ===== 分析3：K-Means 聚类 =====
    st.subheader("🧩 玩家智能分群（K-Means 聚类）")

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

            cluster_df = pd.DataFrame(cluster_features, columns=[
                "游戏时长", "周频率", "游戏龄", "技术水平", "社交偏好", "成就追求", "类型数", "弃坑因素数"
            ])

            scaler = StandardScaler()
            scaled = scaler.fit_transform(cluster_df)
            kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
            df["玩家分群"] = kmeans.fit_predict(scaled)

            cluster_names = {}
            for cluster_id in df["玩家分群"].unique():
                cluster_data = df[df["玩家分群"] == cluster_id]
                avg_social = cluster_data["social_preference"].mean()
                avg_time = cluster_data["play_time"].apply(lambda x: {"<1小时": 0.5, "1-3小时": 2, "3-5小时": 4, "5-8小时": 6.5, "8小时以上": 9}.get(x, 2)).mean()

                if avg_social > 6 and avg_time > 4:
                    name = "🎮 社交硬核玩家"
                elif avg_social > 6:
                    name = "🤝 社交休闲玩家"
                elif avg_time > 4:
                    name = "🏆 独狼硬核玩家"
                else:
                    name = "🌿 休闲探索玩家"
                cluster_names[cluster_id] = name

            df["玩家分群名称"] = df["玩家分群"].map(cluster_names)

            col1, col2 = st.columns(2)
            with col1:
                cluster_counts = df["玩家分群名称"].value_counts().reset_index()
                cluster_counts.columns = ["玩家类型", "人数"]
                fig6 = px.pie(cluster_counts, values="人数", names="玩家类型", color_discrete_sequence=px.colors.qualitative.Set3)
                fig6.update_layout(height=350, title="玩家分群分布")
                st.plotly_chart(fig6, use_container_width=True)

            with col2:
                st.caption("各类玩家特征雷达图")
                radar_data = []
                for cluster_id in sorted(df["玩家分群"].unique()):
                    subset = df[df["玩家分群"] == cluster_id]
                    radar_data.append({
                        "群组": cluster_names[cluster_id],
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
                    fig7.update_layout(height=350, polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
                    st.plotly_chart(fig7, use_container_width=True)

        except Exception as e:
            st.warning(f"聚类分析出错: {e}")

    else:
        st.info(f"需要至少 8 位玩家才能进行聚类分析，当前 {len(user_db)} 位。")

    st.markdown("---")

    # ===== 分析4：关联规则 =====
    st.subheader("🔗 游戏类型关联规则")

    try:
        all_types = df["game_types"].explode().dropna().unique().tolist()
        if len(all_types) >= 3 and len(user_db) >= 5:
            user_type_matrix = pd.DataFrame(0, index=df["用户名"], columns=all_types)
            for _, row in df.iterrows():
                for t in row.get("game_types", []):
                    if t in user_type_matrix.columns:
                        user_type_matrix.loc[row["用户名"], t] = 1

            type_similarity = cosine_similarity(user_type_matrix.T)
            type_sim_df = pd.DataFrame(type_similarity, index=all_types, columns=all_types)

            pairs = []
            for i, t1 in enumerate(all_types):
                for j, t2 in enumerate(all_types):
                    if i < j:
                        pairs.append({"类型A": t1, "类型B": t2, "相似度": type_sim_df.loc[t1, t2]})
            if pairs:
                pairs_df = pd.DataFrame(pairs).sort_values("相似度", ascending=False).head(10)
                st.write("**最常被同时喜欢的游戏类型组合**")
                for _, row in pairs_df.iterrows():
                    st.write(f"- **{row['类型A']}** ↔ **{row['类型B']}**: 相似度 {row['相似度']:.2%}")

                selected_type = st.selectbox("🔮 类型推荐器", all_types)
                if selected_type:
                    recs = type_sim_df[selected_type].sort_values(ascending=False).head(4).index.tolist()
                    recs = [r for r in recs if r != selected_type]
                    if recs:
                        st.success(f"喜欢《{selected_type}》的玩家也喜欢：{'  |  '.join(recs)}")
        else:
            st.info("需要更多玩家数据进行关联分析。")
    except Exception as e:
        st.info(f"关联分析需要更多数据。")

    with st.expander("📋 查看数据汇总表"):
        st.dataframe(df, use_container_width=True)

# ==========================================
# 3. 攻略功能
# ==========================================
def show_publish_strategy():
    st.subheader("✍️ 在 Compass 发布游戏攻略/心得")
    st.caption("帮助新玩家找到方向，你的分享将成为别人的指南针")

    with st.form("strategy_form"):
        game_name = st.text_input("游戏名称")
        title = st.text_input("攻略标题")
        tags = st.multiselect("标签", ["新手向", "进阶", "避坑指南", "速通", "全收集", "剧情解析", "职业攻略", "其他"])
        content = st.text_area("攻略内容（支持Markdown）", height=300)
        submitted = st.form_submit_button("📤 发布到 Compass")

        if submitted and game_name and title and content:
            db = load_json_db(STRATEGY_DB_FILE)
            strategy_id = f"strategy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            db[strategy_id] = {
                "game_name": game_name,
                "title": title,
                "tags": tags,
                "content": content,
                "author": st.session_state.get("username", "匿名玩家"),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            save_json_db(STRATEGY_DB_FILE, db)
            log_activity(st.session_state.get("username", "匿名"), "发布攻略")
            st.success("🎉 攻略发布成功！")
            st.balloons()

def show_strategy_list():
    st.subheader("📚 Compass 攻略库")
    st.caption("每一位玩家的经验，都是新手的指南针")

    db = load_json_db(STRATEGY_DB_FILE)
    if not db:
        st.info("📭 Compass 攻略库暂无内容，快来发布第一篇攻略吧！")
        return

    search_game = st.text_input("🔍 按游戏名筛选", placeholder="输入游戏名称...")
    for sid, item in db.items():
        if search_game and search_game.lower() not in item["game_name"].lower():
            continue
        with st.expander(f"🎯 {item['game_name']} - {item['title']} (by {item.get('author', '匿名')})"):
            st.caption(f"🏷️ 标签: {', '.join(item.get('tags', []))} | 📅 {item.get('time', '')}")
            st.markdown(item["content"])

# ==========================================
# 4. 用户画像
# ==========================================
def show_user_profile():
    username = st.session_state.get("username", "")
    if not username:
        st.warning("请先注册 Compass")
        return

    db = load_json_db(USER_DATA_FILE)
    if username not in db:
        st.warning("用户数据未找到，请重新注册")
        return

    user_data = db[username]
    st.subheader(f"🧭 {username} 的 Compass 玩家档案")
    st.caption("你的数据正在帮助 Compass 更好地理解玩家群体")

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

    st.write("**📊 自我评分**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.progress(user_data.get("gaming_skill", 5) / 10)
        st.caption(f"技术水平: {user_data.get('gaming_skill', 5)}/10")
    with col2:
        st.progress(user_data.get("social_preference", 5) / 10)
        st.caption(f"社交偏好: {user_data.get('social_preference', 5)}/10")
    with col3:
        st.progress(user_data.get("completionist", 5) / 10)
        st.caption(f"成就追求: {user_data.get('completionist', 5)}/10")

# ==========================================
# 5. 管理员面板
# ==========================================
def show_admin_panel():
    st.subheader("🔐 管理员控制面板")
    st.caption("管理 Compass 的数据和演示模式")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 加载演示数据")
        st.write("点击下方按钮将生成 30 位演示玩家和 10 篇演示攻略。")
        if st.button("📥 加载演示数据", use_container_width=True):
            with st.spinner("正在生成演示数据..."):
                if generate_demo_users():
                    st.success("✅ 演示数据加载成功！")
                    st.rerun()
                else:
                    st.error("❌ 演示数据加载失败")

    with col2:
        st.markdown("#### 🗑️ 清除所有数据")
        st.write("⚠️ 此操作将删除所有数据，不可恢复！")
        if st.button("🗑️ 清除所有数据", use_container_width=True, type="secondary"):
            with st.spinner("正在清除数据..."):
                if clear_demo_data():
                    st.success("✅ 所有数据已清除！")
                    st.rerun()
                else:
                    st.error("❌ 清除数据失败")

    st.markdown("---")

    user_db = load_json_db(USER_DATA_FILE)
    strategy_db = load_json_db(STRATEGY_DB_FILE)
    activity_db = load_json_db(ACTIVITY_LOG_FILE)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 注册玩家", len(user_db))
    with col2:
        st.metric("📝 攻略数量", len(strategy_db))
    with col3:
        st.metric("📋 活动日志", len(activity_db))

    if len(user_db) > 0:
        with st.expander("📋 查看所有用户数据"):
            df = pd.DataFrame(user_db).T
            st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.caption("管理员密码: admin123")

# ==========================================
# 6. 主程序
# ==========================================
def main():

    st.set_page_config(
        page_title="Compass · 游戏玩家社区",
        page_icon="🧭",
        layout="wide"
    )

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
            admin_password = st.text_input("输入管理员密码", type="password", placeholder="admin123")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 进入管理员模式", use_container_width=True):
                    if admin_password == "admin123":
                        st.session_state.admin_mode = True
                        generate_demo_users()
                        st.success("✅ 管理员模式已开启")
                        st.rerun()
                    else:
                        st.error("❌ 密码错误")
            with col2:
                if st.button("🚪 退出管理员模式", use_container_width=True):
                    st.session_state.admin_mode = False
                    st.rerun()

            if st.session_state.admin_mode:
                st.success("🟢 当前为管理员模式")
            else:
                st.info("⚪ 当前为普通用户模式")

        st.markdown("---")

        if not st.session_state.registered:
            st.info("欢迎新玩家！请先加入 Compass")
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

            st.markdown("---")
            user_db = load_json_db(USER_DATA_FILE)
            st.metric("👥 Compass 总人数", len(user_db))
            strategy_db = load_json_db(STRATEGY_DB_FILE)
            st.metric("📝 攻略总数", len(strategy_db))

    if st.session_state.registered:
        if st.session_state.admin_mode:
            tabs = st.tabs([
                "📊 Compass 数据看板",
                "📚 攻略库",
                "✍️ 发布攻略",
                "👤 我的档案",
                "🔐 管理员面板"
            ])
            with tabs[0]:
                show_deep_data_insights()
            with tabs[1]:
                show_strategy_list()
            with tabs[2]:
                show_publish_strategy()
            with tabs[3]:
                show_user_profile()
            with tabs[4]:
                show_admin_panel()
        else:
            tabs = st.tabs([
                "📚 攻略库",
                "✍️ 发布攻略",
                "👤 我的档案"
            ])
            with tabs[0]:
                show_strategy_list()
            with tabs[1]:
                show_publish_strategy()
            with tabs[2]:
                show_user_profile()
    else:
        st.info("👈 请先在左侧完成注册，加入 Compass 社区")
        if st.session_state.admin_mode:
            st.markdown("---")
            st.subheader("📊 数据看板预览（管理员视角）")
            user_db = load_json_db(USER_DATA_FILE)
            if len(user_db) > 0:
                st.success(f"当前已有 {len(user_db)} 位玩家加入 Compass")
                df = pd.DataFrame(user_db).T
                st.dataframe(df.head(20), use_container_width=True)
            else:
                st.info("暂无数据，请点击「进入管理员模式」加载演示数据")

if __name__ == "__main__":
    main()
