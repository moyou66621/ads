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
                    
                    # ========== 显示游戏信息 ==========
                    st.success(f"✅ 找到游戏: {game_info['game_name']}")

                    # 获取游戏封面图和简介（从 Steam 页面额外抓取）
                    cover_url = ""
                    short_desc = ""
                    try:
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
                        resp = requests.get(url, headers=headers, cookies=cookies, timeout=10)
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "lxml")
                            # 获取封面图
                            cover_img = soup.find("img", class_="game_header_image_full")
                            if cover_img and cover_img.get("src"):
                                cover_url = cover_img["src"]
                            # 获取简介
                            desc_short = soup.find("div", class_="game_description_snippet")
                            if desc_short:
                                short_desc = desc_short.text.strip()
                            if not short_desc:
                                desc_area = soup.find("div", id="game_area_description")
                                if desc_area:
                                    short_desc = desc_area.text.strip()[:300] + "..."
                    except:
                        pass

                    # 布局：左侧封面图 + 右侧信息
                    col1, col2 = st.columns([1, 2])

                    with col1:
                        if cover_url:
                            st.image(cover_url, use_container_width=True)
                        else:
                            st.info("📷 暂无封面图")

                    with col2:
                        st.markdown(f"### 🎮 {game_info['game_name']}")
                        if short_desc:
                            st.markdown(f"**简介：** {short_desc}")
                        else:
                            st.markdown("暂无简介")

                        # 标签
                        if game_info.get('tags'):
                            st.markdown(f"**标签：** {', '.join(game_info['tags'][:5])}")

                        # Steam 链接
                        st.markdown(f"**Steam 页面：** [点击访问]({game_info['steam_url']})")

                        # ========== 教程平台跳转链接 ==========
                        st.markdown("---")
                        st.markdown("**📺 在以下平台搜索教程：**")

                        # 用游戏名构建搜索链接
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

                    # 查找相关教程
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
