"""
工具基类和注册机制
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    
    def to_openai_format(self) -> Dict:
        """转换为OpenAI function calling格式"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        }


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """工具参数列表"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具"""
        pass
    
    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )
    
    def to_openai_format(self) -> Dict:
        """转换为OpenAI格式"""
        return self.get_definition().to_openai_format()


class ToolRegistry:
    """工具注册表"""
    
    _tools: Dict[str, BaseTool] = {}
    
    @classmethod
    def register(cls, tool: BaseTool):
        """注册工具"""
        cls._tools[tool.name] = tool
    
    @classmethod
    def unregister(cls, name: str):
        """取消注册"""
        if name in cls._tools:
            del cls._tools[name]
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return cls._tools.get(name)
    
    @classmethod
    def list_all(cls) -> List[BaseTool]:
        """列出所有工具"""
        return list(cls._tools.values())
    
    @classmethod
    def get_all_definitions(cls) -> List[Dict]:
        """获取所有工具定义（OpenAI格式）"""
        return [tool.to_openai_format() for tool in cls._tools.values()]
    
    @classmethod
    async def execute(cls, name: str, arguments: Union[str, Dict]) -> str:
        """执行工具"""
        tool = cls.get(name)
        if tool is None:
            return f"错误: 工具 '{name}' 不存在"
        
        try:
            if isinstance(arguments, str):
                kwargs = json.loads(arguments)
            else:
                kwargs = arguments
            
            return await tool.execute(**kwargs)
        except json.JSONDecodeError as e:
            return f"错误: 参数解析失败 - {str(e)}"
        except Exception as e:
            return f"错误: 工具执行失败 - {str(e)}"
    
    @classmethod
    def clear(cls):
        """清空所有工具"""
        cls._tools.clear()


def tool(name: str, description: str, parameters: List[ToolParameter] = None):
    """工具装饰器 - 快速将函数注册为工具"""
    
    def decorator(func: Callable):
        class FunctionTool(BaseTool):
            @property
            def name(self) -> str:
                return name
            
            @property
            def description(self) -> str:
                return description
            
            @property
            def parameters(self) -> List[ToolParameter]:
                return parameters or []
            
            async def execute(self, **kwargs) -> str:
                import asyncio
                result = func(**kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return str(result)
        
        tool_instance = FunctionTool()
        ToolRegistry.register(tool_instance)
        return func
    
    return decorator
