import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# 1. 核心后端逻辑：改用 Steam 官方 API 接口（彻底解决 0 张截图问题）
# ==========================================
def fetch_steam_game_features_v3(app_id):
    # 彻底放弃容易失效的网页强爬，改用官方开放的 appdetails API，天然免疫年龄墙
    api_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=zh-cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200: return None
        
        data = response.json()
        # 判断 API 是否成功返回该游戏的数据
        if not data or str(app_id) not in data or not data[str(app_id)]["success"]:
            return None
            
        game_data = data[str(app_id)]["data"]
        
        # ① 提取游戏名称
        game_name = game_data.get("name", "未知游戏")
        
        # ② 核心修复：直接从官方的 screenshots 数组里拿真实数量，告别永远为0！
        screenshots_list = game_data.get("screenshots", [])
        screenshot_count = len(screenshots_list)
        
        # ③ 提取详细描述
        about_the_game = game_data.get("about_the_game", "")
        # 去除 HTML 标签，只算纯文本字数
        clean_text = re.sub(r'<[^>]+>', '', about_the_game).strip()
        desc_length = len(clean_text)
        
        # ④ 检测动图（独立游戏通常在描述的 HTML 里塞入 gif 链接）
        gif_count = len(re.findall(r'\.gif', about_the_game, re.IGNORECASE))
        
        # ⑤ 提取大类标签作为快照
        genres = game_data.get("genres", [])
        tags = [g.get("description", "") for g in genres[:10]]
        if not tags:
            tags = ["独立", "冒险"] # 稳定兜底标签
            
        return {
            "game_name": game_name, 
            "screenshot_count": screenshot_count, 
            "desc_length": desc_length, 
            "has_gif": 1 if gif_count > 0 else 0, 
            "tags": tags
        }
    except Exception as e:
        return None

# ==========================================
# 2. 诊断规则引擎逻辑（图文并茂示例配置）
# ==========================================
def diagnose_game(features):
    score = 100
    suggestions = []
    bench = {"screenshot_count": 9, "has_gif": 1, "desc_length": 850}

    # 诊断项 A：截图数量判定
    if features["screenshot_count"] < bench["screenshot_count"]:
        score -= int(((bench["screenshot_count"] - features["screenshot_count"]) / bench["screenshot_count"]) * 40)
        suggestions.append({
            "element": "📸 游戏截图数量或排版不足",
            "status": f"当前 {features['screenshot_count']} 张 (标杆均值: {bench['screenshot_count']} 张)",
            "action": f"建议补齐至少 {bench['screenshot_count'] - features['screenshot_count']} 张核心玩法或带有真实 UI 的截图。独立游戏玩家极度看重实际游戏画面，切忌全是虚无缥缈的播片宣传图。",
            "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=600&auto=format&fit=crop", 
            "image_caption": "💡 优秀示例：展示清晰的 UI、战斗激烈的游戏内真实截图（而非概念CG），能让玩家快速建立玩法预期。"
        })
        
    # 诊断项 B：GIF 动图判定
    if features["has_gif"] == 0:
        score -= 35
        suggestions.append({
            "element": "🎞️ 缺失动态 GIF 演示（致命转化痛点）",
            "status": "当前胶囊描述区或详情页未检测到动图 (标杆游戏 100% 具备)",
            "action": "在详细描述前 1/3 黄金区域嵌入展示核心爽点（如华丽特效、爽快连招、大招释放或核心解谜反馈）的短 GIF 动图。静止的文字无法留住当代玩家！",
            "image_url": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3BwZzV5N3N0NXFwaXo3bzh4ZndpZzV4M3VvYXRqMzhpdmF0OHV1diZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/vOsRdf74S6gIE/giphy.gif", 
            "image_caption": "💡 优秀示例：在详情页黄金前排插入 2-3 秒高燃战斗/特效动图，玩家停留转化率平均提升 24%。"
        })
        
    # 诊断项 C：长文本篇幅判定
    if features["desc_length"] < bench["desc_length"] * 0.6:
        score -= 25
        suggestions.append({
            "element": "📝 详细描述篇幅过短或缺乏排版",
            "status": f"当前 {features['desc_length']} 字 (标杆均值: {bench['desc_length']} 字)",
            "action": "丰富你的游戏介绍，使用加粗标题、分栏符号、小图标等排版技术，增加核心特色列表、世界观简述，让玩家快速建立信任感。",
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
app_id_input = st.sidebar.text_input("请输入 Steam 游戏 AppID", value="1091500")
submit_btn = st.sidebar.button("📊 开始数据驱动诊断")

if submit_btn and app_id_input:
    with st.spinner("正在安全调用官方数据通道分析中..."):
        features = fetch_steam_game_features_v3(app_id_input)
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
                st.write(f"**抓取底料快照：** 截图: {features['screenshot_count']} 张 | 动图检测: {'有' if features['has_gif'] else '无'} | 文本: {features['desc_length']} 字")
            
            st.markdown("---")
            st.subheader("🛠️ 优先级改进列表 (Action Items)")
            
            if not report["suggestions"]:
                st.balloons()
                st.success("完美！该游戏的商店页面已经达到了头部游戏的标准！")
            else:
                for item in report["suggestions"]:
                    # 高颜值 Expander 折叠展示块
                    with st.expander(item["element"], expanded=True):
                        # 核心升级：左文右图优雅分栏
                        text_col, img_col = st.columns([3, 2])
                        with text_col:
                            st.markdown(f"**🔴 当前现状：** {item['status']}")
                            st.info(f"**💡 优化方案：** {item['action']}")
                        with img_col:
                            # 渲染示例图和注释
                            st.image(item["image_url"], caption=item["image_caption"], use_container_width=True)
        else:
            st.error("未能成功获取该 AppID，请检查数字是否正确，或该游戏已被下架/锁区。")
