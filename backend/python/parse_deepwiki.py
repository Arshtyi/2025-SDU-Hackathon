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
                # 这是代码块中的代码，不需要特殊处理
                for child in element.children:
                    self._process_element(child, output, level)
            else:
                # 行内代码
                output.write('`')
                for child in element.children:
                    self._process_element(child, output, level)
                output.write('`')
                
        elif tag_name == 'pre':
            language = ''
            if element.get('class'):
                classes = element.get('class')
                for cls in classes:
                    if cls.startswith('language-'):
                        language = cls.replace('language-', '')
                        
            output.write(f'```{language}\n')
            for child in element.children:
                self._process_element(child, output, level)
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
    markdown = parser.parse_html_to_markdown(html_content)
    if not markdown:
        print("解析页面失败")
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
