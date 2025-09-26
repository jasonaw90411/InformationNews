# 安装依赖 pip3 install requests html5lib bs4 schedule
import os
import requests
import json
from openai import OpenAI
import feedparser
from newspaper import Article
from datetime import datetime
import time
import pytz

# 从环境变量获取微信公众号配置
appID = os.environ.get("APP_ID")
appSecret = os.environ.get("APP_SECRET")
openId = os.environ.get("OPEN_ID")
template_id = os.environ.get("TEMPLATE_ID")

# 添加环境变量验证和调试信息
print("===== 环境变量配置检查 =====")
print(f"APP_ID: {'已设置' if appID else '未设置'} (长度: {len(appID) if appID else 0})")
print(f"APP_SECRET: {'已设置' if appSecret else '未设置'} (长度: {len(appSecret) if appSecret else 0})")
print(f"OPEN_ID: {'已设置' if openId else '未设置'} (长度: {len(openId) if openId else 0})")
print(f"TEMPLATE_ID: {'已设置' if template_id else '未设置'} (长度: {len(template_id) if template_id else 0})")
print(f"TEMPLATE_ID 值: {template_id[:10]}...{template_id[-10:] if template_id and len(template_id) > 20 else template_id} (仅显示部分内容以保护隐私)")
print("=========================")

# 选择使用的AI服务 (deepseek 或 alimind)
ai_service = os.environ.get("AI_SERVICE", "deepseek")

if ai_service == "deepseek":
    # DeepSeek API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("环境变量 DEEPSEEK_API_KEY 未设置!")
    api_base_url = "https://api.deepseek.com/v1"
    model_name = "deepseek-chat"
elif ai_service == "alimind":
    # 阿里千文API配置
    api_key = os.environ.get("ALI_MIND_API_KEY")
    if not api_key:
        raise ValueError("环境变量 ALI_MIND_API_KEY 未设置!")
    api_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"  # 阿里千文兼容OpenAI接口的地址
    model_name = "qwen-turbo"  # 阿里千文模型名称
else:
    raise ValueError(f"不支持的AI服务类型: {ai_service}")

# 初始化OpenAI客户端
openai_client = OpenAI(api_key=api_key, base_url=api_base_url)
print(f"使用AI服务: {ai_service}, 模型: {model_name}")

# RSS源地址列表
rss_feeds = {
    "💲 华尔街见闻":{
        "华尔街见闻":"https://dedicated.wallstreetcn.com/rss.xml",      
    },
    "💻 36氪":{
        "36氪":"https://36kr.com/feed",   
        },
    "🇨🇳 中国经济": {
        "香港經濟日報":"https://www.hket.com/rss/china",
        "东方财富":"http://rss.eastmoney.com/rss_partener.xml",
        "百度股票焦点":"http://news.baidu.com/n?cmd=1&class=stock&tn=rss&sub=0",
        "中新网":"https://www.chinanews.com.cn/rss/finance.xml",
        "国家统计局-最新发布":"https://www.stats.gov.cn/sj/zxfb/rss.xml",
    },
      "🇺🇸 美国经济": {
        "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness",
        "华尔街日报 - 市场":"https://feeds.content.dowjones.io/public/rss/RSSMarketsMain",
        "MarketWatch美股": "https://www.marketwatch.com/rss/topstories",
        "ZeroHedge华尔街新闻": "https://feeds.feedburner.com/zerohedge/feed",
        "ETF Trends": "https://www.etftrends.com/feed/",
    },
    "🌍 世界经济": {
        "华尔街日报 - 经济":"https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
        "BBC全球经济": "http://feeds.bbci.co.uk/news/business/rss.xml",
    },
}

# 获取北京时间
def today_date():
    return datetime.now(pytz.timezone("Asia/Shanghai")).date()

# 获取当前时间段标识（上午/下午）
def get_time_period():
    hour = datetime.now(pytz.timezone("Asia/Shanghai")).hour
    if 6 <= hour < 12:
        return "上午"
    elif 12 <= hour < 18:
        return "下午"
    else:
        return "晚间"

# 爬取网页正文 (用于 AI 分析)
def fetch_article_text(url):
    try:
        print(f"📰 正在爬取文章内容: {url}")
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            print(f"⚠️ 文章内容为空: {url}")
        return text
    except Exception as e:
        print(f"❌ 文章爬取失败: {url}，错误: {e}")
        return "（未能获取文章正文）"

# 添加 User-Agent 头
def fetch_feed_with_headers(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    return feedparser.parse(url, request_headers=headers)

# 自动重试获取 RSS
def fetch_feed_with_retry(url, retries=3, delay=5):
    for i in range(retries):
        try:
            feed = fetch_feed_with_headers(url)
            if feed and hasattr(feed, 'entries') and len(feed.entries) > 0:
                return feed
        except Exception as e:
            print(f"⚠️ 第 {i+1} 次请求 {url} 失败: {e}")
            time.sleep(delay)
    print(f"❌ 跳过 {url}, 尝试 {retries} 次后仍失败。")
    return None

# 获取RSS内容（爬取正文用于分析）
def fetch_rss_articles(rss_feeds, max_articles=5):
    news_data = {}
    analysis_text = ""  # 用于AI分析的正文内容

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, url in sources.items():
            print(f"📡 正在获取 {source} 的 RSS 源: {url}")
            feed = fetch_feed_with_retry(url)
            if not feed:
                print(f"⚠️ 无法获取 {source} 的 RSS 数据")
                continue
            print(f"✅ {source} RSS 获取成功，共 {len(feed.entries)} 条新闻")

            articles = []  # 每个source都需要重新初始化列表
            for entry in feed.entries[:5]:
                title = entry.get('title', '无标题')
                link = entry.get('link', '') or entry.get('guid', '')
                if not link:
                    print(f"⚠️ {source} 的新闻 '{title}' 没有链接，跳过")
                    continue

                # 爬取正文用于分析
                article_text = fetch_article_text(link)
                analysis_text += f"【{title}】\n{article_text}\n\n"

                print(f"🔹 {source} - {title} 获取成功")
                articles.append(f"[{title}]({link})")

            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"

        news_data[category] = category_content

    return news_data, analysis_text

# AI 生成内容摘要（基于爬取的正文）
def summarize(text):
    completion = openai_client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": """
             你是一名专业的财经新闻分析师，请根据以下新闻内容，按照以下步骤完成任务：
             1. 提取新闻中涉及的主要行业和主题，找出近1天涨幅最高的3个行业或主题，以及近3天涨幅较高且此前2周表现平淡的3个行业/主题。（如新闻未提供具体涨幅，请结合描述和市场情绪推测热点）
             2. 针对每个热点，输出：
                - 催化剂：分析近期上涨的可能原因（政策、数据、事件、情绪等）。
                - 复盘：梳理过去3个月该行业/主题的核心逻辑、关键动态与阶段性走势。
                - 展望：判断该热点是短期炒作还是有持续行情潜力。
             3. 将以上分析整合为一篇1500字以内的财经热点摘要，逻辑清晰、重点突出，适合专业投资者阅读。
             """},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content.strip()

# 获取微信公众号access_token
def get_access_token():
    # 获取access token的url
    url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}' \
        .format(appID.strip(), appSecret.strip())
    response = requests.get(url).json()
    print(response)
    access_token = response.get('access_token')
    return access_token

# 发送财经新闻到微信
def send_news_to_wechat(access_token, news_content):
    print("===== 准备发送微信模板消息 =====")
    print(f"模板ID长度: {len(template_id)}")
    print(f"模板ID前10位: {template_id[:10] if template_id else '空'}")
    print(f"模板ID后10位: {template_id[-10:] if template_id and len(template_id) > 10 else '空'}")
    print(f"openId长度: {len(openId)}")
    
    # 验证必要参数
    if not access_token:
        print("❌ 错误: access_token为空")
        return {"errcode": -1, "errmsg": "access_token为空"}
    
    if not template_id:
        print("❌ 错误: template_id为空")
        return {"errcode": -1, "errmsg": "template_id为空"}
    
    if not openId:
        print("❌ 错误: openId为空")
        return {"errcode": -1, "errmsg": "openId为空"}

    today = datetime.now(pytz.timezone("Asia/Shanghai"))
    today_str = today.strftime("%Y年%m月%d日 %H:%M")
    time_period = get_time_period()

    body = {
        "touser": openId.strip(),
        "template_id": template_id.strip(),
        "url": "https://weixin.qq.com",
        "data": {
            "date": {
                "value": f"{today_str} - {time_period}推送"
            },
            "content": {
                "value": news_content[:1500]  # 微信模板消息单字段上限2048字符，设置1024以保证完整推送
            },
            "remark": {
                "value": f"{time_period}财经简报，更多详细内容请查看公众号"
            }
        }
    }
    
    # 打印消息体的关键信息用于调试（不打印敏感内容）
    print(f"发送参数概览: touser长度={len(body['touser'])}, template_id长度={len(body['template_id'])}")
    print(f"消息内容长度: {len(body['data']['content']['value'])} 字符")
    
    url = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}'.format(access_token)
    
    try:
        print("正在发送模板消息...")
        response = requests.post(url, json.dumps(body))
        print(f"响应状态码: {response.status_code}")
        print(f"原始响应内容: {response.text}")
        response_data = response.json()
        
        # 分析错误信息
        if response_data.get('errcode') == 40037:
            print("❌ 错误分析: template_id无效")
            print("可能原因:")
            print("1. 模板ID与微信公众平台上的不一致")
            print("2. 模板已被删除或禁用")
            print("3. 模板不在公众号的授权列表中")
            print("建议操作:")
            print("- 检查微信公众平台中的模板ID是否正确")
            print("- 确认模板是否包含date、content、remark三个字段")
        
        return response_data
    except Exception as e:
        print(f"❌ 发送过程中发生异常: {str(e)}")
        return {"errcode": -1, "errmsg": f"发送异常: {str(e)}"}

# 主函数
def news_report():
    # 1. 获取RSS文章
    articles_data, analysis_text = fetch_rss_articles(rss_feeds, max_articles=5)
    
    # 2. AI生成摘要
    summary = summarize(analysis_text)

    # 3. 生成最终消息
    today_str = today_date().strftime("%Y-%m-%d")
    time_period = get_time_period()
    final_summary = f"📅 {today_str} {time_period}财经新闻摘要\n\n✍️ {time_period}分析总结：\n{summary}\n\n---\n\n"
    for category, content in articles_data.items():
        if content.strip():
            final_summary += f"## {category}\n{content}\n\n"
    
    # 4. 获取access_token
    access_token = get_access_token()
    if not access_token:
        print("❌ 获取access_token失败")
        return
    
    # 5. 发送消息到微信
    print(f"📤 正在发送{time_period}财经新闻摘要到微信")
    response = send_news_to_wechat(access_token, final_summary)
    
    if response.get("errcode") == 0:
        print(f"✅ {time_period}财经新闻推送成功")
    else:
        print(f"❌ {time_period}财经新闻推送失败: {response}")

if __name__ == '__main__':
    news_report()