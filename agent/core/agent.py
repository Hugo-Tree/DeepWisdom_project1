"""
核心Agent实现
实现多轮对话、工具调用、记忆管理、多模态理解
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
from pathlib import Path

from ..config import settings, LLMProvider
from ..llm import LLMManager
from ..memory import MemoryManager, MemoryType, create_memory_manager
from ..tools import ToolRegistry, create_search_tool, register_common_tools, create_multimodal_tools


class MessageRole(Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """对话消息"""
    role: MessageRole
    content: Union[str, List[Dict]]  # 支持文本或多模态内容
    name: Optional[str] = None  # 工具名称
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    
    def to_dict(self) -> Dict:
        msg = {
            "role": self.role.value,
            "content": self.content,
        }
        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": tc["arguments"],
                    }
                }
                for tc in self.tool_calls
            ]
        return msg


@dataclass
class ConversationContext:
    """对话上下文"""
    messages: List[Message] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Message):
        self.messages.append(message)
    
    def get_recent_messages(self, n: int) -> List[Message]:
        """获取最近n条消息"""
        return self.messages[-n:] if len(self.messages) > n else self.messages
    
    def to_dict_list(self) -> List[Dict]:
        """转换为字典列表"""
        return [msg.to_dict() for msg in self.messages]
    
    def clear(self):
        """清空对话历史"""
        self.messages.clear()


class Agent:
    """通用对话Agent"""
    
    DEFAULT_SYSTEM_PROMPT = """你是一个智能助手，能够帮助用户解答问题、完成任务。

你的特点：
1. 友好、专业、有帮助
2. 可以使用工具来获取信息或执行操作
3. 会记住用户的偏好和相关信息
4. 回答简洁明了，重点突出
5. **支持多模态**：能够理解图片内容，并能生成或搜索图片

当你需要查找信息时，请使用搜索工具。
当用户分享个人信息时，请记住这些信息以便后续使用。
当用户询问图片相关内容或需要视觉素材时，使用图片工具。
"""
    
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        enable_memory: bool = True,
        enable_tools: bool = True,
        enable_multimodal: bool = True,
        docs_path: Optional[str] = None,
        memory_path: Optional[str] = None,
        history_limit: int = 10,
    ):
        """
        初始化Agent
        
        Args:
            system_prompt: 系统提示词
            llm_provider: LLM提供商
            enable_memory: 是否启用记忆功能
            enable_tools: 是否启用工具
            enable_multimodal: 是否启用多模态功能
            docs_path: 文档搜索路径
            memory_path: 记忆存储路径
            history_limit: 对话历史保留条数
        """
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        self.llm_provider = llm_provider
        self.enable_memory = enable_memory
        self.enable_tools = enable_tools
        self.enable_multimodal = enable_multimodal
        self.history_limit = history_limit
        
        # 初始化对话上下文
        self.context = ConversationContext()
        self.context.add_message(Message(
            role=MessageRole.SYSTEM,
            content=self.system_prompt,
        ))
        
        # 初始化记忆管理器
        self.memory_manager: Optional[MemoryManager] = None
        if enable_memory:
            memory_storage_path = memory_path or settings.agent_settings.memory_storage_path
            self.memory_manager = create_memory_manager(memory_storage_path)
        
        # 初始化工具
        if enable_tools:
            docs_search_path = docs_path or settings.agent_settings.search_docs_path
            create_search_tool(docs_search_path)
            register_common_tools()
            
            # 注册多模态工具
            if enable_multimodal:
                create_multimodal_tools(
                    enable_search=True,
                    enable_generation=True,
                )
        
        # 回调函数
        self.on_tool_call: Optional[Callable[[str, str], None]] = None
        self.on_tool_result: Optional[Callable[[str, str], None]] = None
    
    def _parse_image_path(self, text: str) -> tuple[str, Optional[str]]:
        """从文本中解析图片路径"""
        import re
        # 匹配 [image:path] 或 <image:path> 格式
        pattern = r'[\[<]image:([^\]>]+)[\]>]'
        match = re.search(pattern, text)
        if match:
            image_path = match.group(1).strip()
            # 移除图片标记，保留其他文本
            clean_text = re.sub(pattern, '', text).strip()
            return clean_text, image_path
        return text, None
    
    def _build_multimodal_content(self, text: str, image_path: Optional[str] = None) -> Union[str, List[Dict]]:
        """构建多模态内容"""
        if not image_path or not self.enable_multimodal:
            return text
        
        # 检查图片是否存在
        if not os.path.exists(image_path):
            return f"{text}\n[注意: 图片文件不存在: {image_path}]"
        
        # 构建多模态内容
        content = []
        if text:
            content.append({"type": "text", "text": text})
        
        content.append({
            "type": "image_url",
            "image_url": {"url": image_path}
        })
        
        return content
    
    async def _build_messages(self, memory_context: str = "") -> List[Dict]:
        """构建发送给LLM的消息列表"""
        messages = []
        
        # 系统消息
        system_content = self.system_prompt
        
        # 添加记忆上下文
        if memory_context:
            system_content += f"\n\n{memory_context}"
        
        messages.append({
            "role": "system",
            "content": system_content,
        })
        
        # 获取最近的对话历史（跳过system消息）
        recent_messages = self.context.get_recent_messages(self.history_limit + 1)[1:]
        
        for msg in recent_messages:
            messages.append(msg.to_dict())
        
        return messages
    
    def _get_tools(self) -> Optional[List[Dict]]:
        """获取可用工具列表"""
        if not self.enable_tools:
            return None
        
        tools = ToolRegistry.get_all_definitions()
        return tools if tools else None
    
    async def _handle_tool_calls(self, tool_calls: List[Dict]) -> List[Message]:
        """处理工具调用"""
        tool_messages = []
        
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["arguments"]
            tool_id = tool_call["id"]
            
            # 回调通知
            if self.on_tool_call:
                self.on_tool_call(tool_name, tool_args)
            
            # 执行工具
            result = await ToolRegistry.execute(tool_name, tool_args)
            
            # 回调通知
            if self.on_tool_result:
                self.on_tool_result(tool_name, result)
            
            tool_messages.append(Message(
                role=MessageRole.TOOL,
                content=result,
                name=tool_name,
                tool_call_id=tool_id,
            ))
        
        return tool_messages
    
    async def _extract_memory(self, user_message: str, assistant_response: str):
        """从对话中提取记忆"""
        if not self.memory_manager:
            return
        
        # 简单的规则提取（实际可以用LLM来提取）
        extracted = {}
        
        # 检测用户偏好
        preference_patterns = [
            ("喜欢", MemoryType.USER_PREFERENCE),
            ("偏好", MemoryType.USER_PREFERENCE),
            ("我是", MemoryType.USER_INFO),
            ("我叫", MemoryType.USER_INFO),
            ("我的名字", MemoryType.USER_INFO),
            ("对...感兴趣", MemoryType.TOPIC_INTEREST),
        ]
        
        for pattern, mem_type in preference_patterns:
            if pattern in user_message:
                # 提取相关句子
                sentences = user_message.split("。")
                for sent in sentences:
                    if pattern in sent:
                        mem_type_key = mem_type.value
                        if mem_type_key not in extracted:
                            extracted[mem_type_key] = []
                        extracted[mem_type_key].append(sent.strip())
        
        if extracted:
            await self.memory_manager.extract_and_save_memory(
                user_message, assistant_response, extracted
            )
    
    async def chat(self, user_input: str, image_path: Optional[str] = None) -> str:
        """
        与Agent对话
        
        Args:
            user_input: 用户输入（可包含 [image:path] 标记）
            image_path: 图片路径（可选，也可以在user_input中使用标记）
            
        Returns:
            Agent回复
        """
        # 解析图片路径
        if not image_path:
            user_input, parsed_image = self._parse_image_path(user_input)
            if parsed_image:
                image_path = parsed_image
        
        # 构建消息内容
        message_content = self._build_multimodal_content(user_input, image_path)
        
        # 添加用户消息
        self.context.add_message(Message(
            role=MessageRole.USER,
            content=message_content,
        ))
        
        # 获取记忆上下文
        memory_context = ""
        if self.memory_manager:
            memory_context = await self.memory_manager.format_memories_for_context(user_input)
        
        # 构建消息
        messages = await self._build_messages(memory_context)
        tools = self._get_tools()
        
        # 调用LLM
        response = await LLMManager.chat(
            messages=messages,
            tools=tools,
            provider=self.llm_provider,
        )
        
        # 处理工具调用
        max_tool_iterations = 5
        iteration = 0
        
        while response["tool_calls"] and iteration < max_tool_iterations:
            iteration += 1
            
            # 添加助手消息（包含工具调用）
            self.context.add_message(Message(
                role=MessageRole.ASSISTANT,
                content=response["content"] or "",
                tool_calls=response["tool_calls"],
            ))
            
            # 处理工具调用
            tool_messages = await self._handle_tool_calls(response["tool_calls"])
            for msg in tool_messages:
                self.context.add_message(msg)
            
            # 重新构建消息并调用LLM
            messages = await self._build_messages(memory_context)
            response = await LLMManager.chat(
                messages=messages,
                tools=tools,
                provider=self.llm_provider,
            )
        
        # 获取最终回复
        assistant_response = response["content"] or "抱歉，我无法生成回复。"
        
        # 添加助手回复
        self.context.add_message(Message(
            role=MessageRole.ASSISTANT,
            content=assistant_response,
        ))
        
        # 提取并保存记忆
        await self._extract_memory(user_input, assistant_response)
        
        return assistant_response
    
    async def add_memory(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.FACT,
        importance: float = 0.5,
    ):
        """手动添加记忆"""
        if self.memory_manager:
            await self.memory_manager.add_memory(
                content=content,
                memory_type=memory_type,
                importance=importance,
            )
    
    async def get_user_profile(self) -> Dict:
        """获取用户画像"""
        if self.memory_manager:
            return await self.memory_manager.get_user_profile()
        return {}
    
    def reset_conversation(self):
        """重置对话"""
        self.context.clear()
        self.context.add_message(Message(
            role=MessageRole.SYSTEM,
            content=self.system_prompt,
        ))
    
    def get_conversation_history(self) -> List[Dict]:
        """获取对话历史"""
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in self.context.messages
            if msg.role != MessageRole.SYSTEM
        ]
