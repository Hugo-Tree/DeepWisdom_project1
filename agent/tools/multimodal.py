"""
多模态工具实现
支持图片搜索、图片生成等
"""

import os
import json
import base64
from typing import List, Optional
from pathlib import Path
import httpx

from .base import BaseTool, ToolParameter, ToolRegistry


class ImageSearchTool(BaseTool):
    """图片搜索工具（支持本地和网络搜索）"""
    
    def __init__(self, save_dir: str = "./data/images"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "search_images"
    
    @property
    def description(self) -> str:
        return "搜索图片。当用户想要看图片、查找图片或需要视觉内容时使用。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="图片搜索关键词",
                required=True,
            ),
            ToolParameter(
                name="count",
                type="number",
                description="返回结果数量，默认3",
                required=False,
                default=3,
            ),
        ]
    
    async def execute(self, query: str, count: int = 3, **kwargs) -> str:
        """执行图片搜索"""
        # 这里使用模拟实现
        # 实际可以集成 Bing Image Search API、Unsplash API 等
        
        result = f"""
图片搜索结果 (关键词: {query}):

【模拟结果】
由于这是演示版本，实际的图片搜索功能需要集成第三方API。

建议集成方案：
1. Bing Image Search API - 微软提供的图片搜索
2. Unsplash API - 高质量免费图片
3. Pexels API - 免费图片和视频

如需真实搜索，请配置相应的API Key。

当前你可以通过以下方式查看图片：
- 直接提供图片路径，让Agent分析图片内容
- 使用图片生成工具创建新图片
"""
        return result


class ImageGenerationTool(BaseTool):
    """图片生成工具（使用通义万相等API）"""
    
    def __init__(self, api_key: Optional[str] = None, save_dir: str = "./data/generated_images"):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "generate_image"
    
    @property
    def description(self) -> str:
        return "生成图片。当用户想要创建、画图、生成视觉内容时使用。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="prompt",
                type="string",
                description="图片生成的描述提示词，越详细越好",
                required=True,
            ),
            ToolParameter(
                name="style",
                type="string",
                description="图片风格",
                required=False,
                enum=["auto", "photography", "portrait", "3d", "anime", "oil painting", "watercolor", "sketch"],
            ),
        ]
    
    async def execute(self, prompt: str, style: str = "auto", **kwargs) -> str:
        """执行图片生成"""
        if not self.api_key:
            return """
❌ 图片生成功能未配置

要使用图片生成功能，请：
1. 获取通义万相API Key: https://dashscope.aliyun.com/
2. 设置环境变量: DASHSCOPE_API_KEY=your_api_key

或者集成其他图片生成服务：
- DALL-E 3 (OpenAI)
- Stable Diffusion
- Midjourney API
"""
        
        try:
            # 调用通义万相API
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            data = {
                "model": "wanx-v1",
                "input": {
                    "prompt": prompt,
                },
                "parameters": {
                    "style": style if style != "auto" else "<auto>",
                    "size": "1024*1024",
                    "n": 1,
                }
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=data)
                result = response.json()
            
            if response.status_code == 200 and "output" in result:
                image_url = result["output"]["results"][0]["url"]
                
                # 下载图片
                async with httpx.AsyncClient() as client:
                    img_response = await client.get(image_url)
                    if img_response.status_code == 200:
                        # 保存图片
                        import time
                        filename = f"generated_{int(time.time())}.png"
                        filepath = os.path.join(self.save_dir, filename)
                        
                        with open(filepath, "wb") as f:
                            f.write(img_response.content)
                        
                        return f"""
✅ 图片生成成功！

提示词: {prompt}
风格: {style}
图片已保存至: {filepath}

你可以查看该图片，或让我分析这张图片的内容。
"""
            else:
                error_msg = result.get("message", "未知错误")
                return f"❌ 图片生成失败: {error_msg}"
                
        except Exception as e:
            return f"❌ 图片生成出错: {str(e)}"


class ImageAnalysisTool(BaseTool):
    """图片分析工具（辅助工具，实际通过多模态模型实现）"""
    
    @property
    def name(self) -> str:
        return "analyze_image"
    
    @property
    def description(self) -> str:
        return "分析图片内容。当用户提供图片路径并询问图片相关问题时使用。注意：实际分析由多模态模型完成。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="image_path",
                type="string",
                description="图片文件路径",
                required=True,
            ),
            ToolParameter(
                name="question",
                type="string",
                description="关于图片的问题",
                required=False,
            ),
        ]
    
    async def execute(self, image_path: str, question: str = "请描述这张图片", **kwargs) -> str:
        """执行图片分析"""
        if not os.path.exists(image_path):
            return f"❌ 图片文件不存在: {image_path}"
        
        # 这个工具只是标记，实际分析由Agent的多模态能力完成
        return f"""
📷 图片分析请求已接收

图片路径: {image_path}
分析问题: {question}

提示：实际的图片分析将由多模态模型完成。
如果当前模型不支持视觉理解，请切换到支持的模型（如 qwen-vl-plus）。
"""


def create_multimodal_tools(
    enable_search: bool = True,
    enable_generation: bool = True,
    api_key: Optional[str] = None,
) -> List[BaseTool]:
    """创建并注册多模态工具"""
    tools = []
    
    if enable_search:
        search_tool = ImageSearchTool()
        ToolRegistry.register(search_tool)
        tools.append(search_tool)
    
    if enable_generation:
        gen_tool = ImageGenerationTool(api_key=api_key)
        ToolRegistry.register(gen_tool)
        tools.append(gen_tool)
    
    # 图片分析工具
    analysis_tool = ImageAnalysisTool()
    ToolRegistry.register(analysis_tool)
    tools.append(analysis_tool)
    
    return tools
