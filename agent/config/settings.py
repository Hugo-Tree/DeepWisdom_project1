"""
配置管理模块
统一管理LLM Provider和其他全局配置
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum
from pathlib import Path

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    # 从项目根目录加载 .env
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # 如果没有安装 python-dotenv，跳过


class LLMProvider(Enum):
    """支持的LLM提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    ZHIPU = "zhipu"  # 智谱AI
    QWEN = "qwen"   # 通义千问


@dataclass
class LLMConfig:
    """单个LLM配置"""
    provider: LLMProvider
    api_key: str
    model_name: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    
    def to_dict(self) -> Dict:
        return {
            "provider": self.provider.value,
            "api_key": self.api_key,
            "model_name": self.model_name,
            "base_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
        }


@dataclass 
class AgentSettings:
    """Agent全局配置"""
    # 对话历史保留轮数
    conversation_history_limit: int = 10
    
    # 记忆模块配置
    memory_enabled: bool = True
    memory_storage_path: str = "./data/memory"
    
    # 搜索配置
    search_enabled: bool = True
    search_docs_path: str = "./data/docs"
    search_top_k: int = 3
    
    # 工具配置
    tools_enabled: bool = True
    
    # 默认LLM配置
    default_llm_provider: LLMProvider = LLMProvider.OPENAI


class Settings:
    """全局配置单例"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.agent_settings = AgentSettings()
        self.llm_configs: Dict[LLMProvider, LLMConfig] = {}
        self._load_from_env()
        self._initialized = True
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        # OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self.llm_configs[LLMProvider.OPENAI] = LLMConfig(
                provider=LLMProvider.OPENAI,
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model_name=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )
        
        # Anthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            self.llm_configs[LLMProvider.ANTHROPIC] = LLMConfig(
                provider=LLMProvider.ANTHROPIC,
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model_name=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            )
        
        # DeepSeek
        if os.getenv("DEEPSEEK_API_KEY"):
            self.llm_configs[LLMProvider.DEEPSEEK] = LLMConfig(
                provider=LLMProvider.DEEPSEEK,
                api_key=os.getenv("DEEPSEEK_API_KEY", ""),
                model_name=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
                base_url="https://api.deepseek.com",
            )
        
        # 智谱AI
        if os.getenv("ZHIPU_API_KEY"):
            self.llm_configs[LLMProvider.ZHIPU] = LLMConfig(
                provider=LLMProvider.ZHIPU,
                api_key=os.getenv("ZHIPU_API_KEY", ""),
                model_name=os.getenv("ZHIPU_MODEL", "glm-4"),
            )
        
        # 通义千问
        if os.getenv("QWEN_API_KEY"):
            self.llm_configs[LLMProvider.QWEN] = LLMConfig(
                provider=LLMProvider.QWEN,
                api_key=os.getenv("QWEN_API_KEY", ""),
                model_name=os.getenv("QWEN_MODEL", "qwen-turbo"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
    
    def get_llm_config(self, provider: Optional[LLMProvider] = None) -> Optional[LLMConfig]:
        """获取LLM配置"""
        if provider is None:
            provider = self.agent_settings.default_llm_provider
        return self.llm_configs.get(provider)
    
    def register_llm(self, config: LLMConfig):
        """注册新的LLM配置"""
        self.llm_configs[config.provider] = config
    
    def list_available_providers(self) -> list:
        """列出所有可用的LLM Provider"""
        return list(self.llm_configs.keys())


# 全局配置实例
settings = Settings()
