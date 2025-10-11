# sector_stock_analysis.py - 板块追踪和股票推荐功能模块
import yfinance as yf
import random
import os
from openai import OpenAI
import json

# 全局变量存储股票数据
stock_data = None

# 加载股票数据

def load_stock_data():
    global stock_data
    try:
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'stock_data.json')
        
        with open(json_path, 'r', encoding='utf-8') as f:
            stock_data = json.load(f)
        
        # 计算总股票数量
        total_stocks = 0
        for sector_data in stock_data.get('popular_stocks_by_sector', {}).values():
            total_stocks += len(sector_data.get('stocks', []))
        
        print(f"✅ 成功加载股票数据，共{total_stocks}只股票")
        return stock_data
    except Exception as e:
        print(f"❌ 加载股票数据失败: {str(e)}")
        # 如果加载失败，返回空数据结构
        return {
            'popular_stocks_by_sector': {},
            'a_stock_sectors': {},
            'us_stock_sectors': {},
            'us_popular_stocks_by_sector': {}
        }

# 初始化时加载股票数据
stock_data = load_stock_data()

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
        
        print("🔄 正在获取美股板块实际ETF数据...")
        # 直接从stock_data获取美股板块数据，无需默认值（因为JSON文件中已定义）
        sector_etfs = stock_data['us_stock_sectors']
        
        sector_list = []
        success_count = 0
        
        for sector_name, etf_symbol in sector_etfs.items():
            try:
                print(f"   获取 {sector_name} ({etf_symbol}) 数据...")
                # 使用yfinance获取ETF数据
                ticker = yf.Ticker(etf_symbol)
                hist_data = ticker.history(period="7d")  # 获取7天数据
                
                # 确保有足够的数据进行计算
                if not hist_data.empty and len(hist_data) >= 4:
                    # 获取最近4个交易日的收盘价（计算3个交易日的变化）
                    closes = hist_data['Close'].iloc[-4:]
                    
                    # 计算近3个交易日的累计涨幅
                    start_price = closes.iloc[0]
                    end_price = closes.iloc[-1]
                    
                    if start_price > 0:
                        performance = (end_price - start_price) / start_price * 100
                        
                        # 计算单日涨幅
                        daily_change = (end_price - closes.iloc[-2]) / closes.iloc[-2] * 100
                        
                        sector_info = {
                            'name': sector_name,
                            'performance': round(performance, 2),  # 近3个交易日涨幅
                            'daily_change': round(daily_change, 2),
                            'current_price': round(end_price, 2),
                            'etf': etf_symbol,
                            'data_date': hist_data.index[-1].strftime('%Y-%m-%d')
                        }
                        sector_list.append(sector_info)
                        success_count += 1
                        print(f"   ✓ 成功: 3日涨幅 {performance:.2f}%, 单日涨幅 {daily_change:.2f}%")
                    else:
                        print(f"   ✗ 错误: 起始价格为0，无法计算涨幅")
                else:
                    print(f"   ✗ 错误: 未获取到有效数据或数据不足（需要至少4个交易日数据）")
                    # 不再使用随机数据，只有获取到真实数据的板块才会被添加
                    
            except Exception as etf_e:
                print(f"   ✗ 错误: 获取板块{sector_name}数据失败: {str(etf_e)}")
                # 不再使用随机数据替代
        
        # 按涨幅从高到低排序
        sector_list.sort(key=lambda x: x['performance'], reverse=True)
        
        print(f"\n✅ 成功获取 {success_count}/{len(sector_etfs)} 个美股板块的数据")
        
        # 选出涨幅前三的板块
        top_4_sectors = sector_list[:4]
        
        if top_4_sectors:
            print(f"✅ 成功筛选出前四涨幅板块")
            print(f"📊 前四涨幅板块详情: {top_4_sectors}")  # 调试输出
            return top_4_sectors
        else:
            # 如果没有足够的板块数据，抛出异常而不是使用模拟数据
            raise Exception("无法筛选出前四涨幅板块，获取到的有效板块数据不足")
            
    except Exception as e:
        print(f"获取美股板块数据失败: {str(e)}")
        # 在生产环境中，可能需要返回一个空列表或抛出异常
        # 这里为了保持兼容性，返回空列表，但实际应用中应该处理这种情况
        return []

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
    # 确保股票数据已加载
    global stock_data
    if stock_data is None:
        load_stock_data()
    
    # 从已加载的stock_data中获取美股热门股票数据，参考stock_code_mapping的访问方式
    popular_stocks = stock_data.get('us_popular_stocks_by_sector', {})
    
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

# 筛选A股质量股票
def filter_quality_a_stocks(stocks):
    quality_stocks = []
    
    for stock in stocks:
        try:
            # 判断传入的是股票代码还是股票名称
            # 如果已经包含交易所后缀，则直接使用
            if any(suffix in stock for suffix in ['.SS', '.SZ', '.HK']):
                stock_code = stock
                # 尝试从代码映射表中反查股票名称
                stock_name = stock
                # 创建一个反向映射表，从代码到名称
                code_to_name = {code: name for name, code in get_a_stock_code.__globals__.get('stock_mapping', {}).items()}
                if stock_code in code_to_name:
                    stock_name = code_to_name[stock_code]
            else:
                # 如果是股票名称，使用get_a_stock_code函数获取正确的代码
                stock_name = stock
                stock_code = get_a_stock_code(stock_name)
                
                # 如果无法获取代码，跳过或使用备用逻辑
                if not stock_code:
                    print(f"警告: 无法获取 {stock_name} 的股票代码")
                    continue
            
            # 使用get_stock_data函数获取A股数据
            stock_data = get_stock_data(stock_code)
            
            if not stock_data:
                continue
            
            # 检查数据是否完整
            if not all([stock_data['profile'], stock_data['metrics'], stock_data['candles']]):
                continue
            
            # 筛选条件1: 有正的盈利
            metrics = stock_data['metrics'].get('metric', {})
            # 尝试不同的市盈率字段名称
            pe_ratio = metrics.get('peNormalizedAnnual', 0)
            if pe_ratio == 0:
                pe_ratio = metrics.get('peRatio', 0)
            
            # 尝试不同的利润率字段名称
            profit_margin = metrics.get('profitMargin', 0)
            
            # 尝试不同的价格字段名称
            current_price = metrics.get('price', 0)
            if current_price == 0:
                current_price = metrics.get('regularMarketPrice', 0)
                if current_price == 0:
                    current_price = metrics.get('lastPrice', 0)
            
            # 避免负的市盈率，放宽上限以适应A股特点
            # 不强制要求PE < 300，可以有一定弹性
            if pe_ratio <= 0 and pe_ratio != 0:  # 只排除负市盈率，0值保留
                continue
            
            # 不强制要求利润率数据，允许缺失
            
            # 获取近期表现数据，使用更长的周期（如5天）
            candles = stock_data['candles']
            if 'c' in candles and len(candles['c']) >= 5:
                # 使用5天周期计算近期表现
                close_prices = candles['c']
                # 计算整体涨幅百分比
                recent_performance = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100
                
                # 构建股票信息字典
                stock_info = {
                    'symbol': stock_code,
                    'name': stock_name,
                    'pe_ratio': pe_ratio if pe_ratio > 0 else None,  # 只记录有效的PE值
                    'profit_margin': profit_margin if profit_margin > 0 else None,  # 只记录有效的利润率
                    'current_price': current_price,
                    'recent_performance': recent_performance
                }
                
                # 无论趋势如何，只要有价格数据就添加，后面再排序
                quality_stocks.append(stock_info)
            elif 'c' in candles and len(candles['c']) > 0:
                # 至少有收盘价数据，也添加进来
                close_prices = candles['c']
                recent_performance = (close_prices[-1] - close_prices[0]) / close_prices[0] * 100 if len(close_prices) > 1 else 0
                
                stock_info = {
                    'symbol': stock_code,
                    'name': stock_name,
                    'pe_ratio': pe_ratio if pe_ratio > 0 else None,
                    'profit_margin': profit_margin if profit_margin > 0 else None,
                    'current_price': current_price,
                    'recent_performance': recent_performance
                }
                
                quality_stocks.append(stock_info)
        except Exception as e:
            print(f"处理A股 {stock} 时出错: {str(e)}")
            continue
    
    # 按近期表现排序
    quality_stocks.sort(key=lambda x: x['recent_performance'], reverse=True)
    
    return quality_stocks[:8]  # 返回前8只股票

# 筛选美股质量股票
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
    
    return quality_stocks[:8]  # 返回前8只股票

# 分析板块趋势
def analyze_sector_trends(sectors):
    if not sectors:
        return "无法获取板块数据"
    
    try:
        # 按表现排序
        sorted_sectors = sorted(sectors, key=lambda x: x['performance'], reverse=True)
        
        # 准备分析文本，包含详细的板块数据
        analysis_text = "# 板块趋势分析\n\n"
        analysis_text += "## 最近一日涨幅和最近三日整体涨幅\n\n"
        
        # 分析前4个表现最好的板块，包含详细数据
        for i, sector in enumerate(sorted_sectors[:4]):
            sector_name = sector['name']
            performance = sector['performance']  # 近3个交易日涨幅
            daily_change = sector.get('daily_change', 'N/A')  # 单日涨幅
            current_price = sector.get('current_price', 'N/A')
            etf = sector.get('etf', 'N/A')
            data_date = sector.get('data_date', 'N/A')
            
            analysis_text += f"### {i+1}. {sector_name} (最近一日涨幅: {daily_change:+.2f}%, 最近三日整体涨幅: {performance:+.2f}%)\n\n"
            analysis_text += f"- **最近三日整体涨幅**: +{performance:.2f}%\n"
            analysis_text += f"- **最近一日涨幅**: {daily_change:+.2f}%\n" if isinstance(daily_change, (int, float)) else f"- **最近一日涨幅**: {daily_change}\n"
            analysis_text += f"- **当前价格**: ¥{current_price:.2f}\n" if isinstance(current_price, (int, float)) else f"- **当前价格**: {current_price}\n"
            analysis_text += f"- **ETF代码**: {etf}\n"
            analysis_text += f"- **数据日期**: {data_date}\n"
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
    1. 近1-2日的热点板块（4个以内），包括板块表现、上涨/下跌原因、投资机会分析
    2. 根据提供的股票数据，推荐8只最具投资价值的股票，每只股票需包含：
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
        print("🔄 正在获取A股板块实际ETF数据...")
        # 直接从stock_data获取A股板块数据，无需默认值（因为JSON文件中已定义）
        sector_etfs = stock_data['a_stock_sectors']
        
        sector_list = []
        success_count = 0
        
        for sector_name, etf_symbol in sector_etfs.items():
            try:
                print(f"   获取 {sector_name} ({etf_symbol}) 数据...")
                # 使用yfinance获取ETF数据
                ticker = yf.Ticker(etf_symbol)
                hist_data = ticker.history(period="7d")  # 获取7天数据
                
                # 确保有足够的数据进行计算
                if not hist_data.empty and len(hist_data) >= 4:
                    # 获取最近4个交易日的收盘价（计算3个交易日的变化）
                    closes = hist_data['Close'].iloc[-4:]
                    
                    # 计算近3个交易日的累计涨幅
                    start_price = closes.iloc[0]
                    end_price = closes.iloc[-1]
                    
                    if start_price > 0:
                        performance = (end_price - start_price) / start_price * 100
                        
                        # 计算单日涨幅
                        daily_change = (end_price - closes.iloc[-2]) / closes.iloc[-2] * 100
                        
                        sector_info = {
                            'name': sector_name,
                            'performance': round(performance, 2),  # 近3个交易日涨幅
                            'daily_change': round(daily_change, 2),
                            'current_price': round(end_price, 2),
                            'etf': etf_symbol,
                            'data_date': hist_data.index[-1].strftime('%Y-%m-%d')
                        }
                        sector_list.append(sector_info)
                        success_count += 1
                        print(f"   ✓ 成功: 3日涨幅 {performance:.2f}%, 单日涨幅 {daily_change:.2f}%")
                    else:
                        print(f"   ✗ 错误: 起始价格为0，无法计算涨幅")
                else:
                    print(f"   ✗ 错误: 未获取到有效数据或数据不足（需要至少4个交易日数据）")
                    # 不再使用随机数据
                    
            except Exception as etf_e:
                print(f"   ✗ 错误: 获取板块{sector_name}数据失败: {str(etf_e)}")
                # 不再使用随机数据替代
        
        # 按涨幅从高到低排序
        sector_list.sort(key=lambda x: x['performance'], reverse=True)
        
        print(f"\n✅ 成功获取 {success_count}/{len(sector_etfs)} 个A股板块的数据")
        
        # 选出涨幅前三的板块
        top_4_sectors = sector_list[:4]
        
        if top_4_sectors:
            print(f"✅ 成功筛选出前四涨幅A股板块")
            print(f"📊 前四涨幅板块详情: {top_4_sectors}")  # 调试输出
            return top_4_sectors
        else:
            # 如果没有足够的板块数据，抛出异常而不是使用模拟数据
            raise Exception("无法筛选出前四涨幅A股板块，获取到的有效板块数据不足")
            
    except Exception as e:
        print(f"获取A股板块数据失败: {str(e)}")
        # 在生产环境中，可能需要返回一个空列表或抛出异常
        # 这里为了保持兼容性，返回空列表，但实际应用中应该处理这种情况
        return []

# 智能获取A股股票代码
def get_a_stock_code(stock_name):
    """
    根据股票名称获取对应的A股代码（含交易所后缀）
    从popular_stocks_by_sector中查找代码，不再使用单独的stock_code_mapping
    """
    global stock_data
    # 确保股票数据已加载
    if stock_data is None:
        load_stock_data()
    
    # 遍历所有板块查找股票代码
    for sector, sector_data in stock_data.get('popular_stocks_by_sector', {}).items():
        for stock in sector_data.get('stocks', []):
            if stock.get('name') == stock_name:
                return stock.get('code')
    
    # 如果找不到，返回None
    return None

# 筛选热门A股
def filter_popular_a_stocks(sector_trends):
    """
    基于板块趋势和热点，选择热门A股
    """
    global stock_data
    # 确保股票数据已加载
    if stock_data is None:
        load_stock_data()
    
    # 从JSON数据中获取按板块分类的热门股票
    popular_stocks = stock_data['popular_stocks_by_sector']
    
    # 根据板块趋势选择股票
    selected_stocks = []
    if sector_trends:
        # 按涨跌幅排序板块
        sorted_sectors = sorted(sector_trends, key=lambda x: x['performance'], reverse=True)
        
        # 从表现最好的几个板块中选择股票
        for sector in sorted_sectors[:4]:  # 选择表现最好的4个板块
            sector_name = sector['name']
            if sector_name in popular_stocks:
                # 每个板块选择2只股票，并直接从新结构获取代码
                for stock in popular_stocks[sector_name].get('stocks', [])[:2]:
                    stock_name = stock.get('name')
                    stock_code = stock.get('code')
                    if stock_code:
                        selected_stocks.append(stock_code)
                    else:
                        print(f"警告: 无法获取 {stock_name} 的股票代码")
                        # 如果无法获取代码，仍然添加股票名称作为备选
                        selected_stocks.append(stock_name)
    
    # 如果没有足够的股票，添加一些默认股票
    if len(selected_stocks) < 8:  # 调整目标数量为8
        default_stocks = ['贵州茅台', '宁德时代', '比亚迪', '中芯国际', '招商银行', '恒瑞医药', '隆基绿能', '韦尔股份']  # 增加默认股票数量
        for stock_name in default_stocks:
            # 检查是否已存在
            if stock_name not in selected_stocks:
                # 尝试获取股票代码
                stock_code = get_a_stock_code(stock_name)
                if stock_code:
                    selected_stocks.append(stock_code)
                else:
                    selected_stocks.append(stock_name)
                
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

         # 筛选质量股票
        print("🔄 正在筛选质量股票...")
        quality_a_stocks = filter_quality_a_stocks(popular_a_stocks)
        
        # 准备分析数据
        sector_analysis = analyze_sector_trends(a_sectors)
        
        # 准备股票数据文本
        stock_data_text = "\n"
        for stock in quality_a_stocks:  
            stock_data_text += f"## {stock['symbol']} - {stock['name']}\n"
            stock_data_text += f"- 当前股价: ¥{stock['current_price']:.2f}\n"
            stock_data_text += f"- 市盈率: {stock['pe_ratio']:.2f}\n"
            stock_data_text += f"- 利润率: {stock['profit_margin']:.2f}%\n"
            stock_data_text += f"- 近5日表现: {stock['recent_performance']:+.2f}%\n\n"
        
        # 使用LLM进行综合分析
        print("🧠 正在生成A股分析报告...")
        llm_analysis = analyze_with_llm(sector_analysis, stock_data_text)
        
        return llm_analysis
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