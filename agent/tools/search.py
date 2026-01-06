"""
搜索工具实现
支持本地文档的关键词检索
"""

import os
import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from .base import BaseTool, ToolParameter, ToolRegistry


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    content: str
    score: float
    source: str
    snippet: str = ""


class LocalDocumentSearchTool(BaseTool):
    """本地文档搜索工具"""
    
    def __init__(self, docs_path: str, file_extensions: List[str] = None):
        self.docs_path = docs_path
        self.file_extensions = file_extensions or [".txt", ".md", ".json"]
        self._documents: Dict[str, str] = {}
        self._load_documents()
    
    @property
    def name(self) -> str:
        return "search_documents"
    
    @property
    def description(self) -> str:
        return "在本地知识库中搜索相关文档。当用户询问特定主题、需要查找信息或回答需要依据时使用此工具。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询关键词，可以是问题或关键词组合",
                required=True,
            ),
            ToolParameter(
                name="top_k",
                type="number",
                description="返回结果数量，默认为3",
                required=False,
                default=3,
            ),
        ]
    
    def _load_documents(self):
        """加载本地文档"""
        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path, exist_ok=True)
            return
        
        for root, dirs, files in os.walk(self.docs_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.file_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # 使用相对路径作为key
                            rel_path = os.path.relpath(file_path, self.docs_path)
                            self._documents[rel_path] = content
                    except Exception as e:
                        print(f"加载文档失败 {file_path}: {e}")
    
    def reload_documents(self):
        """重新加载文档"""
        self._documents.clear()
        self._load_documents()
    
    def _calculate_score(self, query: str, content: str) -> float:
        """计算查询与文档的相关性分数"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        score = 0.0
        
        # 完整匹配
        if query_lower in content_lower:
            score += 2.0
        
        # 词级匹配
        query_words = re.findall(r'\w+', query_lower)
        content_words = set(re.findall(r'\w+', content_lower))
        
        matched_words = sum(1 for word in query_words if word in content_words)
        if query_words:
            score += (matched_words / len(query_words)) * 1.5
        
        # 词频加权
        for word in query_words:
            count = content_lower.count(word)
            score += min(count * 0.1, 0.5)  # 限制最大加分
        
        return score
    
    def _extract_snippet(self, query: str, content: str, max_length: int = 200) -> str:
        """提取包含查询词的片段"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # 找到第一个匹配位置
        pos = content_lower.find(query_lower)
        if pos == -1:
            # 尝试找单词匹配
            for word in query_lower.split():
                pos = content_lower.find(word)
                if pos != -1:
                    break
        
        if pos == -1:
            # 返回开头部分
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # 提取上下文
        start = max(0, pos - 50)
        end = min(len(content), pos + max_length - 50)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    async def execute(self, query: str, top_k: int = 3, **kwargs) -> str:
        """执行搜索"""
        if not self._documents:
            return "没有可搜索的文档。请确保文档目录存在且包含文档文件。"
        
        results: List[SearchResult] = []
        
        for doc_name, content in self._documents.items():
            score = self._calculate_score(query, content)
            if score > 0:
                # 提取标题（第一行或文件名）
                first_line = content.split('\n')[0].strip()
                title = first_line[:50] if first_line else doc_name
                
                results.append(SearchResult(
                    title=title,
                    content=content,
                    score=score,
                    source=doc_name,
                    snippet=self._extract_snippet(query, content),
                ))
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        results = results[:top_k]
        
        if not results:
            return f"未找到与 '{query}' 相关的文档。"
        
        # 格式化输出
        output_lines = [f"找到 {len(results)} 条相关结果:\n"]
        for i, result in enumerate(results, 1):
            output_lines.append(f"【结果 {i}】")
            output_lines.append(f"来源: {result.source}")
            output_lines.append(f"标题: {result.title}")
            output_lines.append(f"内容摘要: {result.snippet}")
            output_lines.append("")
        
        return "\n".join(output_lines)


class WebSearchTool(BaseTool):
    """网络搜索工具（模拟实现）"""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "在互联网上搜索信息。当用户询问最新新闻、实时信息或本地知识库无法回答的问题时使用。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询",
                required=True,
            ),
        ]
    
    async def execute(self, query: str, **kwargs) -> str:
        """模拟网络搜索"""
        # 这里是模拟实现，实际可以集成真实的搜索API
        return f"""
网络搜索结果 (模拟):

查询: {query}

【结果 1】
标题: 关于 {query} 的介绍
来源: example.com
摘要: 这是一个关于 {query} 的模拟搜索结果...

【结果 2】
标题: {query} 最新动态
来源: news.example.com
摘要: 这是关于 {query} 的最新新闻...

注意: 这是模拟数据，如需真实搜索结果，请配置搜索API。
"""


def create_search_tool(docs_path: str) -> LocalDocumentSearchTool:
    """创建并注册本地搜索工具"""
    tool = LocalDocumentSearchTool(docs_path)
    ToolRegistry.register(tool)
    return tool


def create_web_search_tool() -> WebSearchTool:
    """创建并注册网络搜索工具"""
    tool = WebSearchTool()
    ToolRegistry.register(tool)
    return tool
