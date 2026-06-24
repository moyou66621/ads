import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# 1. 核心后端逻辑：改用 Steam 官方 API 接口
# ==========================================
def fetch_steam_game_features_v5(app_id):
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=zh-cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200: return None
        
        data = response.json()
        if not data or str(app_id) not in data or not data[str(app_id)]["success"]:
            return None
            
        game_data = data[str(app_id)]["data"]
        game_name = game_data.get("name", "未知游戏")
        
        # ① 统计顶部截图数量
        screenshots_list = game_data.get("screenshots", [])
        screenshot_count = len(screenshots_list)
        
        # ② 统计顶部宣传视频的数量
        movies_list = game_data.get("movies", [])
        video_count = len(movies_list)
        
        # ③ 提取详细描述
        about_the_game = game_data.get("about_the_game", "")
        clean_text = re.sub(r'<[^>]+>', '', about_the_game).strip()
        desc_length = len(clean_text)
        
        # ④ 提取标签
        genres = game_data.get("genres", [])
        tags = [g.get("description", "") for g in genres[:10]]
        if not tags: tags = ["独立", "冒险"]
            
        return {
            "game_name": game_name, 
            "screenshot_count": screenshot_count, 
            "video_count": video_count,
            "desc_length": desc_length, 
            "tags": tags
        }
    except Exception as e:
        return None

# ==========================================
# 2. 诊断规则引擎逻辑（移除 GIF，重新分配权重得分）
# ==========================================
def diagnose_game(features):
    score = 100
    suggestions = []
    
    # 诊断项 A：顶部宣传视频判定（提升至核心权重）
    if features["video_count"] == 0:
        score -= 50
        suggestions.append({
            "element": "🎬 商店顶部缺失核心宣传视频",
            "status": "当前 0 个视频 (标杆要求: 至少包含 1 个实机 PV 预告片)",
            "action": "极度危险！没有视频预告的游戏页面转化率会暴跌 80% 以上。请立刻制作并上传包含实际核心玩法、打击感或核心机制的实机 PV。",
            "image_url": "https://images.unsplash.com/photo-1407845944202-3010d846b904?q=80&w=600&auto=format&fit=crop",
            "image_caption": "💡 优秀示例：轮播图第一位必须放置实机宣传片，前 5 秒就要切入核心玩法或高燃画面。"
        })

    # 诊断项 B：截图数量判定
    if features["screenshot_count"] < 9:
        score -= int(((9 - features["screenshot_count"]) / 9) * 30)
        suggestions.append({
            "element": "📸 游戏截图数量或排版不足",
            "status": f"当前 {features['screenshot_count']} 张 (标杆均值: 9 张以上)",
            "action": "建议补齐至少 9 张带有真实 UI 的高清截图。玩家需要通过截图了解游戏内的真实 UI 布局、画风和画面品质，切忌全是播片和纯概念 CG。",
            "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=600&auto=format&fit=crop", 
            "image_caption": "💡 优秀示例：展示清晰的 UI、战斗/核心反馈激烈的真实截图，能让玩家快速建立玩法预期。"
        })
        
    # 诊断项 C：长文本篇幅及结构化排版判定
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

# ==========================================
# 3. Streamlit 前端界面渲染
# ==========================================
st.set_page_config(page_title="Steam CRO Engine", page_icon="🚀", layout="wide")
st.title("🚀 Steam 商店页面转化率优化引擎 (CRO Engine)")
st.caption("基于数据科学的独立游戏商店页面可视化诊断工具")
st.markdown("---")

st.sidebar.header("📥 诊断控制台")
app_id_input = st.sidebar.text_input("请输入 Steam 游戏 AppID", value="548430") # 默认深岩银河
submit_btn = st.sidebar.button("📊 开始数据驱动诊断")

if submit_btn and app_id_input:
    with st.spinner("正在调用 Steam 官方数据通道分析中..."):
        features = fetch_steam_game_features_v5(app_id_input)
        if features:
            report = diagnose_game(features)
            
            # 顶部基本面板展示
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("### 🎯 总体转化潜力得分")
                if report["score"] >= 80:
                    st.markdown(f"<h1 style='color: #2ecc71; margin-top:0;'>{report['score']} <span style='font-size: 20px; color: #7f8c8d;'>/ 100</span></h1>", unsafe_allow_html=True)
                    st.success("🎉 页面质量优秀，继续保持！")
                elif report["score"] >= 50:
                    st.markdown(f"<h1 style='color: #f39c12; margin-top:0;'>{report['score']} <span style='font-size: 20px; color: #7f8c8d;'>/ 100</span></h1>", unsafe_allow_html=True)
                    st.warning("🟡 页面有较大优化空间，建议调整。")
                else:
                    st.markdown(f"<h1 style='color: #e74c3c; margin-top:0;'>{report['score']} <span style='font-size: 20px; color: #7f8c8d;'>/ 100</span></h1>", unsafe_allow_html=True)
                    st.error("🚨 页面存在严重转化短板，亟需修改！")
            with col2:
                st.subheader(f"🎮 游戏名称：{features['game_name']}")
                st.write(f"**核心标签快照：** {' | '.join(features['tags'])}")
                st.write(f"**抓取底料快照：** 顶部视频: {features['video_count']} 个 | 顶部截图: {features['screenshot_count']} 张 | 图文描述字数: {features['desc_length']} 字")
            
            st.markdown("---")
            st.subheader("🛠️ 优先级改进列表 (Action Items)")
            
            if not report["suggestions"]:
                st.balloons()
                st.success("完美！该游戏的商店页面已经达到了头部大作的页面转化标准！")
            else:
                for item in report["suggestions"]:
                    with st.expander(item["element"], expanded=True):
                        text_col, img_col = st.columns([3, 2])
                        with text_col:
                            st.markdown(f"**🔴 当前现状：** {item['status']}")
                            st.info(f"**💡 优化方案：** {item['action']}")
                        with img_col:
                            st.image(item["image_url"], caption=item["image_caption"], use_container_width=True)
        else:
            st.error("未能成功获取该 AppID，请检查数字是否正确，或该游戏已被下架/锁区。")
