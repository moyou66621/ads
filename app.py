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
    
    # 🌟 关键修复：补全所有能绕过 Steam 敏感内容及成人验证的全局 Cookies
    cookies = {
        "birthtime": "946656000",          # 设为 2000 年出生
        "lastagecheckage": "1-0-2000",
        "wants_mature_content": "1",        # 强行声明接受成人内容
        "data_mature_allowed": "1",         # 绕过部分新版大作的二级验证
        "browserid": "2858114536252114536", # 模拟合法的浏览器指纹
        "Steam_Language": "schinese"       # 锁定中文，便于文案长度测算
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

        # 正则切底层 JS 数据源抓截图
        html_source = response.text
        screenshot_matches = re.findall(r'g_rgScreenshotData\s*=\s*(\[.*?\]);', html_source, re.DOTALL)
        if screenshot_matches:
            screenshot_count = screenshot_matches[0].count('"filename"')
        else:
            screenshot_count = len(soup.find_all("div", class_=lambda x: x and 'highlight_screenshot' in x))

        # 提取详细描述
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
# 2. 诊断规则引擎逻辑
# ==========================================
def diagnose_game(features):
    score = 100
    suggestions = []
    bench = {"screenshot_count": 9, "has_gif": 1, "desc_length": 850}

    if features["screenshot_count"] < bench["screenshot_count"]:
        score -= int(((bench["screenshot_count"] - features["screenshot_count"]) / bench["screenshot_count"]) * 40)
        suggestions.append({
            "element": "📸 游戏截图数量不足",
            "status": f"当前 {features['screenshot_count']} 张 (标杆均值: {bench['screenshot_count']} 张)",
            "action": f"建议补齐至少 {bench['screenshot_count'] - features['screenshot_count']} 张核心玩法或带有 UI 的截图。独立游戏玩家极度看重实际游戏画面。"
        })
    if features["has_gif"] == 0:
        score -= 35
        suggestions.append({
            "element": "🎞️ 缺失动态 GIF 演示",
            "status": "当前页面无动图 (标杆游戏 100% 具备)",
            "action": "在详细描述前 1/3 黄金区域嵌入展示核心爽点（如华丽特效、连招、大招释放）的短 GIF 动图。"
        })
    if features["desc_length"] < bench["desc_length"] * 0.6:
        score -= 25
        suggestions.append({
            "element": "📝 详细描述篇幅过短",
            "status": f"当前 {features['desc_length']} 字 (标杆均值: {bench['desc_length']} 字)",
            "action": "丰富你的游戏介绍，增加核心特色列表、世界观简述，让玩家快速建立信任感。"
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
app_id_input = st.sidebar.text_input("请输入 Steam 游戏 AppID", value="1091500") # 默认换成赛博朋克测试
submit_btn = st.sidebar.button("📊 开始数据驱动诊断")

if submit_btn and app_id_input:
    with st.spinner("正在联网抓取 Steam 页面快照并分析..."):
        features = fetch_steam_game_features_v3(app_id_input)
        if features:
            report = diagnose_game(features)
            
            col1, col2 = st.columns([1, 2])
            
            # 左侧得分面板
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
            
            # 右侧快照
            with col2:
                st.subheader(f"🎮 游戏名称：{features['game_name']}")
                st.write(f"**核心标签快照：** {' | '.join(features['tags'])}")
                st.write(f"**抓取底料快照：** 截图: {features['screenshot_count']} 张 | 动图检测: {'有' if features['has_gif'] else '无'} | 文本: {features['desc_length']} 字")
            
            st.markdown("---")
            
            # 下方改进建议
            st.subheader("🛠️ 优先级改进列表 (Action Items)")
            if not report["suggestions"]:
                st.balloons()
                st.success("完美！该游戏的商店页面已经达到了头部游戏的标准！")
            else:
                for item in report["suggestions"]:
                    with st.expander(item["element"], expanded=True):
                        st.write(f"**当前现状：** {item['status']}")
                        st.info(f"**优化方案：** {item['action']}")
        else:
            st.error("未能成功抓取该 AppID，请检查数字是否正确或该游戏是否锁区。")