# sector_stock_analysis.py - 板块追踪和股票推荐功能模块
import yfinance as yf
import random
import os
from openai import OpenAI
import requests
import json

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
        top_3_sectors = sector_list[:3]
        
        if top_3_sectors:
            print(f"✅ 成功获取并筛选出美股前三涨幅板块")
            print(f"📊 前三涨幅板块详情: {top_3_sectors}")  # 调试输出
            return top_3_sectors
        else:
            raise Exception("无法筛选出前三涨幅板块")
                
    except Exception as e:
        print(f"获取美股板块数据失败: {str(e)}")
        # 提供一个模拟的前三板块数据作为备选
        print("📊 使用模拟美股板块数据作为备选")
        return [
            {'name': 'Technology', 'performance': 2.8, 'etf': 'XLK'},
            {'name': 'Healthcare', 'performance': 1.9, 'etf': 'XLV'},
            {'name': 'Energy', 'performance': 1.5, 'etf': 'XLE'}
        ]

# 获取A股板块数据
def get_top_cn_sectors():
    try:
        # A股主要板块及其代表ETF/指数
        sector_indices = {
            '半导体': '512480.SS',      # 半导体ETF
            '新能源': '159806.SZ',      # 新能源ETF
            '医药生物': '512170.SS',    # 医药ETF
            '消费': '159928.SZ',        # 消费ETF
            '金融': '512880.SS',        # 证券ETF
            '科技': '515000.SH',        # 科技ETF
            '军工': '512660.SS',        # 军工ETF
            '光伏': '515790.SH',        # 光伏ETF
            '银行': '512800.SS',        # 银行ETF
            '保险': '512070.SS'         # 保险ETF
        }
        
        sector_list = []
        
        for sector_name, index_symbol in sector_indices.items():
            try:
                # 使用yfinance获取A股ETF数据
                ticker = yf.Ticker(index_symbol)
                hist_data = ticker.history(period="7d")  # 获取7天数据确保有足够的交易日
                
                # 确保有至少3个完整的交易日数据
                if len(hist_data) >= 4:  # 包含4个数据点才能计算3个交易日的涨幅
                    # 获取最近4个交易日的收盘价
                    closes = hist_data['Close'].iloc[-4:]
                    
                    # 计算近3个交易日的累计涨幅
                    start_price = closes.iloc[0]
                    end_price = closes.iloc[-1]
                    
                    if start_price > 0:
                        performance = (end_price - start_price) / start_price * 100
                        sector_list.append({
                            'name': sector_name,
                            'performance': round(performance, 2),
                            'etf': index_symbol
                        })
                else:
                    print(f"A股板块{sector_name}数据不足，无法计算近3个交易日涨幅")
                    # 使用模拟数据作为备选
                    sector_list.append({
                        'name': sector_name,
                        'performance': round(random.uniform(-2, 3), 2),
                        'etf': index_symbol
                    })
                    
            except Exception as etf_e:
                print(f"获取A股板块{sector_name}数据失败: {str(etf_e)}")
                # 如果获取失败，使用随机模拟数据
                sector_list.append({
                    'name': sector_name,
                    'performance': round(random.uniform(-2, 3), 2),
                    'etf': index_symbol
                })
        
        # 按涨幅从高到低排序
        sector_list.sort(key=lambda x: x['performance'], reverse=True)
        
        # 选出涨幅前三的板块
        top_3_sectors = sector_list[:3]
        
        if top_3_sectors:
            print(f"✅ 成功获取并筛选出A股前三涨幅板块")
            print(f"📊 A股前三涨幅板块详情: {top_3_sectors}")
            return top_3_sectors
        else:
            raise Exception("无法筛选出A股前三涨幅板块")
            
    except Exception as e:
        print(f"获取A股板块数据失败: {str(e)}")
        # 提供一个模拟的前三板块数据作为备选
        print("📊 使用模拟A股板块数据作为备选")
        return [
            {'name': '半导体', 'performance': 3.2, 'etf': '512480.SS'},
            {'name': '新能源', 'performance': 2.5, 'etf': '159806.SZ'},
            {'name': '医药生物', 'performance': 1.8, 'etf': '512170.SS'}
        ]

# 获取港股板块数据
def get_top_hk_sectors():
    try:
        # 港股主要板块及其代表ETF/指数
        sector_indices = {
            '科技': '999011.HK',       # 恒生科技指数
            '金融': '999014.HK',       # 恒生金融指数
            '地产': '999012.HK',       # 恒生地产指数
            '医疗': '999013.HK',       # 恒生医疗健康指数
            '消费': '999020.HK',       # 恒生必需性消费指数
            '能源': '999016.HK',       # 恒生能源指数
            '工业': '999017.HK',       # 恒生工业指数
            '电讯': '999015.HK'        # 恒生电讯业指数
        }
        
        sector_list = []
        
        for sector_name, index_symbol in sector_indices.items():
            try:
                # 使用yfinance获取港股指数数据
                ticker = yf.Ticker(index_symbol)
                hist_data = ticker.history(period="7d")  # 获取7天数据确保有足够的交易日
                
                # 确保有至少3个完整的交易日数据
                if len(hist_data) >= 4:  # 包含4个数据点才能计算3个交易日的涨幅
                    # 获取最近4个交易日的收盘价
                    closes = hist_data['Close'].iloc[-4:]
                    
                    # 计算近3个交易日的累计涨幅
                    start_price = closes.iloc[0]
                    end_price = closes.iloc[-1]
                    
                    if start_price > 0:
                        performance = (end_price - start_price) / start_price * 100
                        sector_list.append({
                            'name': sector_name,
                            'performance': round(performance, 2),
                            'etf': index_symbol
                        })
                else:
                    print(f"港股板块{sector_name}数据不足，无法计算近3个交易日涨幅")
                    # 使用模拟数据作为备选
                    sector_list.append({
                        'name': sector_name,
                        'performance': round(random.uniform(-2, 3), 2),
                        'etf': index_symbol
                    })
                    
            except Exception as etf_e:
                print(f"获取港股板块{sector_name}数据失败: {str(etf_e)}")
                # 如果获取失败，使用随机模拟数据
                sector_list.append({
                    'name': sector_name,
                    'performance': round(random.uniform(-2, 3), 2),
                    'etf': index_symbol
                })
        
        # 按涨幅从高到低排序
        sector_list.sort(key=lambda x: x['performance'], reverse=True)
        
        # 选出涨幅前三的板块
        top_3_sectors = sector_list[:3]
        
        if top_3_sectors:
            print(f"✅ 成功获取并筛选出港股前三涨幅板块")
            print(f"📊 港股前三涨幅板块详情: {top_3_sectors}")
            return top_3_sectors
        else:
            raise Exception("无法筛选出港股前三涨幅板块")
            
    except Exception as e:
        print(f"获取港股板块数据失败: {str(e)}")
        # 提供一个模拟的前三板块数据作为备选
        print("📊 使用模拟港股板块数据作为备选")
        return [
            {'name': '科技', 'performance': 2.9, 'etf': '999011.HK'},
            {'name': '医疗', 'performance': 1.7, 'etf': '999013.HK'},
            {'name': '消费', 'performance': 1.4, 'etf': '999020.HK'}
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
def filter_popular_stocks(sector_trends, market='us'):
    # 基于板块趋势和热点，选择一些可能的热门股票
    popular_stocks = {
    # 美股热门股票
    'us': {
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
        'Financial Services': ['JPM', 'BAC', 'GS', 'MS', 'C', 'WFC', 'USB', 'BLK'],
        'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'LLY', 'PDD'],
        'Consumer Cyclical': ['NKE', 'DIS', 'HD', 'MCD', 'SBUX', 'TGT', 'AMZN', 'BKNG'],
        'Industrials': ['BA', 'UNP', 'HON', 'CAT', 'UPS', 'LMT', 'RTX', 'DE'],
        'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'PXD', 'MPC', 'VLO'],
        'Utilities': ['NEE', 'DUK', 'SO', 'EXC', 'D', 'AEP', 'XEL', 'WEC'],
        'Real Estate': ['AMT', 'DLR', 'PLD', 'CCI', 'SPG', 'EQIX', 'PSA', 'O'],
        'Consumer Defensive': ['XLP', 'PG', 'KO', 'PEP', 'WMT', 'COST', 'CL', 'MO'],
        'Materials': ['LIN', 'SHW', 'APD', 'DD', 'PPG', 'FCX', 'NEM', 'IFF'],
        'Communication': ['T', 'VZ', 'CMCSA', 'DIS', 'CHTR', 'NFLX', 'GOOG', 'META']
    },
    # A股热门股票
    'cn': {
        '半导体': ['600703.SS', '300750.SZ', '600460.SS', '002049.SZ', '300661.SZ', '300458.SZ'],
        '新能源': ['002594.SZ', '300750.SZ', '002459.SZ', '300274.SZ', '300014.SZ', '601012.SS'],
        '医药生物': ['600276.SS', '000661.SZ', '300122.SZ', '600518.SS', '002007.SZ', '603259.SS'],
        '消费': ['600519.SS', '000858.SZ', '002304.SZ', '000568.SZ', '603288.SS', '600887.SS'],
        '金融': ['600036.SS', '601318.SS', '600016.SS', '600837.SS', '601166.SS', '601688.SS'],
        '科技': ['000001.SZ', '002415.SZ', '002230.SZ', '002405.SZ', '300308.SZ', '300750.SZ'],
        '军工': ['002025.SZ', '600893.SS', '600501.SS', '600316.SS', '000738.SZ', '002179.SZ'],
        '光伏': ['601012.SS', '300274.SZ', '600206.SS', '300760.SZ', '002459.SZ', '603185.SS']
    },
    # 港股热门股票
    'hk': {
        '科技': ['00700.HK', '09988.HK', '03690.HK', '00981.HK', '00005.HK', '02078.HK'],
        '金融': ['00005.HK', '00939.HK', '02318.HK', '00011.HK', '00941.HK', '01299.HK'],
        '地产': ['00001.HK', '00002.HK', '00003.HK', '00004.HK', '01109.HK', '00688.HK'],
        '医疗': ['02196.HK', '01093.HK', '01877.HK', '02233.HK', '09995.HK', '02858.HK'],
        '消费': ['00728.HK', '00943.HK', '00019.HK', '00291.HK', '01044.HK', '00883.HK']
    }
    }
    
    # 根据板块趋势选择股票
    selected_stocks = []
    if sector_trends:
        # 按涨跌幅排序板块
        sorted_sectors = sorted(sector_trends, key=lambda x: x['performance'], reverse=True)
        
        # 获取对应市场的股票列表
        market_stocks = popular_stocks.get(market, popular_stocks['us'])
        
        # 从表现最好的几个板块中选择股票
        for sector in sorted_sectors[:3]:  # 选择表现最好的3个板块
            sector_name = sector['name']
            if sector_name in market_stocks:
                # 每个板块选择几只股票
                selected_stocks.extend(market_stocks[sector_name][:2])
    
    # 如果没有足够的股票，添加一些默认股票
    if len(selected_stocks) < 10:
        if market == 'cn':
            default_stocks = ['600519.SS', '000858.SZ', '600036.SS', '000333.SZ', '002594.SZ']
        elif market == 'hk':
            default_stocks = ['00700.HK', '00939.HK', '00005.HK', '00001.HK', '02196.HK']
        else:
            default_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        
        for stock in default_stocks:
            if stock not in selected_stocks:
                selected_stocks.append(stock)
            if len(selected_stocks) >= 10:
                break
    
    return selected_stocks

# 筛选盈利状况和技术走势良好的股票
def filter_quality_stocks(stocks, market='us'):
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
            
            # 根据不同市场调整市盈率阈值
            if market == 'cn':
                # A股容忍较高的市盈率
                if pe_ratio <= 0 or pe_ratio > 150:
                    continue
            elif market == 'hk':
                # 港股市盈率阈值
                if pe_ratio <= 0 or pe_ratio > 120:
                    continue
            else:
                # 美股市盈率阈值
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
def analyze_sector_trends(sectors, market='us'):
    if not sectors:
        return "无法获取板块数据"
    
    try:
        # 按表现排序
        sorted_sectors = sorted(sectors, key=lambda x: x['performance'], reverse=True)
        
        # 根据市场确定标题前缀
        market_name = {'us': '美国', 'cn': 'A股', 'hk': '港股'}.get(market, '美国')
        
        # 准备分析文本
        analysis_text = f"# {market_name}板块趋势分析\n\n"
        analysis_text += f"## {market_name}近期表现最佳的板块\n\n"
        
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
def analyze_with_llm(sector_data, stock_data, market='us'):
    # 根据市场确定分析要求
    market_name = {'us': '美国', 'cn': 'A股', 'hk': '港股'}.get(market, '美国')
    
    # 准备提示文本
    prompt = f"""
    请基于以下板块和股票数据，提供专业的金融分析：
    
    ## 板块数据
    {sector_data}
    
    ## 股票数据
    {stock_data}
    
    ## 分析要求
    1. {market_name}近1-2日的热点板块（3个以内），包括板块表现、上涨/下跌原因、投资机会分析
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
            {"role": "system", "content": "你是一位经验丰富的金融分析师，专注于全球股票市场和板块分析。请基于提供的数据，给出专业、客观、深入的分析和建议。特别重要：在进行技术分析,当前股价,推荐个股时，所有数据都要严格以{stock_data}为基准,不能自行修改,估算或使用其他价格来源"},
            {"role": "user", "content": prompt.format(sector_data=sector_data, stock_data=stock_data)}
        ]
    )
    
    return completion.choices[0].message.content.strip()

# 生成单个市场的板块和股票分析报告
def generate_market_report(market='us'):
    try:
        print(f"🔄 正在获取{market}板块数据...")
        
        # 获取对应市场的板块数据
        if market == 'cn':
            sectors = get_top_cn_sectors()
        elif market == 'hk':
            sectors = get_top_hk_sectors()
        else:
            sectors = get_top_us_sectors()
        
        if not sectors:
            return "无法获取板块数据"
        
        # 筛选热门股票
        print(f"🔄 正在筛选{market}热门股票...")
        popular_stocks = filter_popular_stocks(sectors, market)
        
        # 筛选质量股票
        print(f"🔄 正在筛选{market}质量股票...")
        quality_stocks = filter_quality_stocks(popular_stocks, market)
        
        if not quality_stocks:
            return "无法筛选出符合条件的股票"
        
        # 准备分析数据
        sector_analysis = analyze_sector_trends(sectors, market)
        
        # 准备股票数据文本
        stock_data_text = "\n"
        for stock in quality_stocks:
            stock_data_text += f"## {stock['symbol']} - {stock['name']}\n"
            # 根据市场确定货币符号
            currency = '¥' if market in ['cn', 'hk'] else '$'
            stock_data_text += f"- 当前股价: {currency}{stock['current_price']:.2f}\n"
            stock_data_text += f"- 市盈率: {stock['pe_ratio']:.2f}\n"
            stock_data_text += f"- 利润率: {stock['profit_margin']:.2f}%\n"
            stock_data_text += f"- 近5日表现: +{stock['recent_performance']:.2f}%\n\n"
        
        # 使用LLM进行综合分析
        print(f"🧠 正在生成{market}股票分析报告...")
        llm_analysis = analyze_with_llm(sector_analysis, stock_data_text, market)
        
        return llm_analysis
    except Exception as e:
        print(f"生成{market}股票报告时出错: {str(e)}")
        return f"股票报告生成失败: {str(e)}"

# 生成板块和股票分析报告（主函数，生成三个市场的报告）
def generate_stock_report():
    try:
        # 生成三个市场的报告
        us_report = generate_market_report('us')
        cn_report = generate_market_report('cn')
        hk_report = generate_market_report('hk')
        
        # 组合三个市场的报告，使用特殊分隔符以便在HTML生成时能够正确分割
        combined_report = f"""
## 📊 美股板块与股票分析

{us_report}

---

## 📊 A股板块与股票分析

{cn_report}

---

## 📊 港股板块与股票分析

{hk_report}
        """
        
        return combined_report
    except Exception as e:
        print(f"生成综合股票报告时出错: {str(e)}")
        return f"股票报告生成失败: {str(e)}"