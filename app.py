import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# 1. 核心后端逻辑：破除年龄墙的防封爬虫
# ==========================================
def fetch_steam_game_features_v3(app_id):
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
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, "lxml")
        if "store.steampowered.com/#" in response.url or not soup.find("div", class_="apphub_AppName"): return None

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
        return {"game_name": game_name, "screenshot_count": screenshot_count, "desc_length": desc_length, "has_gif": 1 if gif_count > 0 else 0, "tags": tags}
    except:
        return None

# ==========================================
# 2. 诊断规则引擎逻辑（加入图片示例配置）
# ==========================================
def diagnose_game(features):
    score = 100
    suggestions = []
    bench = {"screenshot_count": 9, "has_gif": 1, "desc_length": 850}

    if features["screenshot_count"] < bench["screenshot_count"]:
        score -= int(((bench["screenshot_count"] - features["screenshot_count"]) / bench["screenshot_count"]) * 40)
        suggestions.append({
            "element": "📸 游戏截图数量或排版不足",
            "status": f"当前 {features['screenshot_count']} 张 (标杆均值: {bench['screenshot_count']} 张)",
            "action": f"建议补齐至少 {bench['screenshot_count'] - features['screenshot_count']} 张核心玩法或带有真实 UI 的截图。独立游戏玩家极度看重实际游戏画面，切忌全是播片宣传图。",
            "image_url": "https://images.unsplash.com/photo-1542751371-adc38448a05e?q=80&w=600&auto=format&fit=crop", # 示例图
            "image_caption": "💡 优秀示例：展示清晰的 UI、战斗激烈的游戏内真实截图（而非概念CG），能让玩家快速建立玩法预期。"
        })
        
    if features["has_gif"] == 0:
        score -= 35
        suggestions.append({
            "element": "🎞️ 缺失动态 GIF 演示（致命痛点）",
            "status": "当前胶囊描述区或详情页无动图 (标杆游戏 100% 具备)",
            "action": "在详细描述前 1/3 黄金区域嵌入展示核心爽点（如华丽特效、连招、大招释放或核心解谜反馈）的短 GIF 动图。静止的文字无法留住当代玩家。",
            "image_url": "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExM3BwZzV5N3N0NXFwaXo3bzh4ZndpZzV4M3VvYXRqMzhpdmF0OHV1diZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/vOsRdf74S6gIE/giphy.gif", # 经典像素战斗GIF
            "image_caption": "💡 优秀示例：在详情页黄金前排插入 2-3 秒高燃战斗/特效动图，玩家停留转化率平均提升 24%。"
        })
        
    if features["desc_length"] < bench["desc_length"] * 0.6:
        score -= 25
        suggestions.append({
            "element": "📝 详细描述篇幅过短或缺乏格式化",
            "status": f"当前 {features['desc_length']} 字 (标杆均值: {bench['desc_length']} 字)",
            "action": "丰富你的游戏介绍，使用加粗标题、分栏符号、小图标等排版技术，增加核心特色列表、世界观简述，让玩家快速建立信任感。",
            "image_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?q=80&w=600&auto=format&fit=crop", # 示例图
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
    with st.spinner("正在联网抓取 Steam 页面快照并分析..."):
        features = fetch_steam_game_features_v3(app_id_input)
        if features:
            report = diagnose_game(features)
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
                    # 🌟 核心升级：改用显眼的 Expander 容器包裹图文
                    with st.expander(item["element"], expanded=True):
                        # 左图右文分栏排版
                        text_col, img_col = st.columns([3, 2])
                        with text_col:
                            st.write(f"**🔴 当前现状：** {item['status']}")
                            st.info(f"**💡 优化方案：** {item['action']}")
                        with img_col:
                            # 渲染示例图和注释
                            st.image(item["image_url"], caption=item["image_caption"], use_container_width=True)
        else:
            st.error("未能成功抓取该 AppID，请检查数字是否正确或该游戏是否锁区。")
