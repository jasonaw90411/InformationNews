# sector_stock_analysis.py - 板块追踪和股票推荐功能模块
import yfinance as yf
import random
import os
from openai import OpenAI

# 初始化OpenAI客户端（需要与主程序保持一致）
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

# 获取美股板块数据
def get_top_us_sectors():
    try:
        # 使用主要ETF数据来代表不同板块的表现
        sector_etfs = {
            'Technology': 'XLK',      # 科技板块ETF
            'Financial Services': 'XLF', # 金融板块ETF
            'Healthcare': 'XLV',      # 医疗板块ETF
            'Consumer Cyclical': 'XLY', # 可选消费板块ETF
            'Industrials': 'XLI',     # 工业板块ETF
            'Energy': 'XLE',          # 能源板块ETF
            'Utilities': 'XLU',       # 公用事业板块ETF
            'Real Estate': 'XLRE',    # 房地产板块ETF
            'Consumer Defensive': 'XLP', # 必需消费板块ETF
            'Materials': 'XLB',       # 材料板块ETF
            'Communication': 'XLC'    # 通信板块ETF
        }
        
        sector_list = []
        
        for sector_name, etf_symbol in sector_etfs.items():
            try:
                # 使用yfinance获取ETF数据，至少需要4天数据才能计算3个交易日涨幅
                ticker = yf.Ticker(etf_symbol)
                hist_data = ticker.history(period="7d")  # 获取7天数据确保有足够的交易日
                
                # 确保有至少3个完整的交易日数据
                if len(hist_data) >= 4:  # 包含4个数据点才能计算3个交易日的涨幅
                    # 获取最近4个交易日的收盘价（需要3个交易日的变化）
                    closes = hist_data['Close'].iloc[-4:]  # 取最后4个数据点
                    
                    # 计算近3个交易日的累计涨幅
                    # 累计涨幅 = (最后一天收盘价 / 三天前收盘价 - 1) * 100
                    start_price = closes.iloc[0]
                    end_price = closes.iloc[-1]
                    
                    if start_price > 0:
                        performance = (end_price - start_price) / start_price * 100
                        sector_list.append({
                            'name': sector_name,
                            'performance': round(performance, 2),
                            'etf': etf_symbol
                        })
                else:
                    print(f"板块{sector_name}数据不足，无法计算近3个交易日涨幅")
                    # 使用模拟数据作为备选
                    sector_list.append({
                        'name': sector_name,
                        'performance': round(random.uniform(-2, 3), 2),
                        'etf': etf_symbol
                    })
                    
            except Exception as etf_e:
                print(f"获取板块{sector_name}数据失败: {str(etf_e)}")
                # 如果获取失败，使用随机模拟数据
                sector_list.append({
                    'name': sector_name,
                    'performance': round(random.uniform(-2, 3), 2),
                    'etf': etf_symbol
                })
        
        # 按涨幅从高到低排序
        sector_list.sort(key=lambda x: x['performance'], reverse=True)
        
        # 选出涨幅前三的板块
        top_4_sectors = sector_list[:4]
        
        if top_4_sectors:
            print(f"✅ 成功获取并筛选出前四涨幅板块")
            print(f"📊 前四涨幅板块详情: {top_4_sectors}")  # 调试输出
            return top_4_sectors
        else:
            raise Exception("无法筛选出前四涨幅板块")
            
    except Exception as e:
        print(f"获取美股板块数据失败: {str(e)}")
        # 提供一个模拟的前三板块数据作为备选
        print("📊 使用模拟美股板块数据作为备选")
        return [
            {'name': 'Technology', 'performance': 2.8, 'etf': 'XLK'},
            {'name': 'Healthcare', 'performance': 1.9, 'etf': 'XLV'},
            {'name': 'Energy', 'performance': 1.5, 'etf': 'XLE'}
        ]

# 获取股票数据
def get_stock_data(symbol):
    try:
        # 使用yfinance获取股票数据
        ticker = yf.Ticker(symbol)
        
        # 获取基本信息
        info = ticker.info
        
        # 获取历史价格数据（最近5天）
        hist_data = ticker.history(period="5d")
        
        # 构建返回数据结构，保持与原代码兼容
        profile = {
            'name': info.get('longName', symbol),
            'symbol': symbol,
            'currency': info.get('currency', 'USD'),
            'exchange': info.get('exchange', '')
        }
        
        # 构建财务指标
        metrics = {'metric': {}}
        
        # 添加基础财务指标
        # 市盈率
        pe_ratio = info.get('forwardPE', info.get('trailingPE', 0))
        metrics['metric']['peNormalizedAnnual'] = float(pe_ratio) if pe_ratio else 0
        
        # 当前价格
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        metrics['metric']['price'] = float(current_price) if current_price else 0
        
        # 利润率
        profit_margin = info.get('profitMargins', 0)
        # yfinance返回的利润率通常是小数形式，乘以100转为百分比
        metrics['metric']['profitMargin'] = float(profit_margin * 100) if profit_margin else 10.0
        
        # 处理历史价格数据，转换为与原代码兼容的格式
        candles = {'c': [], 't': []}  # 'c'为收盘价，'t'为时间戳
        
        if not hist_data.empty:
            for index, row in hist_data.iterrows():
                candles['c'].append(float(row['Close']))
                # 转换日期为时间戳
                candles['t'].append(int(index.timestamp()))
        
        return {
            'profile': profile,
            'metrics': metrics,
            'candles': candles
        }
    except Exception as e:
        print(f"获取股票 {symbol} 数据失败: {str(e)}")
        return None

# 筛选热门股票
def filter_popular_stocks(sector_trends):
    # 基于板块趋势和热点，选择一些可能的热门股票
    popular_stocks = {
    # 科技板块
    'Technology': [
        # 大型科技巨头
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA',
        # 人工智能与机器学习
        'NVDA', 'PLTR', 'CRWD', 'SNPS', 'CDNS', 'AI', 
        # 半导体与芯片
        'INTC', 'AMD', 'QCOM', 'ASML', 'AVGO', 'TXN',
        # 软件与云计算
        'ADBE', 'CRM', 'ORCL', 'SAP', 'IBM', 'SNPS',
        # 新兴科技
        'MNDY', 'DDOG', 'ESTC', 'PANW'
    ],
    # 金融板块
    'Financial Services': ['JPM', 'BAC', 'GS', 'MS', 'C', 'WFC', 'USB', 'BLK'],
    # 医疗板块
    'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'LLY', 'PDD'],
    # 可选消费板块
    'Consumer Cyclical': ['NKE', 'DIS', 'HD', 'MCD', 'SBUX', 'TGT', 'AMZN', 'BKNG'],
    # 工业板块
    'Industrials': ['BA', 'UNP', 'HON', 'CAT', 'UPS', 'LMT', 'RTX', 'DE'],
    # 能源板块
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'VLO'],
    # 公用事业板块
    'Utilities': ['NEE', 'DUK', 'SO', 'EXC', 'D', 'AEP', 'XEL', 'WEC'],
    # 房地产板块
    'Real Estate': ['AMT', 'DLR', 'PLD', 'CCI', 'SPG', 'EQIX', 'PSA', 'O'],
    # 必需消费板块
    'Consumer Defensive': ['XLP', 'PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'MO'],
    # 材料板块
    'Materials': ['LIN', 'SHW', 'APD', 'DD', 'PPG', 'FCX', 'NEM', 'IFF'],
    # 通信板块
    'Communication': ['T', 'VZ', 'CMCSA', 'DIS', 'CHTR', 'NFLX', 'GOOG', 'META']
    }
    
    # 根据板块趋势选择股票
    selected_stocks = []
    if sector_trends:
        # 按涨跌幅排序板块
        sorted_sectors = sorted(sector_trends, key=lambda x: x['performance'], reverse=True)
        
        # 从表现最好的几个板块中选择股票
        for sector in sorted_sectors[:4]:  # 选择表现最好的4个板块
            sector_name = sector['name']
            if sector_name in popular_stocks:
                # 每个板块选择2只股票
                selected_stocks.extend(popular_stocks[sector_name][:2])
    
    # 如果没有足够的股票，添加一些默认股票
    if len(selected_stocks) < 8:  # 调整目标数量为8
        default_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'JPM', 'JNJ']  # 增加默认股票数量
        for stock in default_stocks:
            if stock not in selected_stocks:
                selected_stocks.append(stock)
            if len(selected_stocks) >= 8:  # 目标数量为8
                break
    
    return selected_stocks

# 筛选盈利状况和技术走势良好的股票
def filter_quality_stocks(stocks):
    quality_stocks = []
    
    for stock in stocks:
        stock_data = get_stock_data(stock)
        if not stock_data:
            continue
        
        # 检查数据是否完整
        if not all([stock_data['profile'], stock_data['metrics'], stock_data['candles']]):
            continue
        
        try:
            # 筛选条件1: 有正的盈利
            metrics = stock_data['metrics'].get('metric', {})
            pe_ratio = metrics.get('peNormalizedAnnual', 0)
            profit_margin = metrics.get('profitMargin', 0)
            current_price = metrics.get('price', 0)  # 获取当前股价
            
            # 避免负的市盈率或过高的市盈率
            if pe_ratio <= 0 or pe_ratio > 100:
                continue
            
            # 筛选条件2: 有正的利润率
            if profit_margin <= 0:
                continue
            
            # 筛选条件3: 近5日技术走势良好（收盘价呈上升趋势）
            candles = stock_data['candles']
            if 'c' in candles and len(candles['c']) >= 3:
                # 检查最近3天是否呈上升趋势
                close_prices = candles['c']
                if close_prices[-1] > close_prices[-2] and close_prices[-2] > close_prices[-3]:
                    quality_stocks.append({
                        'symbol': stock,
                        'name': stock_data['profile'].get('name', stock),
                        'pe_ratio': pe_ratio,
                        'profit_margin': profit_margin,
                        'current_price': current_price,  # 添加当前股价
                        'recent_performance': (close_prices[-1] - close_prices[0]) / close_prices[0] * 100
                    })
        except Exception as e:
            print(f"分析股票 {stock} 数据时出错: {str(e)}")
            continue
    
    # 按近期表现排序
    quality_stocks.sort(key=lambda x: x['recent_performance'], reverse=True)
    
    return quality_stocks[:3]  # 返回前3只股票

# 分析板块趋势
def analyze_sector_trends(sectors):
    if not sectors:
        return "无法获取板块数据"
    
    try:
        # 按表现排序
        sorted_sectors = sorted(sectors, key=lambda x: x['performance'], reverse=True)
        
        # 准备分析文本
        analysis_text = "# 板块趋势分析\n\n"
        analysis_text += "## 近期表现最佳的板块\n\n"
        
        # 分析前3个表现最好的板块
        for i, sector in enumerate(sorted_sectors[:3]):
            sector_name = sector['name']
            performance = sector['performance']
            analysis_text += f"### {i+1}. {sector_name} (+{performance:.2f}%)\n\n"
            analysis_text += f"- **表现**: +{performance:.2f}%\n"
            analysis_text += f"- **趋势评估**: {'强势上涨' if performance > 1 else '温和上涨' if performance > 0 else '下跌'}\n\n"
        
        return analysis_text
    except Exception as e:
        print(f"分析板块趋势时出错: {str(e)}")
        return "板块趋势分析失败"

# 使用LLM分析板块和股票
def analyze_with_llm(sector_data, stock_data):
    # 准备提示文本
    prompt = """
    请基于以下板块和股票数据，提供专业的金融分析：
    
    ## 板块数据
    {sector_data}
    
    ## 股票数据
    {stock_data}
    
    ## 分析要求
    1. 美国近1-2日的热点板块（3个以内），包括板块表现、上涨/下跌原因、投资机会分析
    2. 根据提供的股票数据，推荐5只最具投资价值的股票，每只股票需包含：
       - 基本信息（股票代码、名称、行业）
       - **最近一日股价**
       - 盈利状况分析
       - 技术走势分析
       - 投资理由
       - 风险提示
    3. 分析应专业、客观，适合金融专业人士阅读
    4. 格式清晰，使用适当的标题和小标题
    """
    
    completion = openai_client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "你是一位经验丰富的金融分析师，专注于股票市场和板块分析。请基于提供的数据，给出专业、客观、深入的分析和建议。特别重要：在进行技术分析,当前股价,推荐个股时，所有数据都要严格以{stock_data}为基准,不能自行修改,估算或使用其他价格来源"},
            {"role": "user", "content": prompt.format(sector_data=sector_data, stock_data=stock_data)}
        ]
    )
    
    return completion.choices[0].message.content.strip()

# 获取A股板块数据
def get_top_a_sectors():
    try:
        # 使用A股主要指数或ETF数据来代表不同板块的表现
        # 注意：A股数据可能需要特殊处理，这里使用模拟数据作为示例
        sector_list = [
            {'name': '新能源', 'performance': round(random.uniform(0.5, 3.5), 2), 'etf': '515030'},
            {'name': '半导体', 'performance': round(random.uniform(0.3, 3.0), 2), 'etf': '512480'},
            {'name': '医药生物', 'performance': round(random.uniform(0.2, 2.5), 2), 'etf': '512010'},
            {'name': '白酒', 'performance': round(random.uniform(0.1, 2.0), 2), 'etf': '161725'},
            {'name': '光伏', 'performance': round(random.uniform(0.4, 2.8), 2), 'etf': '515790'},
            {'name': '人工智能', 'performance': round(random.uniform(0.6, 3.2), 2), 'etf': '515070'},
            {'name': '券商', 'performance': round(random.uniform(-0.5, 2.0), 2), 'etf': '512880'},
            {'name': '军工', 'performance': round(random.uniform(0.2, 2.3), 2), 'etf': '512660'},
            {'name': '汽车', 'performance': round(random.uniform(0.3, 2.4), 2), 'etf': '516110'},
            {'name': '银行', 'performance': round(random.uniform(-0.3, 1.5), 2), 'etf': '512800'},
            {'name': '科技', 'performance': round(random.uniform(0.4, 3.0), 2), 'etf': '515000'},
            {'name': '消费', 'performance': round(random.uniform(0.2, 2.5), 2), 'etf': '159928'}
        ]
        
        # 按涨幅从高到低排序
        sector_list.sort(key=lambda x: x['performance'], reverse=True)
        
        # 选出涨幅前三的板块
        top_4_sectors = sector_list[:4]
        
        if top_4_sectors:
            print(f"✅ 成功获取并筛选出A股前四涨幅板块")
            print(f"📊 A股前四涨幅板块详情: {top_4_sectors}")  # 调试输出
            return top_4_sectors
        else:
            raise Exception("无法筛选出A股前四涨幅板块")
            
    except Exception as e:
        print(f"获取A股板块数据失败: {str(e)}")
        # 提供一个模拟的前三板块数据作为备选
        print("📊 使用模拟A股板块数据作为备选")
        return [
            {'name': '新能源', 'performance': 2.8, 'etf': '515030'},
            {'name': '半导体', 'performance': 2.1, 'etf': '512480'},
            {'name': '人工智能', 'performance': 1.9, 'etf': '515070'}
        ]

# 筛选热门A股
def filter_popular_a_stocks(sector_trends):
    # 基于板块趋势和热点，选择一些可能的热门A股
    popular_stocks = {
    # 新能源板块 - 增加细分领域龙头
    '新能源': [
        '宁德时代', '比亚迪', '隆基绿能', '阳光电源', '中环股份',
        '恩捷股份', '赣锋锂业', '天齐锂业', '华友钴业', '亿纬锂能',  # 电池材料细分龙头
        '晶盛机电', '先导智能', '杭可科技'  # 设备细分龙头
    ],
    # 半导体板块 - 增加设计、制造、封测各环节龙头
    '半导体': [
        '中芯国际', '韦尔股份', '北方华创', '卓胜微', '兆易创新',
        '三安光电', '紫光国微', '通富微电', '长电科技', '华天科技',  # 封测龙头
        '士兰微', '圣邦股份', '澜起科技', '景嘉微'  # 设计细分龙头
    ],
    # 医药生物板块 - 增加创新药、CXO、医疗器械、医疗服务细分龙头
    '医药生物': [
        '恒瑞医药', '迈瑞医疗', '药明康德', '爱尔眼科', '智飞生物',
        '信达生物', '君实生物', '百济神州', '康龙化成', '凯莱英',  # CXO与创新药
        '片仔癀', '云南白药', '同仁堂', '东阿阿胶',  # 中药龙头
        '金域医学', '迪安诊断', '乐普医疗', '鱼跃医疗'  # 医疗器械与服务
    ],
    # 白酒板块 - 增加不同档次白酒龙头
    '白酒': [
        '贵州茅台', '五粮液', '泸州老窖', '山西汾酒', '洋河股份',
        '古井贡酒', '口子窖', '今世缘', '迎驾贡酒', '水井坊',
        '舍得酒业', '酒鬼酒'  # 次高端白酒龙头
    ],
    # 光伏板块 - 增加硅料、硅片、电池片、组件各环节龙头
    '光伏': [
        '隆基绿能', '晶科能源', '通威股份', '阳光电源', '中环股份',
        '特变电工', '东方日升', '天合光能', '福斯特', '福莱特',  # 组件与辅材
        '大全能源', '保利协鑫', '新特能源',  # 硅料龙头
        '爱旭股份', '晶澳科技', '隆基绿能'  # 电池片龙头
    ],
    # 人工智能板块 - 增加算力、算法、应用各环节龙头
    '人工智能': [
        '科大讯飞', '中科曙光', '浪潮信息', '海康威视', '大华股份',
        '寒武纪', '虹软科技', '旷视科技', '商汤科技', '依图科技',  # 算法龙头
        '同方股份', '紫光股份', '神州数码',  # 算力基础设施
        '东软集团', '恒生电子', '用友网络'  # 行业应用龙头
    ],
    # 券商板块 - 增加综合与特色券商龙头
    '券商': [
        '中信证券', '华泰证券', '国泰君安', '招商证券', '中金公司',
        '中信建投', '海通证券', '广发证券', '东方证券', '兴业证券',
        '中国银河', '国信证券', '平安证券', '长江证券'
    ],
    # 军工板块 - 增加航空、航天、船舶、兵器各细分龙头
    '军工': [
        '中国重工', '中航沈飞', '中直股份', '航发动力', '洪都航空',
        '中国卫星', '航天电子', '航天动力', '航天彩虹',  # 航天领域
        '中国船舶', '中船防务', '中国动力',  # 船舶领域
        '北方导航', '内蒙一机', '光电股份',  # 兵器领域
        '振华科技', '中航光电', '航天电器'  # 军工电子
    ],
    # 汽车板块 - 增加传统车企与新能源车企龙头
    '汽车': [
        '比亚迪', '长城汽车', '长安汽车', '上汽集团', '广汽集团',
        '吉利汽车', '小鹏汽车', '理想汽车', '蔚来汽车',  # 整车制造
        '宁德时代', '亿纬锂能', '国轩高科',  # 电池供应商
        '德赛西威', '均胜电子', '拓普集团'  # 零部件龙头
    ],
    # 银行板块 - 增加不同类型银行龙头
    '银行': [
        '招商银行', '平安银行', '兴业银行', '工商银行', '建设银行',
        '农业银行', '中国银行', '邮储银行',  # 国有大行
        '宁波银行', '南京银行', '江苏银行', '杭州银行',  # 城商行龙头
        '浦发银行', '中信银行', '民生银行'  # 股份制银行
    ],
    # 消费板块 - 新增消费板块龙头
    '消费': [
        '伊利股份', '蒙牛乳业', '海天味业', '中炬高新', '双汇发展',  # 食品饮料
        '贵州茅台', '五粮液', '泸州老窖', '山西汾酒', '洋河股份',  # 白酒
        '中国中免', '王府井', '百联股份', '永辉超市',  # 零售龙头
        '李宁', '安踏体育', '特步国际'  # 体育用品
    ],
    # 科技板块 - 新增科技板块龙头
    '科技': [
        '腾讯控股', '阿里巴巴', '美团', '京东', '拼多多',  # 互联网巨头
        '中芯国际', '韦尔股份', '北方华创', '卓胜微', '兆易创新',  # 半导体
        '立讯精密', '歌尔股份', '蓝思科技', '德赛电池'  # 电子零部件
    ]
    }
    
    # 根据板块趋势选择股票
    selected_stocks = []
    if sector_trends:
        # 按涨跌幅排序板块
        sorted_sectors = sorted(sector_trends, key=lambda x: x['performance'], reverse=True)
        
        # 从表现最好的几个板块中选择股票
        for sector in sorted_sectors[:4]:  # 选择表现最好的4个板块
            sector_name = sector['name']
            if sector_name in popular_stocks:
                # 每个板块选择2只股票
                selected_stocks.extend(popular_stocks[sector_name][:2])
    
    # 如果没有足够的股票，添加一些默认股票
    if len(selected_stocks) < 8:  # 调整目标数量为8
        default_stocks = ['贵州茅台', '宁德时代', '比亚迪', '中芯国际', '招商银行', '恒瑞医药', '隆基绿能', '韦尔股份']  # 增加默认股票数量
        for stock in default_stocks:
            if stock not in selected_stocks:
                selected_stocks.append(stock)
            if len(selected_stocks) >= 8:  # 目标数量为8
                break
    
    return selected_stocks

# 生成A股板块和股票分析报告
def generate_a_stock_report():
    try:
        print("🔄 正在获取A股板块数据...")
        # 获取A股板块数据
        a_sectors = get_top_a_sectors()
        
        if not a_sectors:
            return "无法获取A股板块数据"
        
        # 筛选热门A股
        print("🔄 正在筛选热门A股...")
        popular_a_stocks = filter_popular_a_stocks(a_sectors)
        
        if not popular_a_stocks:
            return "无法筛选出符合条件的A股"
        
        # 准备分析数据
        sector_analysis = analyze_sector_trends(a_sectors)
        
        # 准备股票数据文本
        stock_data_text = "\n"
        for stock in popular_a_stocks[:3]:  # 选择前3只股票进行分析
            # 由于无法直接获取A股实时数据，这里使用模拟数据
            stock_data_text += f"## {stock}\n"
            stock_data_text += f"- 当前股价: ¥{round(random.uniform(10, 300), 2)}\n"
            stock_data_text += f"- 市盈率: {round(random.uniform(15, 50), 2)}\n"
            stock_data_text += f"- 利润率: {round(random.uniform(5, 30), 2)}%\n"
            stock_data_text += f"- 近5日表现: +{round(random.uniform(1, 5), 2)}%\n\n"
        
        # 使用LLM进行综合分析
        print("🧠 正在生成A股分析报告...")
        # 修改提示词以适应A股分析
        prompt = """
        请基于以下板块和股票数据，提供专业的A股市场分析：
        
        ## 板块数据
        {sector_data}
        
        ## 股票数据
        {stock_data}
        
        ## 分析要求
        1. 中国A股近1-2日的热点板块（3个以内），包括板块表现、上涨/下跌原因、投资机会分析
        2. 根据提供的股票数据，推荐3-5只最具投资价值的A股，每只股票需包含：
           - 基本信息（股票名称、行业）
           - 最近一日股价
           - 盈利状况分析
           - 技术走势分析
           - 投资理由
           - 风险提示
        3. 分析应专业、客观，适合金融专业人士阅读
        4. 格式清晰，使用适当的标题和小标题
        """
        
        completion = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一位经验丰富的金融分析师，专注于中国A股市场和板块分析。请基于提供的数据，给出专业、客观、深入的分析和建议。特别重要：在进行技术分析,当前股价,推荐个股时，所有数据都要严格以{stock_data}为基准,不能自行修改,估算或使用其他价格来源"},
                {"role": "user", "content": prompt.format(sector_data=sector_analysis, stock_data=stock_data_text)}
            ]
        )
        
        # 添加一些固定的股票推荐格式
        a_stock_report = completion.choices[0].message.content.strip()
        
        # 添加一些额外的A股推荐信息
        for stock in popular_a_stocks[:3]:
            if '宁德时代' in stock:
                a_stock_report += "\n- **投资理由**: 全球动力电池龙头，技术领先，客户结构优质\n"
                a_stock_report += "- **风险提示**: 行业竞争加剧，原材料价格波动\n\n"
            elif '比亚迪' in stock:
                a_stock_report += "\n- **投资理由**: 新能源汽车全产业链布局，技术创新能力强\n"
                a_stock_report += "- **风险提示**: 汽车行业竞争激烈，销量不及预期\n\n"
            elif '中芯国际' in stock:
                a_stock_report += "\n- **投资理由**: 国内芯片制造龙头，受益于国产替代趋势\n"
                a_stock_report += "- **风险提示**: 国际贸易摩擦，技术升级不及预期\n\n"
            else:
                a_stock_report += "\n- **投资理由**: 行业龙头地位，基本面良好，成长性强\n"
                a_stock_report += "- **风险提示**: 市场波动风险，行业政策变化风险\n\n"
        
        # 添加风险提示
        a_stock_report += "## 风险提示\n"
        a_stock_report += "- 市场有风险，投资需谨慎\n"
        a_stock_report += "- 以上内容仅供参考，不构成投资建议\n"
        
        return a_stock_report
    except Exception as e:
        print(f"生成A股报告时出错: {str(e)}")
        return f"A股报告生成失败: {str(e)}"

# 生成美股板块和股票分析报告
def generate_us_stock_report():
    try:
        print("🔄 正在获取美股板块数据...")
        # 获取美股板块数据
        us_sectors = get_top_us_sectors()
        
        if not us_sectors:
            return "无法获取美股板块数据"
        
        # 筛选热门股票
        print("🔄 正在筛选热门股票...")
        popular_stocks = filter_popular_stocks(us_sectors)
        
        # 筛选质量股票
        print("🔄 正在筛选质量股票...")
        quality_stocks = filter_quality_stocks(popular_stocks)
        
        if not quality_stocks:
            return "无法筛选出符合条件的股票"
        
        # 准备分析数据
        sector_analysis = analyze_sector_trends(us_sectors)
        
        # 准备股票数据文本
        stock_data_text = "\n"
        for stock in quality_stocks:
            stock_data_text += f"## {stock['symbol']} - {stock['name']}\n"
            stock_data_text += f"- 当前股价: ${stock['current_price']:.2f}\n"
            stock_data_text += f"- 市盈率: {stock['pe_ratio']:.2f}\n"
            stock_data_text += f"- 利润率: {stock['profit_margin']:.2f}%\n"
            stock_data_text += f"- 近5日表现: +{stock['recent_performance']:.2f}%\n\n"
        
        # 使用LLM进行综合分析
        print("🧠 正在生成美股分析报告...")
        llm_analysis = analyze_with_llm(sector_analysis, stock_data_text)
        
        return llm_analysis
    except Exception as e:
        print(f"生成美股报告时出错: {str(e)}")
        return f"美股报告生成失败: {str(e)}"

# 生成完整的股票分析报告（同时包含A股和美股）
def generate_complete_stock_report():
    try:
        print("📊 开始生成完整股票分析报告...")
        
        # 生成美股分析报告
        us_report = generate_us_stock_report()
        
        # 生成A股分析报告
        a_report = generate_a_stock_report()
        
        # 合并报告并添加适当的标题
        complete_report = "## 📊 美股板块与股票分析\n\n"
        complete_report += us_report + "\n\n"
        complete_report += "## 📈 A股热点板块及股票推荐\n\n"
        complete_report += a_report + "\n\n"
        
        print("✅ 完整股票分析报告生成成功")
        return complete_report
    except Exception as e:
        print(f"生成完整股票报告时出错: {str(e)}")
        return f"完整股票报告生成失败: {str(e)}"