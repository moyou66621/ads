import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import scipy.stats as stats
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. 数据存储配置
# ==========================================
USER_DATA_FILE = "user_data.json"
COMMENT_DB_FILE = "comments_db.json"
STRATEGY_DB_FILE = "strategies_db.json"
ACTIVITY_LOG_FILE = "activity_log.json"

def load_json_db(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json_db(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_activity(username, action):
    """记录用户行为日志（用于时间序列分析）"""
    db = load_json_db(ACTIVITY_LOG_FILE)
    log_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{username}"
    db[log_id] = {
        "username": username,
        "action": action,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_json_db(ACTIVITY_LOG_FILE, db)

# ==========================================
# 2. 用户注册 + 扩展问卷
# ==========================================
def show_registration_survey():
    st.subheader("🧭 欢迎加入 Compass！请完成玩家档案")
    st.caption("用数据指引你的游戏之路")

    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("玩家昵称*", max_chars=20)
        with col2:
            st.write("")

        st.markdown("---")
        st.caption("📊 以下数据将用于 Compass 数据科学分析，仅展示统计结果")

        # 基础人口统计
        col1, col2 = st.columns(2)
        with col1:
            gender = st.radio("性别", ["男", "女", "不愿透露"], horizontal=True)
        with col2:
            age = st.selectbox("年龄段", ["18岁以下", "18-24岁", "25-30岁", "31-35岁", "36岁以上"])

        # 游戏行为
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

        # 心理/态度
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

        # 主观评分（1-10）
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

            st.success(f"✅ 欢迎来到 Compass，{username}！你的数据已加入社区分析库")
            return username
    return None

# ==========================================
# 3. 深度数据分析看板
# ==========================================
def show_deep_data_insights():
    st.subheader("📊 Compass 数据科学看板")
    st.caption("基于真实玩家数据的统计建模、聚类分析、关联挖掘与预测")

    user_db = load_json_db(USER_DATA_FILE)
    strategy_db = load_json_db(STRATEGY_DB_FILE)
    activity_db = load_json_db(ACTIVITY_LOG_FILE)

    if len(user_db) == 0:
        st.info("📭 Compass 暂无玩家数据，等待第一位开拓者...")
        return

    if len(user_db) < 5:
        st.warning(f"当前只有 {len(user_db)} 位玩家，数据量不足深度分析。建议积累至少 10 位玩家后查看完整分析。")

    df = pd.DataFrame(user_db).T.reset_index().rename(columns={"index": "用户名"})

    # ====================================================================
    # 分析 1：用户分群聚类（K-Means）
    # ====================================================================
    st.markdown("---")
    st.subheader("🧩 分析 1：Compass 玩家智能分群（K-Means 聚类）")
    st.caption("基于游戏行为和心理特征，将玩家自动分为 4 类典型群体")

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
                elif avg_social > 6 and avg_time <= 4:
                    name = "🤝 社交休闲玩家"
                elif avg_social <= 6 and avg_time > 4:
                    name = "🏆 独狼硬核玩家"
                else:
                    name = "🌿 休闲探索玩家"
                cluster_names[cluster_id] = name

            df["玩家分群名称"] = df["玩家分群"].map(cluster_names)

            col1, col2 = st.columns(2)
            with col1:
                cluster_counts = df["玩家分群名称"].value_counts().reset_index()
                cluster_counts.columns = ["玩家类型", "人数"]
                fig1 = px.pie(cluster_counts, values="人数", names="玩家类型", color_discrete_sequence=px.colors.qualitative.Set3)
                fig1.update_layout(height=350)
                st.plotly_chart(fig1, use_container_width=True)

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
                radar_df = pd.DataFrame(radar_data)
                fig2 = go.Figure()
                for _, row in radar_df.iterrows():
                    fig2.add_trace(go.Scatterpolar(
                        r=[row["技术水平"], row["社交偏好"], row["成就追求"], row["游戏龄"]],
                        theta=["技术水平", "社交偏好", "成就追求", "游戏龄"],
                        fill='toself',
                        name=row["群组"]
                    ))
                fig2.update_layout(height=350, polar=dict(radialaxis=dict(visible=True, range=[0, 10])))
                st.plotly_chart(fig2, use_container_width=True)

        except Exception as e:
            st.warning(f"聚类分析需要更多数据样本：{e}")

    else:
        st.info(f"需要至少 8 位玩家才能进行聚类分析，当前 {len(user_db)} 位。")

    # ====================================================================
    # 分析 2：基础统计图表
    # ====================================================================
    st.markdown("---")
    st.subheader("📈 分析 2：Compass 社区基础统计画像")
    st.caption("玩家群体的基本特征分布")

    col1, col2 = st.columns(2)

    with col1:
        gender_counts = df["gender"].value_counts().reset_index()
        gender_counts.columns = ["性别", "人数"]
        fig3 = px.pie(gender_counts, values="人数", names="性别", color_discrete_sequence=px.colors.qualitative.Set2)
        fig3.update_layout(height=300, title="性别分布")
        st.plotly_chart(fig3, use_container_width=True)

        time_counts = df["play_time"].value_counts().reset_index()
        time_counts.columns = ["时长", "人数"]
        time_order = ["<1小时", "1-3小时", "3-5小时", "5-8小时", "8小时以上"]
        time_counts["时长"] = pd.Categorical(time_counts["时长"], categories=time_order, ordered=True)
        time_counts = time_counts.sort_values("时长")
        fig4 = px.bar(time_counts, x="时长", y="人数", color="时长", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig4.update_layout(height=300, title="每日游戏时长分布", showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        all_types = []
        for types in df["game_types"]:
            if isinstance(types, list):
                all_types.extend(types)
        type_counts = pd.Series(all_types).value_counts().reset_index()
        type_counts.columns = ["游戏类型", "人数"]
        fig5 = px.bar(type_counts, x="人数", y="游戏类型", orientation="h", color="人数", color_continuous_scale="Blues")
        fig5.update_layout(height=300, title="最受欢迎的游戏类型", showlegend=False)
        st.plotly_chart(fig5, use_container_width=True)

        all_reasons = []
        for reasons in df["quit_reason"]:
            if isinstance(reasons, list):
                all_reasons.extend(reasons)
        reason_counts = pd.Series(all_reasons).value_counts().reset_index()
        reason_counts.columns = ["弃坑原因", "人数"]
        fig6 = px.bar(reason_counts, x="人数", y="弃坑原因", orientation="h", color="人数", color_continuous_scale="Oranges")
        fig6.update_layout(height=300, title="弃坑主要原因", showlegend=False)
        st.plotly_chart(fig6, use_container_width=True)

    # ====================================================================
    # 分析 3：交叉分析热力图
    # ====================================================================
    st.markdown("---")
    st.subheader("🔍 分析 3：交叉分析 - 游戏类型 × 弃坑原因")
    st.caption("深度洞察：不同类型游戏的玩家主要因何弃坑")

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
            fig7 = px.imshow(
                cross_tab,
                text_auto=True,
                color_continuous_scale="RdBu_r",
                aspect="auto"
            )
            fig7.update_layout(height=400)
            st.plotly_chart(fig7, use_container_width=True)

            st.caption("💡 颜色越深表示该类型玩家更容易因该原因弃坑。Compass 据此针对性优化社区内容。")

    # ====================================================================
    # 分析 4：时间序列 - 社区活跃度趋势
    # ====================================================================
    st.markdown("---")
    st.subheader("📉 分析 4：Compass 社区活跃度趋势")
    st.caption("追踪社区注册和活跃趋势，识别增长阶段")

    if activity_db:
        activity_df = pd.DataFrame(activity_db).T
        activity_df["time"] = pd.to_datetime(activity_df["time"])
        activity_df["date"] = activity_df["time"].dt.date
        daily_activity = activity_df.groupby("date").size().reset_index(name="活跃数")

        if len(daily_activity) > 1:
            daily_activity["MA7"] = daily_activity["活跃数"].rolling(window=min(7, len(daily_activity)), min_periods=1).mean()

            fig8 = go.Figure()
            fig8.add_trace(go.Scatter(x=daily_activity["date"], y=daily_activity["活跃数"], mode="lines+markers", name="日活跃"))
            fig8.add_trace(go.Scatter(x=daily_activity["date"], y=daily_activity["MA7"], mode="lines", name="移动平均", line=dict(dash="dash")))
            fig8.update_layout(height=300, xaxis_title="日期", yaxis_title="活跃用户数")
            st.plotly_chart(fig8, use_container_width=True)

            if len(daily_activity) > 7:
                recent_growth = (daily_activity["MA7"].iloc[-1] - daily_activity["MA7"].iloc[-7]) / daily_activity["MA7"].iloc[-7] * 100 if daily_activity["MA7"].iloc[-7] > 0 else 0
                if recent_growth > 10:
                    st.success(f"📈 Compass 处于快速增长阶段，近7天增长 {recent_growth:.1f}%")
                elif recent_growth < -10:
                    st.warning(f"📉 Compass 活跃度下降，近7天下降 {abs(recent_growth):.1f}%")
                else:
                    st.info(f"📊 Compass 活跃度稳定，近7天变化 {recent_growth:.1f}%")
    else:
        st.info("暂无活跃数据，等待玩家登录...")

    # ====================================================================
    # 分析 5：关联规则发现
    # ====================================================================
    st.markdown("---")
    st.subheader("🔗 分析 5：游戏类型关联规则")
    st.caption("发现玩家偏好模式：喜欢某类游戏的人也倾向喜欢另一类")

    try:
        all_types = df["game_types"].explode().dropna().unique().tolist()
        if len(all_types) >= 3:
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
            pairs_df = pd.DataFrame(pairs).sort_values("相似度", ascending=False).head(10)

            st.write("**最常被同时喜欢的游戏类型组合**")
            for _, row in pairs_df.iterrows():
                st.write(f"- **{row['类型A']}** ↔ **{row['类型B']}**: 相似度 {row['相似度']:.2%}")

            selected_type = st.selectbox("🔮 Compass 类型推荐器：选择一个游戏类型", all_types)
            if selected_type:
                recs = type_sim_df[selected_type].sort_values(ascending=False).head(4).index.tolist()
                recs = [r for r in recs if r != selected_type]
                if recs:
                    st.success(f"喜欢《{selected_type}》的玩家也喜欢：{'  |  '.join(recs)}")
                else:
                    st.info("暂无足够数据推荐。")
    except Exception as e:
        st.info("关联分析需要更多玩家数据。")

    # ====================================================================
    # 页面底部：问卷数据汇总
    # ====================================================================
    st.markdown("---")
    with st.expander("📋 查看 Compass 问卷数据汇总表"):
        st.dataframe(df, use_container_width=True)
        st.caption(f"共 {len(df)} 位玩家，{len(df.columns)} 个数据字段")

# ==========================================
# 4. 攻略发布 + 社区功能
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
            st.success("🎉 攻略发布成功！你的分享将成为其他玩家的指南针！")
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
# 5. 用户画像
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

    with st.sidebar:
        st.title("🧭 Compass")
        st.caption("用数据指引你的游戏之路")
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
        tabs = st.tabs([
            "📊 Compass 数据看板",
            "📚 攻略库",
            "✍️ 发布攻略",
            "👤 我的档案"
        ])

        with tabs[0]:
            show_deep_data_insights()

        with tabs[1]:
            show_strategy_list()

        with tabs[2]:
            show_publish_strategy()

        with tabs[3]:
            show_user_profile()
    else:
        st.info("👈 请先在左侧完成注册，加入 Compass 社区")

if __name__ == "__main__":
    main()
