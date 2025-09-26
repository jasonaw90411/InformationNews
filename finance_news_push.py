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
        # 移除爬取文章开始的打印
        article = Article(url)
        article.download()
        article.parse()
        text = article.text[:1500]  # 限制长度，防止超出 API 输入限制
        if not text:
            # 移除内容为空的打印
            pass
        return text
    except Exception as e:
        # 移除爬取失败的打印
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
            # 移除失败重试的打印
            time.sleep(delay)
    # 移除最终失败的打印
    return None

# 获取RSS内容（爬取正文用于分析）
def fetch_rss_articles(rss_feeds, max_articles=5):
    news_data = {}
    analysis_text = ""  # 用于AI分析的正文内容

    for category, sources in rss_feeds.items():
        category_content = ""
        for source, url in sources.items():
            # 移除RSS获取开始的打印
            feed = fetch_feed_with_retry(url)
            if not feed:
                # 移除RSS获取失败的打印
                continue
            # 移除RSS获取成功的打印

            articles = []  # 每个source都需要重新初始化列表
            for entry in feed.entries[:5]:
                title = entry.get('title', '无标题')
                link = entry.get('link', '') or entry.get('guid', '')
                if not link:
                    # 移除无链接跳过的打印
                    continue

                # 爬取正文用于分析
                article_text = fetch_article_text(link)
                analysis_text += f"【{title}】\n{article_text}\n\n"

                # 移除单条新闻获取成功的打印
                articles.append(f"[{title}]({link})")

            if articles:
                category_content += f"### {source}\n" + "\n".join(articles) + "\n\n"

        news_data[category] = category_content

    return news_data, analysis_text

# AI 生成内容摘要（基于爬取的正文）
# 生成完整新闻摘要HTML文件
def generate_summary_html(summary_text):
    # 使用固定文件名在同层级生成HTML，便于GitHub Pages访问
    html_filename = 'finance_summary.html'
    
    # 生成当前时间字符串（单独计算，避免f-string中的语法问题）
    current_time = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y年%m月%d日 %H:%M:%S")
    
    # 获取时间戳，用于防止缓存
    timestamp = int(time.time())
    
    # 转义换行符为HTML<br>标签
    formatted_summary = summary_text.replace('\n', '<br>')
    
    # 生成HTML内容
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="format-detection" content="telephone=no">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>财经新闻摘要</title>
        <style>
            /* 安全区域样式重置 */
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            /* 基础样式 */
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
                line-height: 1.7;
                color: #333;
                max-width: 100%;
                margin: 0;
                padding: 0;
                background-color: #f8f8f8;
                -webkit-text-size-adjust: 100%;
                -webkit-tap-highlight-color: transparent;
            }}
            
            /* 容器样式 */
            .container {{
                max-width: 800px;
                margin: 0 auto;
                padding: 20px 15px;
                background-color: #fff;
                min-height: 100vh;
            }}
            
            /* 标题样式 */
            h1, h2, h3 {{
                color: #2c3e50;
                margin: 15px 0 10px 0;
                line-height: 1.4;
            }}
            
            h1 {{ font-size: 22px; padding-bottom: 10px; border-bottom: 1px solid #eee; }}
            h2 {{ font-size: 20px; }}
            h3 {{ font-size: 18px; }}
            
            /* 内容样式 */
            .summary-content {{ background: white; padding: 0; }}
            .summary-meta {{
                color: #666;
                font-size: 14px;
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #eee;
            }}
            
            .summary-body {{
                font-size: 16px;
                color: #333;
            }}
            
            /* 段落样式 */
            .summary-body > div {{
                margin-bottom: 15px;
            }}
            
            /* 响应式设计 */
            @media (max-width: 480px) {{
                .container {{
                    padding: 15px 12px;
                }}
                
                h1 {{ font-size: 20px; }}
                h2 {{ font-size: 18px; }}
                h3 {{ font-size: 16px; }}
                
                .summary-body {{
                    font-size: 15px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="summary-content">
                <h1>财经新闻摘要</h1>
                <div class="summary-meta">生成时间: {current_time} (版本: {timestamp})</div>
                <div class="summary-body">
                    {formatted_summary}
                </div>
            </div>
        </div>
        
        <script>
            // 简单的兼容性脚本
            document.addEventListener('DOMContentLoaded', function() {{
                // 处理iOS Safari上的滚动问题
                document.body.style.webkitOverflowScrolling = 'touch';
                
                // 防止缓存
                window.onpageshow = function(event) {{
                    if (event.persisted) {{
                        window.location.reload();
                    }}
                }};
            }});
        </script>
    </body>
    </html>
    """
    
    # 写入文件
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 返回文件的相对路径
    return html_filename

# AI 生成内容摘要（基于爬取的正文）
def summarize(text):
    completion = openai_client.chat.completions.create(
        model=model_name, 
        messages=[
            {"role": "system", "content":"你是一位经验丰富、逻辑严谨的财经新闻分析师，服务对象为券商分析师、基金经理、金融研究员、宏观策略师等专业人士。请基于以下财经新闻原文内容，完成高质量的内容理解与结构化总结，形成一份专业、精准、清晰的财经要点摘要，用于支持机构投资者的日常研判工作。【输出要求】1.全文控制在 2000 字以内，内容精炼、逻辑清晰；2.从宏观政策、金融市场、行业动态、公司事件、风险提示等角度进行分类总结；3.每一部分要突出数据支持、趋势研判、可能的市场影响；4.明确指出新闻背后的核心变量或政策意图，并提出投资视角下的参考意义；5.语气专业、严谨、无情绪化表达，适配专业机构投研阅读习惯；6.禁止套话，不重复新闻原文，可用条列式增强结构性；7.如涉及数据和预测，请标注来源或指出主张机构（如高盛、花旗等）；8.若原文较多内容无关财经市场，可酌情略去，只保留关键影响要素。"},
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
    # 移除响应打印
    access_token = response.get('access_token')
    return access_token

# 发送财经新闻到微信
def send_news_to_wechat(access_token, news_content, summary_html_path):
    # 删除调试信息
    
    # touser 就是 openID
    # template_id 就是模板ID
    # url 就是点击模板跳转的url
    # data按模板格式组织

    today = datetime.now(pytz.timezone("Asia/Shanghai"))
    today_str = today.strftime("%Y年%m月%d日 %H:%M")
    time_period = get_time_period()
    
    # 优化内容处理 - 处理可能导致显示问题的元素
    if isinstance(news_content, str):
        core_content = news_content
    else:
        core_content = "内容生成失败"

    # 使用GitHub Pages URL作为跳转链接，添加时间戳参数防止缓存
    # 获取当前时间戳作为URL参数，防止缓存
    timestamp = int(time.time())
    
    # 基础URL
    base_url = "https://jasonaw90411.github.io/InformationNews/finance_summary.html"
    github_pages_url = f"{base_url}?t={timestamp}"
    
    # 在GitHub Actions环境中，可以使用GITHUB_REPOSITORY环境变量来构建URL
    github_repo = os.environ.get('GITHUB_REPOSITORY', '')
    if github_repo:
        # github_repo 格式通常为 "username/repository"
        parts = github_repo.split('/')
        if len(parts) == 2:
            base_url = f"https://{parts[0]}.github.io/{parts[1]}/finance_summary.html"
            github_pages_url = f"{base_url}?t={timestamp}"
    
    body = {
        "touser": openId.strip(),
        "template_id": template_id.strip(),
        "url": github_pages_url,  # 使用GitHub Pages URL作为跳转链接
        "data": {
            "date": {
                "value": f"{today_str} - {time_period}推送"
            },
            "content": {
                "value": core_content
            },
            "remark": {
                "value": f"{time_period}财经简报"  
            }
        }
    }
    
    
    url = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}'.format(access_token)
    response = requests.post(url, json.dumps(body))
    # 移除响应状态打印
    return response.json()

# 主函数
def news_report():
    # 获取当前日期和时间段
    today = today_date()
    time_period = get_time_period()
    print(f"🔄 开始生成{time_period}财经新闻推送，日期: {today}")
    
    # 1. 获取RSS文章
    print("🔄 正在获取RSS文章...")
    articles_data, analysis_text = fetch_rss_articles(rss_feeds, max_articles=5)
    print(f"✅ 文章获取完成")
    print(f"   文章分类数量: {len(articles_data)}")
    print(f"   文章类别: {list(articles_data.keys())}")
    
    # 2. 使用AI生成财经新闻摘要
    today_str = today.strftime("%Y-%m-%d")
    final_summary = ""
    
    try:
        print("🧠 正在生成AI财经摘要...")
        ai_summary = summarize(analysis_text)
        print(f"✅ AI摘要生成完成，长度: {len(ai_summary)}字符")
        final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\n{ai_summary}\n\n---\n\n"
    except Exception as e:
        print(f"❌ AI摘要生成失败: {str(e)}")
        final_summary = f"📅 **{today_str} 财经新闻摘要**\n\n✍️ **今日分析总结：**\nAI摘要生成失败，请查看系统日志获取详细信息\n\n---\n\n"

    
    print("📝 正在组装最终消息...")
    for category, content in articles_data.items():
        if content.strip():
            print(f"   添加{category}类文章，长度: {len(content)}")
            final_summary += f"## {category}\n{content}\n\n"
    
    # 3. 获取access_token
    access_token = get_access_token()
    if not access_token:
        print("❌ 获取access_token失败")
        return
    
    # 4. 生成HTML文件，使用完整内容
    summary_html_path = generate_summary_html(final_summary)  # 使用完整内容
    
    # 5. 发送消息到微信
    response = send_news_to_wechat(access_token, final_summary, summary_html_path)
    
    if response.get("errcode") == 0:
        print(f"✅ {time_period}财经新闻推送成功")
    else:
        print(f"❌ {time_period}财经新闻推送失败: {response}")

if __name__ == '__main__':
    news_report()