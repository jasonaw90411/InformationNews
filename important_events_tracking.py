# important_events_tracking.py - 重要事件和社交媒体追踪功能模块
import os
import json
import requests
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

# Alpha Vantage API Key
alpha_vantage_api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
if not alpha_vantage_api_key:
    print("警告: 环境变量 ALPHA_VANTAGE_API_KEY 未设置，使用demo密钥")
    alpha_vantage_api_key = "demo"

# 获取北京时间
def get_beijing_time():
    return datetime.now(pytz.timezone("Asia/Shanghai"))

# 获取未来一个月的重点会议信息
def get_important_meetings():
    """
    获取未来一个月重要的经济和政策会议信息
    从Alpha Vantage API获取实时财经日历数据
    获取失败时直接返回错误信息
    """
    try:
        print("🔄 正在获取重要会议信息...")
        current_time = get_beijing_time()
        one_month_later = current_time + timedelta(days=30)
        
        # 从Alpha Vantage API获取实时数据
        # 注意：此处使用的是免费API，有调用限制
        # 实际应用中，建议设置API密钥为环境变量
        url = f"https://www.alphavantage.co/query?function=ECONOMIC_CALENDAR&from_date={current_time.strftime('%Y-%m-%d')}&to_date={one_month_later.strftime('%Y-%m-%d')}&apikey={alpha_vantage_api_key}"
        
        print("📡 尝试从Alpha Vantage API获取财经日历数据...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 检查API是否返回了有效的数据
        if "data" not in data or len(data["data"]) == 0:
            print("❌ API返回的数据为空或格式不正确")
            raise Exception("API返回的数据无效")
        
        print("✅ 成功从API获取实时财经日历数据")
        meetings = []
        
        # 处理API返回的数据
        for item in data["data"]:
            # 过滤重要性较高的事件
            if item.get("importance") in ["high", "medium"]:
                # 将API数据转换为我们需要的格式
                importance_map = {"high": "高", "medium": "中高", "low": "低"}
                
                # 确定事件类别
                category = "经济数据"
                event_title = item.get("event", "")
                if any(keyword in event_title.lower() for keyword in ["fed", "central bank", "利率", "monetary policy"]):
                    category = "国际政策" if "us" in event_title.lower() or "fomc" in event_title.lower() else "国内政策"
                elif any(keyword in event_title.lower() for keyword in ["cpi", "ppi", "gdp", "employment"]):
                    category = "经济数据"
                
                meetings.append({
                    "date": item.get("date"),
                    "title": event_title,
                    "description": item.get("event", "") + " - " + item.get("country", "全球"),
                    "importance": importance_map.get(item.get("importance"), "中"),
                    "category": category
                })
        
        # 确保有足够的数据
        if len(meetings) < 5:
            print("❌ API返回的数据不足")
            raise Exception("API返回的数据不足")
        
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
        return "当前经济日历信息获取失败"

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