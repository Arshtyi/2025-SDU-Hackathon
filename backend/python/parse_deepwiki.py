#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DeepWiki Parser - 解析GitHub仓库的DeepWiki内容
用法: python parse_deepwiki.py <github_url|deepwiki_url>
"""

import sys
import os
import time
import requests
import urllib3
import urllib.parse
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
import re
import json
from requests.adapters import HTTPAdapter
import traceback
import io
import logging
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DeepWikiParser")

# 禁用不安全HTTPS警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DeepWikiParser:
    """DeepWiki解析器类"""
    
    def __init__(self, progress_callback=None):
        """
        初始化解析器
        
        Args:
            progress_callback: 进度回调函数，接受参数 (stage, percentage, message)
                stage: 当前阶段 ("fetch", "parse", "convert")
                percentage: 0-100的进度百分比
                message: 状态消息
        """
        self.session = requests.Session()
        self.session.mount('https://', HTTPAdapter(max_retries=3))
        self.progress_callback = progress_callback
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.code_blocks = {}  # 存储所有提取的代码块
        
    def _report_progress(self, stage, percentage, message):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(stage, percentage, message)
        logger.info(f"{stage} - {percentage}% - {message}")
        
    def github_to_deepwiki_url(self, github_url):
        """将GitHub URL转换为DeepWiki URL"""
        if not github_url:
            return None
        
        # 清理URL
        github_url = github_url.strip()
        if github_url.endswith("/"):
            github_url = github_url[:-1]
            
        # 替换domain
        return github_url.replace("github.com", "deepwiki.com")
    
    def fetch_deepwiki_content(self, url):
        """获取DeepWiki页面内容"""
        try:
            self._report_progress("fetch", 10, f"正在获取页面: {url}")
            response = self.session.get(url, headers=self.headers, verify=False, timeout=30)
            
            if response.status_code != 200:
                self._report_progress("fetch", 0, f"获取页面失败，状态码: {response.status_code}")
                return None
                
            self._report_progress("fetch", 100, "成功获取页面内容")
            return response.content
            
        except Exception as e:
            self._report_progress("fetch", 0, f"获取页面时发生错误: {str(e)}")
            logger.error(f"获取页面失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def parse_html_to_markdown(self, html_content):
        """将HTML内容解析为Markdown"""
        if not html_content:
            return None
            
        self._report_progress("parse", 10, "开始解析HTML内容")
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            self._report_progress("parse", 30, "HTML解析完成，开始提取内容")
            
            # 提取代码块内容供后续使用
            self.code_blocks = self.extract_code_blocks_from_html(html_content)
            
            # 查找主要内容区域
            main_content = soup.select_one('.prose-custom-md')
            
            if not main_content:
                self._report_progress("parse", 0, "找不到主要内容区域")
                return None
                
            self._report_progress("parse", 50, "找到主要内容，开始转换为Markdown")
            
            # 转换为Markdown
            markdown = self._convert_to_markdown(main_content)
            self._report_progress("parse", 100, "Markdown转换完成")
            
            return markdown
            
        except Exception as e:
            self._report_progress("parse", 0, f"解析页面时发生错误: {str(e)}")
            logger.error(f"解析页面失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None
    
    def _convert_to_markdown(self, element):
        """将HTML元素转换为Markdown格式"""
        self._report_progress("convert", 0, "开始HTML转Markdown转换")
        result = io.StringIO()
        
        # 处理元素
        self._process_element(element, result)
        
        self._report_progress("convert", 100, "Markdown转换完成")
        return result.getvalue()
    
    def _process_element(self, element, output, level=0):
        """递归处理HTML元素转换为Markdown"""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            if text:
                output.write(text)
            return
            
        tag_name = element.name if hasattr(element, 'name') else None
        
        # 特殊标签处理
        if tag_name == 'h1':
            output.write('# ')
            for child in element.children:
                if not (hasattr(child, 'name') and child.name == 'button'):
                    self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'h2':
            output.write('## ')
            for child in element.children:
                if not (hasattr(child, 'name') and child.name == 'button'):
                    self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'h3':
            output.write('### ')
            for child in element.children:
                if not (hasattr(child, 'name') and child.name == 'button'):
                    self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'h4':
            output.write('#### ')
            for child in element.children:
                if not (hasattr(child, 'name') and child.name == 'button'):
                    self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'h5':
            output.write('##### ')
            for child in element.children:
                if not (hasattr(child, 'name') and child.name == 'button'):
                    self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'h6':
            output.write('###### ')
            for child in element.children:
                if not (hasattr(child, 'name') and child.name == 'button'):
                    self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'p':
            for child in element.children:
                self._process_element(child, output, level)
            output.write('\n\n')
            
        elif tag_name == 'a':
            href = element.get('href', '#')
            # 获取链接文本
            link_text = []
            for child in element.children:
                if isinstance(child, NavigableString):
                    link_text.append(str(child))
                elif child.name == 'img':
                    # 如果链接内是图片，使用图片的alt文本
                    alt = child.get('alt', '')
                    link_text.append(alt)
                else:
                    # 递归获取其他元素的文本
                    buf = io.StringIO()
                    self._process_element(child, buf, level)
                    link_text.append(buf.getvalue())
                    
            text = ''.join(link_text).strip()
            
            # 如果链接文本为空，尝试使用链接本身
            if not text:
                text = href
                
            output.write(f'[{text}]({href})')
            
        elif tag_name == 'strong' or tag_name == 'b':
            output.write('**')
            for child in element.children:
                self._process_element(child, output, level)
            output.write('**')
            
        elif tag_name == 'em' or tag_name == 'i':
            output.write('*')
            for child in element.children:
                self._process_element(child, output, level)
            output.write('*')
            
        elif tag_name == 'code':
            if element.parent and element.parent.name == 'pre':
                # 这是代码块中的代码，在pre标签处理中进行特殊处理
                # 这里只处理内容，不添加反引号
                for child in element.children:
                    if isinstance(child, NavigableString):
                        # 直接写入文本，保留空白和缩进
                        output.write(str(child))
                    else:
                        self._process_element(child, output, level)
            else:
                # 行内代码
                output.write('`')
                for child in element.children:
                    self._process_element(child, output, level)
                output.write('`')
                
        elif tag_name == 'pre':
            language = ''
            
            # 调试信息
            self._report_progress("convert", 50, f"处理代码块: {element}")
            
            # 更精确地检测代码语言
            if element.get('class'):
                classes = element.get('class')
                for cls in classes:
                    if cls.startswith('language-'):
                        language = cls.replace('language-', '')
                    elif 'hljs' in cls and '-' in cls:
                        # 处理hljs风格的语言类名，如 hljs-python
                        parts = cls.split('-')
                        if len(parts) > 1:
                            language = parts[1]
            
            # 检查是否有code子元素，这是常见的结构
            code_element = element.find('code')
            if code_element:
                # 检查代码元素的类来确定语言
                if code_element.get('class'):
                    for cls in code_element.get('class'):
                        if cls.startswith('language-'):
                            language = cls.replace('language-', '')
                        elif 'hljs' in cls and len(cls.split('-')) > 1:
                            language = cls.split('-')[1]
            
            # 检查是否有特殊标记表示代码块
            placeholder_marker = element.get('data-placeholder')
            has_special_marker = False
            
            # 检查元素内的文本是否包含 $!/$ 标记
            element_text = element.get_text() if element else ""
            # 扩展检测逻辑，支持更多可能的变体格式
            special_markers = ['$!/$', '$!$', '$/$']
            
            # 新策略：如果检测到$!/$标记，则跳过这个元素，不进行处理
            if (placeholder_marker and any(marker in placeholder_marker for marker in special_markers)) or \
               (element_text and any(marker in element_text for marker in special_markers)):
                self._report_progress("convert", 60, "检测到DeepWiki特殊标记，根据新策略跳过处理")
                # 直接返回，不对这种特殊标记内容进行处理
                return
                
                # 首先尝试从预先提取的代码块中查找匹配的内容
                matched_code_block = None
                element_hash = hash(str(element)) % 10000
                
                # 检查所有已提取的代码块，优先使用mermaid类型的代码块
                for key, block in self.code_blocks.items():
                    if ('mermaid' in key or block.get('type') == 'mermaid'):
                        matched_code_block = block
                        self._report_progress("convert", 62, f"找到预先提取的mermaid图表: {key}")
                        break
                
                # 尝试更多策略来提取特殊代码块内容
                mermaid_content = None
                if not matched_code_block:
                    # 首先检查元素内部文本
                    own_text = element.get_text().strip()
                    if own_text:
                        # 检查是否包含mermaid关键词但非常短的文本，如果是则可能是需要替换的标记
                        if len(own_text) < 100 and ('$!/$' in own_text):
                            # 在周围寻找更完整的数据
                            # 优先检查父级元素的数据属性，许多框架使用这种方式存储数据
                            parent_element = element.parent if hasattr(element, 'parent') else None
                            if parent_element:
                                for attr_name, attr_value in parent_element.attrs.items():
                                    if 'data-' in attr_name and isinstance(attr_value, str) and len(attr_value) > 50:
                                        try:
                                            # 尝试解析为JSON
                                            data = json.loads(attr_value)
                                            mermaid_candidates = []
                                            # 递归搜索JSON中的图表内容
                                            self._extract_mermaid_content_from_json(data, mermaid_candidates)
                                            if mermaid_candidates:
                                                mermaid_content = mermaid_candidates[0]
                                                self._report_progress("convert", 65, "从父级元素数据属性中提取到图表内容")
                                        except json.JSONDecodeError:
                                            # 如果不是JSON，检查是否直接包含图表内容
                                            if any(keyword in attr_value.lower() for keyword in ['graph ', 'flowchart ', 'sequencediagram']):
                                                mermaid_content = attr_value
                                                self._report_progress("convert", 65, "从父级元素属性中提取到图表内容")
                                                
                    # 如果还没有找到内容，检查相邻元素
                    if not mermaid_content:
                        # 检查前一个兄弟元素是否包含mermaid内容
                        prev_sibling = element.previous_sibling
                        while prev_sibling and isinstance(prev_sibling, NavigableString) and not prev_sibling.strip():
                            prev_sibling = prev_sibling.previous_sibling
                        
                        if prev_sibling and isinstance(prev_sibling, Tag) and prev_sibling.name == 'p':
                            text_content = prev_sibling.get_text()
                            if text_content and any(keyword in text_content.lower() for keyword in ['graph ', 'flowchart ', 'sequencediagram']):
                                mermaid_content = text_content
                                self._report_progress("convert", 65, "从前一个元素提取到mermaid内容")
                        
                        # 检查后一个兄弟元素
                        next_sibling = element.next_sibling
                        while next_sibling and isinstance(next_sibling, NavigableString) and not next_sibling.strip():
                            next_sibling = next_sibling.next_sibling
                        
                        if next_sibling and isinstance(next_sibling, Tag):
                            text_content = next_sibling.get_text()
                            if text_content and any(keyword in text_content.lower() for keyword in ['graph ', 'flowchart ', 'sequencediagram']):
                                mermaid_content = text_content
                                self._report_progress("convert", 65, "从后一个元素提取到mermaid内容")
                
                # 推断图表类型并创建后备内容
                graph_type = self._detect_mermaid_type(element_text)
                if not graph_type:
                    # 检查周围元素来确定图表类型
                    surrounding_text = ""
                    parent_element = element.parent if hasattr(element, 'parent') else None
                    if parent_element:
                        for sibling in list(parent_element.children)[:10]:
                            if isinstance(sibling, Tag):
                                text = sibling.get_text().lower()
                                surrounding_text += text + " "
                                if "流程图" in text or "flowchart" in text:
                                    graph_type = "flowchart TD"
                                elif "序列图" in text or "sequence" in text:
                                    graph_type = "sequenceDiagram"
                                elif "类图" in text or "class diagram" in text:
                                    graph_type = "classDiagram"
                                elif "甘特图" in text or "gantt" in text:
                                    graph_type = "gantt"
                                elif "饼图" in text or "pie chart" in text:
                                    graph_type = "pie"
                                elif "时间线" in text or "timeline" in text:
                                    graph_type = "timeline"
                
                # 创建后备内容（如果没有找到匹配的内容）
                fallback_content = None
                if not mermaid_content and graph_type:
                    try:
                        fallback_content = f"{graph_type}\n    A[\"请参考原始页面获取完整图表\"] --\u003e B[\"图表内容无法提取\"]"
                        self._report_progress("convert", 67, f"创建了{graph_type}类型的后备图表内容")
                    except Exception as e:
                        self._report_progress("convert", 67, f"创建后备图表内容时出错: {str(e)}")
                
                # 输出代码块，按优先级使用：预提取代码块 > 周围提取内容 > 后备内容 > 提示信息
                code_content = None
                if matched_code_block:
                    code_content = matched_code_block.get('content')
                    language = matched_code_block.get('type', language or 'mermaid')
                elif mermaid_content:
                    code_content = mermaid_content
                    language = language or 'mermaid'
                elif fallback_content:
                    code_content = fallback_content
                    language = 'mermaid'
                
                output.write(f'```{language or "mermaid"}\n')
                
                if code_content:
                    output.write(code_content)
                else:
                    # 尝试提取周围可能的图表说明作为注释
                    description = ""
                    # 确保parent已经被定义
                    parent_element = element.parent if hasattr(element, 'parent') else None
                    if parent_element:
                        for sibling in parent_element.find_all(['p', 'div'], limit=3):
                            if "diagram" in sibling.get_text().lower() or "图表" in sibling.get_text():
                                description = sibling.get_text().strip()
                                break
                    
                    if description:
                        output.write(f"// {description}\n")
                    output.write("// 代码块内容未能提取，可能是动态加载的内容\n")
                    output.write("// 请查看原始页面获取完整代码块\n")
                
                output.write('\n```\n\n')
                return
            
            # 开始代码块
            output.write(f'```{language}\n')
            
            # 处理代码内容
            if code_element:
                try:
                    # 尝试保留原始HTML，这样可以保留格式
                    original_content = str(code_element)
                    # 提取标签之间的内容
                    import re
                    clean_content = re.sub(r'<[^>]*>', '', original_content)
                    # 处理HTML实体
                    import html
                    clean_content = html.unescape(clean_content)
                    # 直接获取原始文本，保留缩进和空白
                    if not clean_content.strip():
                        # 如果上面的方法没有得到内容，尝试直接获取文本
                        clean_content = code_element.get_text()
                    
                    # 删除开头和结尾多余的空行，但保留中间的空行和缩进
                    code_content = clean_content.strip('\n')
                    
                    self._report_progress("convert", 70, f"提取到代码内容，长度：{len(code_content)} 字符")
                    
                    # 写入代码内容
                    output.write(code_content)
                except Exception as e:
                    self._report_progress("convert", 30, f"处理代码内容时出错: {str(e)}")
                    # 回退到基本的文本提取
                    output.write(code_element.get_text().strip('\n'))
            else:
                # 如果没有code子元素，处理所有子元素
                self._report_progress("convert", 40, "找不到code元素，处理所有子元素")
                for child in element.children:
                    self._process_element(child, output, level)
            
            # 结束代码块，确保前后有足够的空行
            output.write('\n```\n\n')
            
        elif tag_name == 'ul':
            output.write('\n')
            for child in element.children:
                if hasattr(child, 'name') and child.name == 'li':
                    output.write('* ')
                    for li_child in child.children:
                        self._process_element(li_child, output, level+1)
                    output.write('\n')
            output.write('\n')
            
        elif tag_name == 'ol':
            output.write('\n')
            for i, child in enumerate(element.find_all('li', recursive=False)):
                output.write(f'{i+1}. ')
                for li_child in child.children:
                    self._process_element(li_child, output, level+1)
                output.write('\n')
            output.write('\n')
            
        elif tag_name == 'li':
            # 只处理直接子元素，避免嵌套列表问题
            for child in element.children:
                self._process_element(child, output, level)
                
        elif tag_name == 'blockquote':
            lines = []
            for child in element.children:
                buf = io.StringIO()
                self._process_element(child, buf, level)
                lines.extend(buf.getvalue().splitlines())
            
            for line in lines:
                if line.strip():
                    output.write(f'> {line}\n')
                else:
                    output.write('>\n')
            output.write('\n')
            
        elif tag_name == 'hr':
            output.write('\n---\n\n')
            
        elif tag_name == 'br':
            output.write('\n')
            
        elif tag_name == 'img':
            alt = element.get('alt', '')
            src = element.get('src', '')
            output.write(f'![{alt}]({src})')
            
        elif tag_name == 'table':
            # 处理表格的转换
            headers = []
            rows = []
            
            # 获取表头
            thead = element.find('thead')
            if thead:
                th_elems = thead.find_all('th')
                for th in th_elems:
                    buf = io.StringIO()
                    self._process_element(th, buf, level)
                    headers.append(buf.getvalue().strip())
            
            # 获取表格内容
            tbody = element.find('tbody')
            if tbody:
                tr_elems = tbody.find_all('tr')
                for tr in tr_elems:
                    row = []
                    td_elems = tr.find_all(['td', 'th'])
                    for td in td_elems:
                        buf = io.StringIO()
                        self._process_element(td, buf, level)
                        row.append(buf.getvalue().strip())
                    rows.append(row)
            
            # 生成Markdown表格
            if headers:
                output.write('| ' + ' | '.join(headers) + ' |\n')
                output.write('| ' + ' | '.join(['---'] * len(headers)) + ' |\n')
                
                for row in rows:
                    # 如果行的列数少于表头，补充空单元格
                    while len(row) < len(headers):
                        row.append('')
                    output.write('| ' + ' | '.join(row) + ' |\n')
                    
                output.write('\n')
        
        # 通用情况：递归处理所有子元素
        elif tag_name not in ['button', 'script', 'style']:
            for child in element.children:
                self._process_element(child, output, level)

    def extract_code_blocks_from_html(self, html_content):
        """从HTML中提取代码块内容"""
        code_blocks = {}
        if not html_content:
            return code_blocks
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取所有包含特殊标记的文本
            special_markers = []
            
            # 更全面地查找包含特殊标记的元素 - 不仅检查element.string，还检查完整的文本内容
            all_elements = soup.find_all(['pre', 'code', 'div', 'p', 'span', 'script'])
            for element in all_elements:
                # 根据新策略，不再收集带有$!/$标记的元素
                # 以下代码被注释掉以实现新策略
                # if '$!/$' in element.get_text():
                #     special_markers.append(element)
                # # 同时检查元素的属性中是否包含特殊标记
                # for attr_name, attr_value in element.attrs.items():
                #     if isinstance(attr_value, str) and '$!/$' in attr_value:
                #         special_markers.append(element)
                #         break
                
                # 记录找到特殊标记但跳过处理
                if '$!/$' in element.get_text() or any(isinstance(attr_value, str) and '$!/$' in attr_value for attr_name, attr_value in element.attrs.items()):
                    self._report_progress("parse", 25, f"发现$!/$ 特殊标记，但根据新策略跳过处理")
            
            self._report_progress("parse", 25, f"找到 {len(special_markers)} 个特殊标记")
            
            # 优先搜索特殊标记附近的真实内容
            # 先检查script元素中是否包含mermaid数据，这些通常是图表的真实数据源
            script_elements = soup.find_all('script')
            mermaid_in_script = []
            
            for script in script_elements:
                script_content = script.string if script.string else ""
                if not script_content:
                    continue
                    
                # 检查脚本内容是否包含mermaid相关关键字
                if any(keyword in script_content.lower() for keyword in 
                       ['mermaid', 'graph ', 'flowchart', 'sequence', 'class diagram']):
                    # 尝试从脚本中提取包含的图表定义
                    try:
                        # 查找常见的图表定义模式
                        patterns = [
                            r'graph\s+[TBLR][TBLRD]\s*[\r\n]{.*?}',
                            r'flowchart\s+[TBLR][TBLRD]\s*[\r\n]{.*?}',
                            r'sequenceDiagram[\r\n]{.*?}',
                            r'classDiagram[\r\n]{.*?}',
                            r'gantt[\r\n]{.*?}',
                            r'pie[\r\n]{.*?}'
                        ]
                        for pattern in patterns:
                            import re
                            matches = re.findall(pattern, script_content, re.DOTALL)
                            for match in matches:
                                self._report_progress("parse", 26, f"从脚本中提取到mermaid内容")
                                mermaid_in_script.append(match)
                    except Exception as e:
                        self._report_progress("parse", 26, f"从脚本提取mermaid内容时出错: {str(e)}")
            
            # 处理每个特殊标记
            for i, marker in enumerate(special_markers):
                parent_elem = marker.parent if hasattr(marker, 'parent') else None
                
                # 确定这个特殊标记对应的真实内容
                code_text = ""
                
                # 先检查元素自身的完整文本内容
                marker_text = marker.get_text()
                
                # 特殊标记的内容往往是尖括号内包含的代码
                # 寻找符合特定模式的mermaid内容
                if '$!/$' in marker_text:
                    # 检查是否有mermaid关键词
                    if any(keyword in marker_text.lower() for keyword in 
                          ['graph ', 'flowchart ', 'sequencediagram', 'classdiagram']):
                        # 如果特殊标记中包含了完整的图表代码，直接使用
                        code_text = marker_text.replace('$!/$', '').strip()
                    else:
                        # 如果只有标记，尝试使用从脚本中提取的内容
                        if mermaid_in_script:
                            code_text = mermaid_in_script[0] if len(mermaid_in_script) == 1 else mermaid_in_script[i % len(mermaid_in_script)]
                
                # 如果标记元素本身没有提供有效内容，检查父元素
                if not code_text or len(code_text) < 20:  # 小于20字符可能是无效内容或仅标记
                    parent_element = marker.parent if hasattr(marker, 'parent') else None
                    if parent_element:
                        # 这可能是一个代码块
                        code_element = parent_element.find('code')
                        if code_element:
                            code_text = code_element.get_text()
                            # 去除特殊标记
                            code_text = code_text.replace('$!/$', '').strip()
                
                # 检查是否获得有效内容，如果不成功，尝试从周围元素或属性查找
                if not code_text or len(code_text) < 20 or not any(keyword in code_text.lower() for keyword in 
                                                             ['graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                                                              'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                                                              'erdiagram', 'journey']):
                    # 查找周围或父级元素的data属性
                    nearby_content = self._find_mermaid_content_nearby(marker)
                    if nearby_content:
                        code_text = nearby_content
                
                # 确定代码块类型
                language = 'text'
                if code_text:
                    code_text_lower = code_text.lower()
                    if 'graph ' in code_text_lower or 'flowchart ' in code_text_lower:
                        language = 'mermaid'
                    elif 'sequencediagram' in code_text_lower:
                        language = 'mermaid'
                    elif 'classdiagram' in code_text_lower:
                        language = 'mermaid'
                    elif 'gantt' in code_text_lower:
                        language = 'mermaid'
                    elif 'pie' in code_text_lower:
                        language = 'mermaid'
                
                # 只有找到有效内容才添加到代码块集合
                if code_text and len(code_text) > 20:
                    key = f"special-code-{i}"
                    code_blocks[key] = {
                        'type': language,
                        'content': code_text
                    }
                    self._report_progress("parse", 26, f"提取到特殊代码块: {key}")
                
            # 尝试提取所有mermaid图表内容
            potential_mermaid = []
            
            # 查找包含mermaid内容的元素
            for tag in ['pre', 'code', 'div', 'p']:
                elements = soup.find_all(tag)
                for element in elements:
                    text = element.get_text()
                    if text and any(keyword in text.lower() for keyword in ['graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 'gantt']):
                        potential_mermaid.append(element)
            
            self._report_progress("parse", 28, f"找到 {len(potential_mermaid)} 个潜在的mermaid图表")
            
            for i, element in enumerate(potential_mermaid):
                text = element.get_text()
                # 提取mermaid内容
                mermaid_content = text
                
                # 识别图表类型
                graph_type = None
                if 'graph ' in text.lower():
                    graph_type = "流程图"
                elif 'flowchart ' in text.lower():
                    graph_type = "流程图"
                elif 'sequencediagram' in text.lower():
                    graph_type = "序列图"
                elif 'classdiagram' in text.lower():
                    graph_type = "类图"
                elif 'gantt' in text.lower():
                    graph_type = "甘特图"
                
                if graph_type:
                    key = f"mermaid-{i}-{hash(mermaid_content) % 10000}"
                    code_blocks[key] = {
                        'type': 'mermaid',
                        'content': mermaid_content,
                        'description': f"{graph_type}图表"
                    }
                    self._report_progress("parse", 28, f"成功提取到特殊代码块: {graph_type}")
            
        except Exception as e:
            self._report_progress("parse", 20, f"提取代码块时出错: {str(e)}")
            logger.error(f"提取代码块时出错: {str(e)}")
            logger.error(traceback.format_exc())
        
        self._report_progress("parse", 45, f"共提取到 {len(code_blocks)} 个代码块")
        return code_blocks
        
    def _extract_mermaid_from_json(self, data, code_blocks, depth=0):
        """递归搜索JSON中的mermaid内容"""
        if depth > 10:  # 限制递归深度
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 20:
                    # 检查字符串是否包含mermaid内容
                    if any(keyword in value.lower() for keyword in [
                        'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                        'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                        'erdiagram', 'journey'
                    ]):
                        # 识别图表类型
                        chart_type = 'mermaid'
                        chart_desc = '图表'
                        
                        if 'graph ' in value.lower() or 'flowchart ' in value.lower():
                            chart_desc = '流程图'
                        elif 'sequencediagram' in value.lower():
                            chart_desc = '序列图'
                        elif 'classdiagram' in value.lower():
                            chart_desc = '类图'
                        elif 'gitgraph' in value.lower():
                            chart_desc = 'Git图'
                        elif 'gantt' in value.lower():
                            chart_desc = '甘特图'
                        elif 'pie ' in value.lower():
                            chart_desc = '饼图'
                        elif 'mindmap' in value.lower():
                            chart_desc = '思维导图'
                        elif 'timeline' in value.lower():
                            chart_desc = '时间线'
                        elif 'erdiagram' in value.lower():
                            chart_desc = '实体关系图'
                        elif 'journey' in value.lower():
                            chart_desc = '用户旅程图'
                            
                        # 保存到代码块字典
                        code_blocks[f"mermaid-json-{key}-{hash(value) % 10000}"] = {
                            'type': chart_type,
                            'content': value,
                            'description': chart_desc
                        }
                        self._report_progress("parse", 38, f"从JSON字段'{key}'中提取到{chart_desc}")
                        
                elif isinstance(value, (dict, list)):
                    self._extract_mermaid_from_json(value, code_blocks, depth + 1)
                    
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._extract_mermaid_from_json(item, code_blocks, depth + 1)
                elif isinstance(item, str) and len(item) > 20:
                    # 检查字符串是否包含mermaid内容
                    if any(keyword in item.lower() for keyword in [
                        'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                        'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                        'erdiagram', 'journey'
                    ]):
                        # 识别图表类型
                        chart_type = 'mermaid'
                        chart_desc = '图表'
                        
                        if 'graph ' in item.lower() or 'flowchart ' in item.lower():
                            chart_desc = '流程图'
                        elif 'sequencediagram' in item.lower():
                            chart_desc = '序列图'
                        elif 'classdiagram' in item.lower():
                            chart_desc = '类图'
                        elif 'gitgraph' in item.lower():
                            chart_desc = 'Git图'
                        elif 'gantt' in item.lower():
                            chart_desc = '甘特图'
                        elif 'pie ' in item.lower():
                            chart_desc = '饼图'
                        elif 'mindmap' in item.lower():
                            chart_desc = '思维导图'
                        elif 'timeline' in item.lower():
                            chart_desc = '时间线'
                        elif 'erdiagram' in item.lower():
                            chart_desc = '实体关系图'
                        elif 'journey' in item.lower():
                            chart_desc = '用户旅程图'
                            
                        # 保存到代码块字典
                        code_blocks[f"mermaid-json-list-{hash(item) % 10000}"] = {
                            'type': chart_type,
                            'content': item,
                            'description': chart_desc
                        }
                        self._report_progress("parse", 38, f"从JSON列表中提取到{chart_desc}")

    def _detect_mermaid_type(self, text):
        """检测Mermaid图表类型"""
        if not text:
            return None
            
        text_lower = text.lower()
        
        if 'graph ' in text_lower:
            direction = 'TD'  # 默认方向
            for dir_type in ['TB', 'TD', 'BT', 'RL', 'LR']:
                if f'graph {dir_type}' in text_lower:
                    direction = dir_type
                    break
            return f"graph {direction}"
            
        if 'flowchart ' in text_lower:
            direction = 'TD'  # 默认方向
            for dir_type in ['TB', 'TD', 'BT', 'RL', 'LR']:
                if f'flowchart {dir_type}' in text_lower:
                    direction = dir_type
                    break
            return f"flowchart {direction}"
            
        if 'sequencediagram' in text_lower:
            return "sequenceDiagram"
            
        if 'classdiagram' in text_lower:
            return "classDiagram"
            
        if 'gantt' in text_lower:
            return "gantt"
            
        if 'pie' in text_lower:
            return "pie"
            
        if 'mindmap' in text_lower:
            return "mindmap"
            
        if 'gitgraph' in text_lower:
            return "gitGraph"
            
        if 'timeline' in text_lower:
            return "timeline"
            
        if 'erdiagram' in text_lower:
            return "erDiagram"
            
        if 'journey' in text_lower:
            return "journey"
            
        return None
        
    def _extract_mermaid_content_from_json(self, data, result_list, depth=0):
        """从JSON中提取mermaid内容，并将结果添加到result_list中"""
        if depth > 10:  # 限制递归深度
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 20:
                    # 检查字符串是否包含mermaid内容
                    if any(keyword in value.lower() for keyword in [
                        'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                        'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                        'erdiagram', 'journey'
                    ]):
                        result_list.append(value)
                        
                elif isinstance(value, (dict, list)):
                    self._extract_mermaid_content_from_json(value, result_list, depth + 1)
                    
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._extract_mermaid_content_from_json(item, result_list, depth + 1)
                elif isinstance(item, str) and len(item) > 20:
                    # 检查字符串是否包含mermaid内容
                    if any(keyword in item.lower() for keyword in [
                        'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                        'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                        'erdiagram', 'journey'
                    ]):
                        result_list.append(item)

    def _find_mermaid_content_nearby(self, marker):
        """
        在特殊标记周围查找mermaid图表内容
        
        Args:
            marker: 包含特殊标记($!/$)的元素
            
        Returns:
            str: 找到的mermaid内容，如果未找到则返回None
        """
        if not marker:
            return None
        
        content = None
        
        # 1. 检查当前元素的data属性
        for attr_name, attr_value in marker.attrs.items():
            if attr_name.startswith('data-') and isinstance(attr_value, str) and len(attr_value) > 20:
                if any(keyword in attr_value.lower() for keyword in [
                    'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                    'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                    'erdiagram', 'journey'
                ]):
                    return attr_value
        
        # 2. 检查父元素
        parent = marker.parent if hasattr(marker, 'parent') else None
        if parent:
            # 检查父元素的data属性
            for attr_name, attr_value in parent.attrs.items():
                if attr_name.startswith('data-') and isinstance(attr_value, str) and len(attr_value) > 20:
                    if any(keyword in attr_value.lower() for keyword in [
                        'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                        'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                        'erdiagram', 'journey'
                    ]):
                        return attr_value
            
            # 检查父元素的子元素中是否有code元素
            code_element = parent.find('code')
            if code_element and code_element != marker:
                code_text = code_element.get_text()
                if len(code_text) > 20 and any(keyword in code_text.lower() for keyword in [
                    'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                    'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                    'erdiagram', 'journey'
                ]):
                    return code_text
        
        # 3. 检查相邻的兄弟元素
        prev_sibling = marker.previous_sibling if hasattr(marker, 'previous_sibling') else None
        next_sibling = marker.next_sibling if hasattr(marker, 'next_sibling') else None
        
        # 检查前一个兄弟元素
        if prev_sibling and hasattr(prev_sibling, 'get_text'):
            text = prev_sibling.get_text()
            if len(text) > 20 and any(keyword in text.lower() for keyword in [
                'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                'erdiagram', 'journey'
            ]):
                return text
        
        # 检查后一个兄弟元素
        if next_sibling and hasattr(next_sibling, 'get_text'):
            text = next_sibling.get_text()
            if len(text) > 20 and any(keyword in text.lower() for keyword in [
                'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                'erdiagram', 'journey'
            ]):
                return text
        
        # 4. 查找附近的隐藏元素，这些元素可能包含原始数据
        if parent:
            hidden_elements = parent.find_all(['div', 'span', 'pre'], style=lambda s: s and 'display:none' in s)
            for hidden in hidden_elements:
                text = hidden.get_text()
                if len(text) > 20 and any(keyword in text.lower() for keyword in [
                    'graph ', 'flowchart ', 'sequencediagram', 'classdiagram', 
                    'gantt', 'pie ', 'mindmap', 'gitgraph', 'timeline', 
                    'erdiagram', 'journey'
                ]):
                    return text
        
        # 5. 查找相关的script元素中的JSON数据
        nearest_json_script = None
        script_elements = marker.find_all_next('script')
        for script in script_elements:
            if script.get('type') in ['application/json', 'text/json']:
                script_content = script.string if script.string else ""
                if script_content and ('graph' in script_content or 'flowchart' in script_content):
                    nearest_json_script = script
                    break
        
        if nearest_json_script:
            try:
                script_content = nearest_json_script.string
                # 尝试解析JSON并提取mermaid内容
                import json
                data = json.loads(script_content)
                # 递归查找JSON结构中的mermaid内容
                content = self._extract_mermaid_from_json(data, {}, 0)
                if content:
                    return content
            except Exception as e:
                self._report_progress("error", 0, f"解析JSON失败: {str(e)}")
        
        return None

def main():
    """命令行入口点"""
    if len(sys.argv) < 2:
        print("用法: python parse_deepwiki.py <github_url|deepwiki_url>")
        return 1
        
    url = sys.argv[1]
    
    # 进度回调函数
    def progress_callback(stage, percentage, message):
        print(f"[{stage}] {percentage}%: {message}")
    
    parser = DeepWikiParser(progress_callback)
    
    # 将GitHub URL转换为DeepWiki URL
    if "github.com" in url:
        url = parser.github_to_deepwiki_url(url)
        print(f"转换为DeepWiki URL: {url}")
    
    # 获取页面内容
    html_content = parser.fetch_deepwiki_content(url)
    if not html_content:
        print("无法获取页面内容")
        return 1
        
    # 解析为Markdown
    try:
        markdown = parser.parse_html_to_markdown(html_content)
        if not markdown:
            print("解析页面失败：未能提取到有效内容")
            return 1
    except Exception as e:
        print(f"解析页面时发生错误: {str(e)}")
        logger.error(f"解析页面时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return 1
        
    # 输出结果
    print("--------- Markdown 内容 ---------")
    if markdown:
        # 使用明确的分隔符格式，确保每一行Markdown都能被完整捕获
        for line in markdown.split('\n'):
            print(line)
    else:
        print("警告: Markdown内容为空")
    print("--------- Markdown 结束 ---------")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
