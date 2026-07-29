# ==========================================
# 0. 演示数据生成器（首次启动时自动运行）
# ==========================================
def generate_demo_users():
    """如果数据库为空，自动生成 30 个演示用户，让看板立即可用"""
    if os.path.exists(USER_DATA_FILE) and os.path.getsize(USER_DATA_FILE) > 100:
        return  # 已有数据，跳过

    import random
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

    # 同时生成一些演示攻略
    demo_strategies = {}
    sample_games = ["艾尔登法环", "赛博朋克2077", "星露谷物语", "空洞骑士", "巫师3", "只狼", "文明6", "我的世界"]
    for i in range(10):
        sid = f"demo_strategy_{i}"
        game = random.choice(sample_games)
        demo_strategies[sid] = {
            "game_name": game,
            "title": f"【新手向】{game} 入门指南 {i+1}",
            "tags": ["新手向", "避坑指南"],
            "content": f"这是关于《{game}》的演示攻略内容。在 Compass 中，每位玩家都可以分享自己的游戏经验，帮助新玩家快速上手。",
            "author": f"Demo_Player_{random.randint(1,30):02d}",
            "time": (datetime.now() - timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d %H:%M")
        }
    save_json_db(STRATEGY_DB_FILE, demo_strategies)

    # 生成演示活动日志
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

    print("✅ Compass 演示数据已生成（30位玩家 + 10篇攻略）")
