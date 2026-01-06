"""
LLM管理模块
统一管理多家Model Provider的调用
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator
import json

from ..config import settings, LLMProvider, LLMConfig


class BaseLLMClient(ABC):
    """LLM客户端基类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict:
        """发送对话请求"""
        pass
    
    @abstractmethod
    async def chat_stream(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式对话"""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI兼容客户端（支持OpenAI、DeepSeek等）"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def chat(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict:
        client = self._get_client()
        
        params = {
            "model": self.config.model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
        }
        
        if tools:
            params["tools"] = tools
            params["tool_choice"] = kwargs.get("tool_choice", "auto")
        
        response = await client.chat.completions.create(**params)
        
        return {
            "content": response.choices[0].message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in (response.choices[0].message.tool_calls or [])
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            },
            "raw": response,
        }
    
    async def chat_stream(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        
        params = {
            "model": self.config.model_name,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "stream": True,
        }
        
        if tools:
            params["tools"] = tools
        
        stream = await client.chat.completions.create(**params)
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude客户端"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                timeout=self.config.timeout,
            )
        return self._client
    
    def _convert_tools(self, tools: Optional[List[Dict]]) -> Optional[List[Dict]]:
        """转换工具格式为Anthropic格式"""
        if not tools:
            return None
        
        anthropic_tools = []
        for tool in tools:
            anthropic_tools.append({
                "name": tool["function"]["name"],
                "description": tool["function"].get("description", ""),
                "input_schema": tool["function"].get("parameters", {"type": "object", "properties": {}}),
            })
        return anthropic_tools
    
    async def chat(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict:
        client = self._get_client()
        
        # 提取system消息
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                filtered_messages.append(msg)
        
        params = {
            "model": self.config.model_name,
            "messages": filtered_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        
        if system_msg:
            params["system"] = system_msg
        
        if tools:
            params["tools"] = self._convert_tools(tools)
        
        response = await client.messages.create(**params)
        
        # 解析响应
        content = ""
        tool_calls = []
        
        for block in response.content:
            if hasattr(block, "text"):
                content = block.text
            elif hasattr(block, "type") and block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": json.dumps(block.input),
                })
        
        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
            },
            "raw": response,
        }
    
    async def chat_stream(
        self, 
        messages: List[Dict], 
        tools: Optional[List[Dict]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        
        # 提取system消息
        system_msg = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                filtered_messages.append(msg)
        
        params = {
            "model": self.config.model_name,
            "messages": filtered_messages,
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }
        
        if system_msg:
            params["system"] = system_msg
        
        async with client.messages.stream(**params) as stream:
            async for text in stream.text_stream:
                yield text


class LLMManager:
    """LLM管理器 - 统一管理多家Provider"""
    
    _clients: Dict[LLMProvider, BaseLLMClient] = {}
    
    @classmethod
    def get_client(cls, provider: Optional[LLMProvider] = None) -> BaseLLMClient:
        """获取LLM客户端"""
        if provider is None:
            provider = settings.agent_settings.default_llm_provider
        
        if provider not in cls._clients:
            config = settings.get_llm_config(provider)
            if config is None:
                raise ValueError(f"未找到 {provider.value} 的配置，请检查环境变量")
            
            cls._clients[provider] = cls._create_client(config)
        
        return cls._clients[provider]
    
    @classmethod
    def _create_client(cls, config: LLMConfig) -> BaseLLMClient:
        """根据配置创建对应的客户端"""
        if config.provider in [LLMProvider.OPENAI, LLMProvider.DEEPSEEK, LLMProvider.QWEN]:
            return OpenAIClient(config)
        elif config.provider == LLMProvider.ANTHROPIC:
            return AnthropicClient(config)
        elif config.provider == LLMProvider.ZHIPU:
            # 智谱AI使用OpenAI兼容接口
            config.base_url = "https://open.bigmodel.cn/api/paas/v4"
            return OpenAIClient(config)
        else:
            raise ValueError(f"不支持的Provider: {config.provider}")
    
    @classmethod
    def list_available(cls) -> List[LLMProvider]:
        """列出所有可用的Provider"""
        return settings.list_available_providers()
    
    @classmethod
    async def chat(
        cls,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        provider: Optional[LLMProvider] = None,
        **kwargs
    ) -> Dict:
        """统一的对话接口"""
        client = cls.get_client(provider)
        return await client.chat(messages, tools, **kwargs)
