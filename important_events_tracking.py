# important_events_tracking.py - 重要事件和社交媒体追踪功能模块
import os
import json
from datetime import datetime, timedelta
import pytz
from openai import OpenAI

# 初始化OpenAI客户端（与主程序保持一致）
ai_service = os.environ.get("AI_SERVICE", "deepseek")

if ai_service == "deepseek":
    # DeepSeek API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("警告: 环境变量 DEEPSEEK_API_KEY 未设置，使用模拟数据")
    api_base_url = "https://api.deepseek.com/v1"
    model_name = "deepseek-chat"
elif ai_service == "alimind":
    # 阿里千文API配置
    api_key = os.environ.get("ALI_MIND_API_KEY")
    if not api_key:
        print("警告: 环境变量 ALI_MIND_API_KEY 未设置，使用模拟数据")
    api_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 阿里千文兼容OpenAI接口的地址
    model_name = "qwen-turbo"  # 阿里千文模型名称
else:
    print("警告: 不支持的AI服务类型，使用模拟数据")
    api_key = None

# 初始化OpenAI客户端（仅在有API密钥时）
openai_client = OpenAI(api_key=api_key, base_url=api_base_url) if api_key else None

# 获取北京时间
def get_beijing_time():
    return datetime.now(pytz.timezone("Asia/Shanghai"))

# 获取未来一个月的重点会议信息
def get_important_meetings():
    """
    获取未来一个月重要的经济和政策会议信息
    在实际应用中，这里可以对接真实的API或数据源
    目前使用模拟数据
    """
    try:
        print("🔄 正在获取重要会议信息...")
        current_time = get_beijing_time()
        one_month_later = current_time + timedelta(days=30)
        
        # 模拟会议数据 - 实际应用中可以从外部API获取
        meetings = [
            {
                "date": (current_time + timedelta(days=2)).strftime("%Y-%m-%d"),
                "title": "中国CPI/PPI数据公布",
                "description": "国家统计局公布月度居民消费价格指数和工业生产者出厂价格指数",
                "importance": "高",
                "category": "经济数据"
            },
            {
                "date": (current_time + timedelta(days=5)).strftime("%Y-%m-%d"),
                "title": "美联储FOMC会议",
                "description": "美联储公开市场委员会讨论货币政策，可能宣布利率决议",
                "importance": "高",
                "category": "国际政策"
            },
            {
                "date": (current_time + timedelta(days=7)).strftime("%Y-%m-%d"),
                "title": "中国人民银行货币政策委员会会议",
                "description": "讨论当前货币政策和经济形势",
                "importance": "中高",
                "category": "国内政策"
            },
            {
                "date": (current_time + timedelta(days=10)).strftime("%Y-%m-%d"),
                "title": "美国非农就业报告",
                "description": "美国劳工部公布月度非农就业数据，是重要的经济指标",
                "importance": "高",
                "category": "经济数据"
            },
            {
                "date": (current_time + timedelta(days=15)).strftime("%Y-%m-%d"),
                "title": "中国三中全会（模拟日期）",
                "description": "讨论国家重要政策方向和经济改革措施",
                "importance": "高",
                "category": "国内政策"
            },
            {
                "date": (current_time + timedelta(days=18)).strftime("%Y-%m-%d"),
                "title": "欧盟央行利率决议",
                "description": "欧洲中央银行宣布最新利率决议和货币政策立场",
                "importance": "中高",
                "category": "国际政策"
            },
            {
                "date": (current_time + timedelta(days=22)).strftime("%Y-%m-%d"),
                "title": "中国GDP季度数据公布",
                "description": "国家统计局公布季度国内生产总值数据",
                "importance": "高",
                "category": "经济数据"
            },
            {
                "date": (current_time + timedelta(days=25)).strftime("%Y-%m-%d"),
                "title": "美国CPI数据公布",
                "description": "美国劳工部公布月度消费者价格指数数据",
                "importance": "高",
                "category": "经济数据"
            },
            {
                "date": (current_time + timedelta(days=28)).strftime("%Y-%m-%d"),
                "title": "OPEC+部长级会议",
                "description": "讨论石油产量政策和市场调节措施",
                "importance": "中高",
                "category": "国际政策"
            }
        ]
        
        # 按日期排序会议
        meetings.sort(key=lambda x: x["date"])
        
        # 生成Markdown格式的会议列表
        markdown_content = "# 📅 未来一个月重要经济与政策会议\n\n"
        markdown_content += f"*数据更新时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        # 按类别分组显示会议
        categories = {"国内政策": [], "国际政策": [], "经济数据": []}
        for meeting in meetings:
            category = meeting["category"]
            if category in categories:
                categories[category].append(meeting)
        
        # 为每个类别生成内容
        for category_name, category_meetings in categories.items():
            if category_meetings:
                markdown_content += f"## {category_name}\n\n"
                for meeting in category_meetings:
                    # 根据重要性添加标记
                    importance_marker = "🔴 " if meeting["importance"] == "高" else "🟠 "
                    markdown_content += f"### {importance_marker}{meeting['date']} - {meeting['title']}\n"
                    markdown_content += f"- **重要性**: {meeting['importance']}\n"
                    markdown_content += f"- **描述**: {meeting['description']}\n\n"
        
        print("✅ 重要会议信息获取成功")
        return markdown_content
    except Exception as e:
        print(f"❌ 获取重要会议信息失败: {str(e)}")
        # 返回错误信息
        return "# 📅 未来一个月重要经济与政策会议\n\n获取会议信息失败，请稍后重试。"

# 获取社交媒体重要人物的最新消息
def get_social_media_updates():
    """
    获取特朗普和马斯克的X(Twitter)最新动态
    在实际应用中，这里需要使用Twitter API或第三方服务
    目前使用模拟数据
    """
    try:
        print("🔄 正在获取社交媒体重要人物最新动态...")
        current_time = get_beijing_time()
        
        # 模拟社交媒体数据 - 实际应用中可以从Twitter API获取
        social_media_data = {
            "Elon Musk": {
                "username": "elonmusk",
                "latest_post": "Just announced Tesla's new AI chip development. This will revolutionize autonomous driving capabilities and potentially have applications beyond automotive.",
                "post_time": (current_time - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
                "avatar": "https://pbs.twimg.com/profile_images/1676253427580887041/_kdXo4pE_400x400.jpg",
                "verified": True
            },
            "Donald J. Trump": {
                "username": "DonaldJTrump",
                "latest_post": "Great economic numbers today! America is winning again. The stock market is booming and jobs are being created at record levels. We need to keep this momentum going!",
                "post_time": (current_time - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                "avatar": "https://pbs.twimg.com/profile_images/1296667294030526464/DH1Z18t__400x400.jpg",
                "verified": True
            }
        }
        
        # 生成Markdown格式的社交媒体更新
        markdown_content = "# 📱 重要人物社交媒体最新动态\n\n"
        markdown_content += f"*数据更新时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        for name, data in social_media_data.items():
            verified_badge = "✅ " if data["verified"] else ""
            markdown_content += f"## {verified_badge}{name} (@{data['username']})\n\n"
            markdown_content += f"### 最新动态\n"
            markdown_content += f"> {data['latest_post']}\n\n"
            markdown_content += f"**发布时间**: {data['post_time']} (北京时间)\n\n"
            markdown_content += "---\n\n"
        
        print("✅ 社交媒体更新获取成功")
        return markdown_content
    except Exception as e:
        print(f"❌ 获取社交媒体更新失败: {str(e)}")
        # 返回错误信息
        return "# 📱 重要人物社交媒体最新动态\n\n获取社交媒体更新失败，请稍后重试。"

# 生成完整的事件追踪报告
def generate_events_tracking_report():
    """
    生成包含重要会议和社交媒体更新的完整报告
    """
    try:
        print("🔄 正在生成事件追踪报告...")
        
        # 获取重要会议信息
        meetings_report = get_important_meetings()
        
        # 获取社交媒体更新
        social_media_report = get_social_media_updates()
        
        # 合并报告
        full_report = f"## 📊 重要事件与社交媒体追踪\n\n"
        full_report += meetings_report
        full_report += "\n---\n\n"
        full_report += social_media_report
        
        print("✅ 事件追踪报告生成成功")
        return full_report
    except Exception as e:
        print(f"❌ 生成事件追踪报告失败: {str(e)}")
        return "## 📊 重要事件与社交媒体追踪\n\n生成报告失败，请稍后重试。"

# 测试函数
def test_events_tracking():
    """
    测试事件追踪功能
    """
    report = generate_events_tracking_report()
    print("\n=== 事件追踪报告测试 ===")
    print(report[:500] + "..." if len(report) > 500 else report)

if __name__ == "__main__":
    test_events_tracking()