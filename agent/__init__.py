"""
通用对话Agent

一个具备多轮对话、搜索、记忆等能力的智能Agent
"""

from .core import Agent, Message, MessageRole, ConversationContext
from .config import settings, Settings, LLMProvider, LLMConfig, AgentSettings
from .llm import LLMManager
from .memory import MemoryManager, MemoryType, create_memory_manager
from .tools import ToolRegistry, BaseTool, ToolParameter, create_search_tool

__version__ = "0.1.0"

__all__ = [
    # Core
    "Agent",
    "Message",
    "MessageRole",
    "ConversationContext",
    # Config
    "settings",
    "Settings",
    "LLMProvider",
    "LLMConfig",
    "AgentSettings",
    # LLM
    "LLMManager",
    # Memory
    "MemoryManager",
    "MemoryType",
    "create_memory_manager",
    # Tools
    "ToolRegistry",
    "BaseTool",
    "ToolParameter",
    "create_search_tool",
]
