# important_events_tracking.py - 重要事件追踪功能模块
import os
import json
from datetime import datetime, timedelta
import pytz
import openai
from openai import OpenAI

# 获取北京时间
def get_beijing_time():
    return datetime.now(pytz.timezone("Asia/Shanghai"))

# 获取未来一个月的重点会议信息
def get_important_meetings():
    """
    使用LLM获取未来一个月重要的美国和中国经济政策会议信息
    """
    try:
        print("🔄 正在使用LLM获取重要会议信息...")
        current_time = get_beijing_time()
        one_month_later = current_time + timedelta(days=30)
        
        # 获取API密钥 - 使用阿里千问模型
        print("📋 检查环境变量配置...")
        
        # 只使用阿里千问模型
        ai_service = "alimind"
        api_key = os.environ.get("ALI_MIND_API_KEY")
        print(f"  ALI_MIND_API_KEY: {'已设置 (长度: ' + str(len(api_key)) + ')' if api_key else '未设置'}")
        
        if not api_key:
            raise ValueError("环境变量 ALI_MIND_API_KEY 未设置!")
            
        api_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        model_name = "qwen-turbo"
        
        print(f"  API服务配置: 服务={ai_service}, 模型={model_name}, 基础URL={api_base_url}")
        
        # 初始化OpenAI客户端
        print("🔄 初始化OpenAI客户端...")
        client = OpenAI(api_key=api_key, base_url=api_base_url)
        print("✅ 客户端初始化完成")
        
        # 构建提示词
        current_date = current_time.strftime("%Y-%m-%d")
        one_month_date = one_month_later.strftime("%Y-%m-%d")
        
        prompt = f"""请列出从{current_date}到{one_month_date}期间，美国和中国重要的经济和政策会议及数据发布时间。

要求：
1. 包含美联储FOMC会议、美国非农就业数据、CPI数据等重要经济指标发布时间
2. 包含中国人民银行会议、中国重要经济数据(CPI、GDP等)发布时间
3. 按照重要性分为"高"、"中高"两个级别
4. 按照类别分为"国内政策"、"国际政策"、"经济数据"三个类别
5. 返回JSON格式数据，包含以下字段：
   - date: 日期(YYYY-MM-DD格式)
   - title: 会议/数据发布标题
   - description: 详细描述
   - importance: 重要性级别("高"或"中高")
   - category: 类别("国内政策"、"国际政策"或"经济数据")

请确保数据准确且时间合理，返回纯JSON格式，不要添加其他解释文字。"""
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的金融分析师，熟悉中美两国的经济政策会议和数据发布时间表。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # 解析响应，增强错误处理
        content = response.choices[0].message.content.strip()
        
        # 打印完整响应内容用于调试
        print(f"完整响应内容:\n{content}")
        
        # 尝试提取JSON部分
        try:
            # 方法1: 清理内容并尝试直接解析
            # 移除可能的Markdown代码块标记
            clean_content = content.replace('```json', '').replace('```', '').strip()
            
            # 尝试直接解析
            try:
                meetings = json.loads(clean_content)
                print(f"✅ 成功获取会议信息")
                return format_meetings_markdown(meetings, current_time)
            except json.JSONDecodeError as e:
                print(f"⚠️ 直接JSON解析失败: {str(e)}")
            
            # 方法2: 智能提取JSON数组
            try:
                import re
                # 查找JSON数组的开始和结束位置
                if '[' in clean_content and ']' in clean_content:
                    # 找到第一个[和最后一个]，确保包含整个数组
                    start_idx = clean_content.find('[')
                    end_idx = clean_content.rfind(']') + 1
                    array_content = clean_content[start_idx:end_idx]
                    print(f"📋 提取JSON数组内容: {array_content[:100]}...")
                    
                    try:
                        meetings = json.loads(array_content)
                        print(f"✅ 成功解析JSON数组")
                        return format_meetings_markdown(meetings, current_time)
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON数组解析失败: {str(e)}")
                else:
                    print("⚠️ 未找到JSON数组标记")
            except Exception as inner_e:
                print(f"❌ 数组提取失败: {str(inner_e)}")
            
            # 方法3: 针对多行JSON对象的特殊处理
            try:
                print("🔄 尝试处理多行JSON对象...")
                
                # 按行分割内容
                lines = clean_content.split('\n')
                
                # 检查是否有多个JSON对象（如错误信息所示）
                if len(lines) > 1:
                    # 尝试手动构建JSON数组
                    json_objects = []
                    current_object_lines = []
                    brace_count = 0
                    
                    for line in lines:
                        stripped_line = line.strip()
                        if not stripped_line:  # 跳过空行
                            continue
                        
                        # 跟踪花括号数量以识别完整的JSON对象
                        current_object_lines.append(line)
                        brace_count += stripped_line.count('{') - stripped_line.count('}')
                        
                        # 当花括号平衡时，尝试解析当前对象
                        if brace_count == 0 and current_object_lines:
                            try:
                                object_str = '\n'.join(current_object_lines)
                                # 移除可能的逗号
                                object_str = object_str.rstrip(',')
                                json_obj = json.loads(object_str)
                                json_objects.append(json_obj)
                                current_object_lines = []
                                print(f"✅ 成功解析单个JSON对象: {json_obj.get('title', '')}")
                            except json.JSONDecodeError:
                                # 如果解析失败，继续累积行
                                pass
                    
                    # 如果成功解析了多个对象
                    if json_objects:
                        print(f"✅ 成功构建包含{len(json_objects)}个对象的数组")
                        return format_meetings_markdown(json_objects, current_time)
            except Exception as inner_e:
                print(f"❌ 多行JSON处理失败: {str(inner_e)}")
            
            # 方法4: 正则表达式提取单个JSON对象
            try:
                import re
                # 尝试匹配JSON对象
                json_pattern = r'\{[^}]*\}'
                matches = re.findall(json_pattern, clean_content, re.DOTALL)
                
                if matches:
                    json_objects = []
                    for match in matches:
                        try:
                            # 修复可能的格式问题
                            fixed_match = match.replace('\n', ' ').strip()
                            json_obj = json.loads(fixed_match)
                            json_objects.append(json_obj)
                        except json.JSONDecodeError:
                            continue
                    
                    if json_objects:
                        print(f"✅ 通过正则表达式提取了{len(json_objects)}个JSON对象")
                        return format_meetings_markdown(json_objects, current_time)
            except Exception as inner_e:
                print(f"❌ 正则提取对象失败: {str(inner_e)}")
            
            # 方法5: 最后的兜底方案 - 尝试直接从响应中提取结构化数据
            try:
                print("🔄 尝试从响应中提取结构化数据...")
                # 分割每一行，尝试提取键值对
                meetings_data = []
                current_meeting = {}
                
                for line in lines:
                    stripped_line = line.strip()
                    # 检查是否是新对象的开始
                    if stripped_line.startswith('{'):
                        current_meeting = {}
                    # 检查键值对格式
                    elif ':' in stripped_line and not stripped_line.startswith('//'):
                        try:
                            # 简单的键值对提取
                            key_part, value_part = stripped_line.split(':', 1)
                            key = key_part.strip().strip('"').strip("'")
                            # 清理值
                            value = value_part.strip().strip(',').strip('"').strip("'")
                            current_meeting[key] = value
                        except Exception:
                            pass
                    # 检查对象结束
                    elif stripped_line.endswith('}'):
                        if current_meeting:  # 只有当有数据时才添加
                            meetings_data.append(current_meeting)
                            current_meeting = {}
                
                if meetings_data:
                    print(f"✅ 成功提取了{len(meetings_data)}个会议数据")
                    return format_meetings_markdown(meetings_data, current_time)
            except Exception as inner_e:
                print(f"❌ 结构化数据提取失败: {str(inner_e)}")
            
            # 所有尝试都失败，抛出异常
            raise ValueError(f"无法解析LLM响应内容，已尝试多种解析方法")
        except Exception as e:
            print(f"❌ 解析响应内容失败: {str(e)}")
            raise
        
    except Exception as e:
        print(f"❌ 使用LLM获取会议信息失败: {str(e)}")
        # 返回包含错误信息的基本报告
        error_report = "# 📅 未来一个月重要经济与政策会议\n\n"
        error_report += f"*数据更新时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        error_report += "### 📝 数据获取失败\n\n"
        error_report += f"- 原因: {str(e)}\n"
        error_report += "- 请检查API密钥配置或网络连接\n"
        return error_report

def format_meetings_markdown(meetings, current_time):
    """
    将会议数据格式化为Markdown格式
    """
    try:
        # 检查meetings的类型并转换为列表格式
        if isinstance(meetings, dict):
            # 如果是字典格式，尝试提取其中的列表数据
            # 查找可能包含会议列表的键
            list_keys = [key for key in meetings.keys() if isinstance(meetings[key], list)]
            if list_keys:
                # 使用第一个找到的列表
                meetings_list = meetings[list_keys[0]]
                print(f"🔄 数据格式调整：从字典中提取列表数据（键: {list_keys[0]}）")
            else:
                # 如果字典中没有列表，尝试将字典本身作为单个会议项
                meetings_list = [meetings]
                print("🔄 数据格式调整：将字典转换为单元素列表")
        elif isinstance(meetings, list):
            meetings_list = meetings
        else:
            raise TypeError(f"不支持的数据类型: {type(meetings)}")
        
        # 按日期排序会议（如果有date字段）
        if meetings_list and "date" in meetings_list[0]:
            meetings_list.sort(key=lambda x: x["date"])
        
        # 生成Markdown格式的会议列表
        markdown_content = "# 📅 未来一个月重要经济与政策会议\n\n"
        markdown_content += f"*数据更新时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        
        # 按类别分组显示会议
        categories = {"国内政策": [], "国际政策": [], "经济数据": []}
        
        for meeting in meetings_list:
            # 检查是否有必要的字段
            if not all(key in meeting for key in ["title", "description"]):
                # 如果缺少必要字段，尝试使用默认值或跳过
                if "title" not in meeting:
                    meeting["title"] = "未命名会议"
                if "description" not in meeting:
                    meeting["description"] = "无描述"
                if "importance" not in meeting:
                    meeting["importance"] = "中高"
                if "category" not in meeting:
                    meeting["category"] = "经济数据"
            
            category = meeting["category"]
            if category in categories:
                categories[category].append(meeting)
            else:
                # 对于未识别的类别，默认归类为经济数据
                categories["经济数据"].append(meeting)
        
        # 为每个类别生成内容
        has_content = False
        for category_name, category_meetings in categories.items():
            if category_meetings:
                has_content = True
                markdown_content += f"## {category_name}\n\n"
                for meeting in category_meetings:
                    # 根据重要性添加标记
                    importance_marker = "🔴 " if meeting["importance"] == "高" else "🟠 "
                    # 确保date字段存在
                    date = meeting.get("date", "日期未知")
                    markdown_content += f"### {importance_marker}{date} - {meeting['title']}\n"
                    markdown_content += f"- **重要性**: {meeting['importance']}\n"
                    markdown_content += f"- **描述**: {meeting['description']}\n\n"
        
        if not has_content:
            markdown_content += "### 📝 暂无会议数据\n\n"
            markdown_content += "- 当前暂无可用的会议数据或数据格式不兼容\n"
        
        print(f"✅ 重要会议信息获取成功，共{len(meetings_list)}个会议")
        return markdown_content
    except Exception as e:
        print(f"❌ 格式化会议信息失败: {str(e)}")
        return "# 📅 未来一个月重要经济与政策会议\n\n格式化会议信息失败: " + str(e)

# 生成完整的事件追踪报告
def generate_events_tracking_report():
    """
    生成包含重要会议信息的完整报告
    """
    try:
        print("🔄 正在生成事件追踪报告...")
        
        # 获取重要会议信息
        meetings_report = get_important_meetings()
        
        # 生成报告
        full_report = f"## 📊 重要事件追踪\n\n"
        full_report += meetings_report
        
        print("✅ 事件追踪报告生成成功")
        return full_report
    except Exception as e:
        print(f"❌ 生成事件追踪报告失败: {str(e)}")
        return "## 📊 重要事件追踪\n\n生成报告失败，请稍后重试。"




if __name__ == "__main__":
    # 执行测试
    print("=== 运行重要事件追踪测试 ===")
    try:
        # 生成并显示事件追踪报告
        report = generate_events_tracking_report()
        print(report[:500] + "..." if len(report) > 500 else report)
    except Exception as e:
        print(f"测试执行失败: {str(e)}")
