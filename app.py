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
    st.subheader("🎮 欢迎加入游戏社区！请完成玩家档案")

    with st.form("registration_form"):
        col1, col2 = st.columns(2)
        with col1:
            username = st.text_input("玩家昵称*", max_chars=20)
        with col2:
            st.write("")

        st.markdown("---")
        st.caption("📊 以下数据将用于社区数据科学分析，仅展示统计结果")

        # 基础人口统计
        col1, col2, col3 = st.columns(3)
        with col1:
            gender = st.radio("性别", ["男", "女", "不愿透露"], horizontal=True)
        with col2:
            age = st.selectbox("年龄段", ["18岁以下", "18-24岁", "25-30岁", "31-35岁", "36岁以上"])
        with col3:
            region = st.selectbox("所在地区", ["华北", "华东", "华南", "西南", "西北", "东北", "海外"])

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

        submitted = st.form_submit_button("🚀 建立档案")

        if submitted:
            if not username.strip():
                st.error("请输入昵称！")
                return None

            user_data = {
                "username": username.strip(),
                "gender": gender,
                "age": age,
                "region": region,
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

            st.success(f"✅ 欢迎 {username}！你的数据已加入社区分析库")
            return username
    return None

# ==========================================
# 3. 深度数据分析看板
# ==========================================
def show_deep_data_insights():
    st.subheader("📊 社区数据科学看板")
    st.caption("基于真实玩家数据的统计建模、聚类分析、关联挖掘与预测")

    user_db = load_json_db(USER_DATA_FILE)
    strategy_db = load_json_db(STRATEGY_DB_FILE)
    activity_db = load_json_db(ACTIVITY_LOG_FILE)

    if len(user_db) < 5:
        st.warning(f"当前只有 {len(user_db)} 位玩家，数据量不足深度分析。建议积累至少 10 位玩家后查看完整分析。")
        # 即使数据少也展示部分内容
        if len(user_db) == 0:
            st.info("📭 暂无玩家数据，等待第一位注册玩家...")
            return

    df = pd.DataFrame(user_db).T.reset_index().rename(columns={"index": "用户名"})

    # ====================================================================
    # 分析 1：用户分群聚类（K-Means）
    # ====================================================================
    st.markdown("---")
    st.subheader("🧩 分析 1：玩家智能分群（K-Means 聚类）")
    st.caption("基于游戏行为和心理特征，将玩家自动分为 4 类典型群体")

    try:
        # 特征工程
        cluster_features = []
        for _, row in df.iterrows():
            # 将分类变量转换为数值
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

        # 标准化 + KMeans
        scaler = StandardScaler()
        scaled = scaler.fit_transform(cluster_df)
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        df["玩家分群"] = kmeans.fit_predict(scaled)

        # 分群命名
        cluster_names = {}
        for cluster_id in df["玩家分群"].unique():
            cluster_data = df[df["玩家分群"] == cluster_id]
            avg_social = cluster_data["social_preference"].mean()
            avg_skill = cluster_data["gaming_skill"].mean()
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
            # 分群分布
            cluster_counts = df["玩家分群名称"].value_counts().reset_index()
            cluster_counts.columns = ["玩家类型", "人数"]
            fig1 = px.pie(cluster_counts, values="人数", names="玩家类型", color_discrete_sequence=px.colors.qualitative.Set3)
            fig1.update_layout(height=350)
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # 分群特征雷达图
            st.caption("各类玩家特征雷达图")
            # 计算各群平均特征
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

        # 分群详细描述
        with st.expander("📖 点击查看各玩家类型详细画像"):
            for cluster_id, name in cluster_names.items():
                subset = df[df["玩家分群"] == cluster_id]
                st.markdown(f"**{name}** ({len(subset)} 人)")
                st.write(f"- 平均技术水平: {subset['gaming_skill'].mean():.1f}/10")
                st.write(f"- 平均社交偏好: {subset['social_preference'].mean():.1f}/10")
                st.write(f"- 平均成就追求: {subset['completionist'].mean():.1f}/10")
                st.write(f"- 最常玩的类型: {', '.join(subset['game_types'].explode().value_counts().head(3).index.tolist())}")
                st.write("---")

    except Exception as e:
        st.warning(f"聚类分析需要更多数据样本，当前数据量不足。继续注册更多玩家后自动生效。")

    # ====================================================================
    # 分析 2：相关性分析（Cramér's V + 卡方检验）
    # ====================================================================
    st.markdown("---")
    st.subheader("📈 分析 2：玩家特征与弃坑原因的相关性（Cramér's V）")
    st.caption("检验哪些因素与玩家弃坑显著相关，为社区内容优化提供数据支撑")

    if len(df) >= 10:
        try:
            # 预处理分类变量
            categorical_cols = ["gender", "age", "region", "play_time", "weekly_frequency"]

            # 提取主弃坑原因（取第一个）
            df["main_quit"] = df["quit_reason"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "其他")

            # Cramér's V 计算
            def cramers_v(confusion_matrix):
                chi2 = stats.chi2_contingency(confusion_matrix)[0]
                n = confusion_matrix.sum()
                phi2 = chi2 / n
                r, k = confusion_matrix.shape
                phi2corr = max(0, phi2 - ((k-1)*(r-1))/(n-1))
                rcorr = r - ((r-1)**2)/(n-1)
                kcorr = k - ((k-1)**2)/(n-1)
                return np.sqrt(phi2corr / min((kcorr-1), (rcorr-1)))

            corr_results = []
            for col in categorical_cols:
                if col in df.columns:
                    crosstab = pd.crosstab(df[col], df["main_quit"])
                    if crosstab.shape[1] > 1 and crosstab.shape[0] > 1:
                        try:
                            v = cramers_v(crosstab.values)
                            corr_results.append({"特征": col, "Cramér's V": round(v, 3)})
                        except:
                            pass

            if corr_results:
                corr_df = pd.DataFrame(corr_results).sort_values("Cramér's V", ascending=False)
                fig3 = px.bar(corr_df, x="Cramér's V", y="特征", orientation="h", color="Cramér's V", color_continuous_scale="Reds")
                fig3.update_layout(height=300)
                st.plotly_chart(fig3, use_container_width=True)
                st.caption("💡 V 值越接近 1，表示该特征与弃坑原因关联越强。V > 0.3 为中等相关，V > 0.5 为强相关。")
            else:
                st.info("数据量不足以计算相关性，继续积累数据。")

        except Exception as e:
            st.info("相关性分析需要更多数据样本。")
    else:
        st.info(f"相关性分析需要至少 10 位玩家数据，当前 {len(df)} 位。继续招募玩家吧！")

    # ====================================================================
    # 分析 3：假设检验（t检验）- 不同性别的游戏时长差异
    # ====================================================================
    st.markdown("---")
    st.subheader("🔬 分析 3：统计假设检验 - 性别对游戏时长的影响（t检验）")
    st.caption("检验男性和女性的平均游戏时长是否存在显著差异")

    if len(df) >= 15:
        try:
            time_map = {"<1小时": 0.5, "1-3小时": 2, "3-5小时": 4, "5-8小时": 6.5, "8小时以上": 9}
            df["play_time_numeric"] = df["play_time"].map(time_map)

            male_times = df[df["gender"] == "男"]["play_time_numeric"].dropna()
            female_times = df[df["gender"] == "女"]["play_time_numeric"].dropna()

            if len(male_times) > 3 and len(female_times) > 3:
                t_stat, p_value = stats.ttest_ind(male_times, female_times)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("男性平均游戏时长", f"{male_times.mean():.1f} 小时/天")
                    st.metric("女性平均游戏时长", f"{female_times.mean():.1f} 小时/天")
                with col2:
                    st.metric("t统计量", f"{t_stat:.3f}")
                    st.metric("p值", f"{p_value:.4f}")
                    if p_value < 0.05:
                        st.success("✅ p < 0.05，差异显著！男性和女性的游戏时长有统计学显著差异。")
                    else:
                        st.info("ℹ️ p ≥ 0.05，差异不显著。男性和女性的游戏时长没有统计学显著差异。")
            else:
                st.info("男/女性玩家样本量不足，需要各至少 3 人。")
        except Exception as e:
            st.info("假设检验需要更多样本。")
    else:
        st.info(f"假设检验需要至少 15 位玩家数据，当前 {len(df)} 位。")

    # ====================================================================
    # 分析 4：时间序列 - 社区活跃度趋势
    # ====================================================================
    st.markdown("---")
    st.subheader("📉 分析 4：社区生命周期分析（时间序列）")
    st.caption("追踪社区注册和活跃趋势，识别增长阶段")

    if activity_db:
        activity_df = pd.DataFrame(activity_db).T
        activity_df["time"] = pd.to_datetime(activity_df["time"])
        activity_df["date"] = activity_df["time"].dt.date
        daily_activity = activity_df.groupby("date").size().reset_index(name="活跃数")

        # 7日移动平均
        daily_activity["MA7"] = daily_activity["活跃数"].rolling(window=7, min_periods=1).mean()

        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(x=daily_activity["date"], y=daily_activity["活跃数"], mode="lines+markers", name="日活跃"))
        fig4.add_trace(go.Scatter(x=daily_activity["date"], y=daily_activity["MA7"], mode="lines", name="7日移动平均", line=dict(dash="dash")))
        fig4.update_layout(height=300, xaxis_title="日期", yaxis_title="活跃用户数")
        st.plotly_chart(fig4, use_container_width=True)

        # 增长阶段识别
        if len(daily_activity) > 7:
            recent_growth = (daily_activity["MA7"].iloc[-1] - daily_activity["MA7"].iloc[-7]) / daily_activity["MA7"].iloc[-7] * 100
            if recent_growth > 10:
                st.success(f"📈 社区处于快速增长阶段，近7天增长 {recent_growth:.1f}%")
            elif recent_growth < -10:
                st.warning(f"📉 社区活跃度下降，近7天下降 {abs(recent_growth):.1f}%，建议进行社区活动拉新")
            else:
                st.info(f"📊 社区活跃度稳定，近7天变化 {recent_growth:.1f}%")
    else:
        st.info("暂无活跃数据，等待玩家登录...")

    # ====================================================================
    # 分析 5：关联规则发现 - "喜欢A类型的人也喜欢B类型"
    # ====================================================================
    st.markdown("---")
    st.subheader("🔗 分析 5：游戏类型关联规则（协同过滤）")
    st.caption("发现玩家偏好模式：喜欢某类游戏的人也倾向喜欢另一类")

    try:
        all_types = df["game_types"].explode().dropna().unique().tolist()
        if len(all_types) >= 3:
            # 构建用户-类型矩阵
            user_type_matrix = pd.DataFrame(0, index=df["用户名"], columns=all_types)
            for _, row in df.iterrows():
                for t in row.get("game_types", []):
                    if t in user_type_matrix.columns:
                        user_type_matrix.loc[row["用户名"], t] = 1

            # 计算类型间的余弦相似度
            type_similarity = cosine_similarity(user_type_matrix.T)
            type_sim_df = pd.DataFrame(type_similarity, index=all_types, columns=all_types)

            # 展示 Top 5 关联对
            pairs = []
            for i, t1 in enumerate(all_types):
                for j, t2 in enumerate(all_types):
                    if i < j:
                        pairs.append({"类型A": t1, "类型B": t2, "相似度": type_sim_df.loc[t1, t2]})
            pairs_df = pd.DataFrame(pairs).sort_values("相似度", ascending=False).head(10)

            st.write("**最常被同时喜欢的游戏类型组合**")
            for _, row in pairs_df.iterrows():
                st.write(f"- **{row['类型A']}** ↔ **{row['类型B']}**: 相似度 {row['相似度']:.2%}")

            # 推荐引擎：输入一个类型，输出最相关的3个类型
            st.caption("🔮 **类型推荐器**：选择你喜欢的类型，系统推荐你可能也喜欢的其他类型")
            selected_type = st.selectbox("选择一个游戏类型", all_types)
            if selected_type:
                recs = type_sim_df[selected_type].sort_values(ascending=False).head(4).index.tolist()
                recs = [r for r in recs if r != selected_type]
                st.success(f"喜欢《{selected_type}》的玩家也喜欢：{'  |  '.join(recs)}")
        else:
            st.info("游戏类型数据不足以构建关联规则。")

    except Exception as e:
        st.info("关联分析需要更多玩家数据。")

    # ====================================================================
    # 分析 6：流失风险预测模型（逻辑回归）
    # ====================================================================
    st.markdown("---")
    st.subheader("⚠️ 分析 6：玩家流失风险预测模型（逻辑回归）")
    st.caption("基于玩家画像预测其流失概率，帮助社区提前干预")

    if len(df) >= 20:
        try:
            # 构造特征和标签
            time_map = {"<1小时": 0, "1-3小时": 1, "3-5小时": 2, "5-8小时": 3, "8小时以上": 4}
            df["play_time_encoded"] = df["play_time"].map(time_map)
            df["quit_count"] = df["quit_reason"].apply(lambda x: len(x) if isinstance(x, list) else 0)

            # 假设：弃坑因素>=3的玩家为高风险流失群体
            df["churn_risk"] = (df["quit_count"] >= 3).astype(int)

            features = ["gaming_years", "gaming_skill", "social_preference", "completionist", "play_time_encoded"]
            X = df[features].fillna(df[features].mean())
            y = df["churn_risk"]

            if y.sum() >= 3 and (1 - y).sum() >= 3:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
                model = LogisticRegression(max_iter=1000)
                model.fit(X_train, y_train)

                # 显示特征重要性
                importance_df = pd.DataFrame({
                    "特征": features,
                    "系数": model.coef_[0],
                    "影响方向": ["正面（增加流失风险）" if c > 0 else "负面（降低流失风险）" for c in model.coef_[0]]
                })
                importance_df = importance_df.sort_values("系数", ascending=False)

                fig6 = px.bar(importance_df, x="系数", y="特征", orientation="h", color="影响方向", color_discrete_map={"正面（增加流失风险）": "red", "负面（降低流失风险）": "green"})
                fig6.update_layout(height=250)
                st.plotly_chart(fig6, use_container_width=True)

                st.caption("💡 系数为正的特征会增加流失风险，系数为负的特征会降低流失风险。")
            else:
                st.info("流失风险样本不均衡，需要更多数据。")
        except Exception as e:
            st.info("流失预测模型需要更多数据。")
    else:
        st.info(f"流失预测模型需要至少 20 位玩家数据，当前 {len(df)} 位。")

    # ====================================================================
    # 页面底部：问卷数据汇总统计
    # ====================================================================
    st.markdown("---")
    with st.expander("📋 查看问卷数据汇总表"):
        st.dataframe(df, use_container_width=True)
        st.caption(f"共 {len(df)} 位玩家，{len(df.columns)} 个数据字段")

# ==========================================
# 4. 攻略发布 + 社区功能
# ==========================================
def show_publish_strategy():
    st.subheader("✍️ 发布游戏攻略/心得")

    with st.form("strategy_form"):
        game_name = st.text_input("游戏名称")
        title = st.text_input("攻略标题")
        tags = st.multiselect("标签", ["新手向", "进阶", "避坑指南", "速通", "全收集", "剧情解析", "职业攻略", "其他"])
        content = st.text_area("攻略内容（支持Markdown）", height=300)
        submitted = st.form_submit_button("📤 发布")

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
    st.subheader("📚 社区攻略库")
    db = load_json_db(STRATEGY_DB_FILE)
    if not db:
        st.info("暂无攻略，快来发布第一篇吧！")
        return

    search_game = st.text_input("🔍 按游戏名筛选", placeholder="输入游戏名称...")
    for sid, item in db.items():
        if search_game and search_game.lower() not in item["game_name"].lower():
            continue
        with st.expander(f"🎯 {item['game_name']} - {item['title']} (by {item.get('author', '匿名')})"):
            st.caption(f"🏷️ 标签: {', '.join(item.get('tags', []))} | 📅 {item.get('time', '')}")
            st.markdown(item["content"])
            if st.button(f"👍 有用 ({sid})"):
                st.toast("感谢反馈！")

# ==========================================
# 5. 用户画像
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
    st.subheader(f"👤 {username} 的玩家档案")

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
    st.set_page_config(page_title="🎮 游戏玩家社区", page_icon="🎮", layout="wide")

    if "username" not in st.session_state:
        st.session_state.username = None
    if "registered" not in st.session_state:
        st.session_state.registered = False

    with st.sidebar:
        st.title("🎮 游戏玩家社区")

        if not st.session_state.registered:
            st.info("欢迎新玩家！请先完成注册")
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
            st.metric("👥 社区总人数", len(user_db))
            strategy_db = load_json_db(STRATEGY_DB_FILE)
            st.metric("📝 攻略总数", len(strategy_db))

    if st.session_state.registered:
        tabs = st.tabs([
            "📊 数据科学看板",
            "📚 攻略库",
            "✍️ 发布攻略",
            "👤 我的画像"
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
        st.info("👈 请先在左侧完成注册问卷，解锁社区全部功能")

if __name__ == "__main__":
    main()
