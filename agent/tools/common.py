"""
通用工具实现
"""

import datetime
import math
from typing import List

from .base import BaseTool, ToolParameter, ToolRegistry


class CalculatorTool(BaseTool):
    """计算器工具"""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "执行数学计算。支持基本运算（加减乘除）和高级运算（幂、开方、三角函数等）。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="数学表达式，如 '2 + 3 * 4' 或 'sqrt(16)'",
                required=True,
            ),
        ]
    
    async def execute(self, expression: str, **kwargs) -> str:
        """执行计算"""
        try:
            # 安全的数学函数
            safe_dict = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
            }
            
            # 执行计算
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return f"计算结果: {expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"


class DateTimeTool(BaseTool):
    """日期时间工具"""
    
    @property
    def name(self) -> str:
        return "datetime"
    
    @property
    def description(self) -> str:
        return "获取当前日期时间或进行日期计算。"
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型",
                required=True,
                enum=["now", "date", "time", "weekday"],
            ),
            ToolParameter(
                name="format",
                type="string",
                description="日期时间格式（可选）",
                required=False,
            ),
        ]
    
    async def execute(self, action: str, format: str = None, **kwargs) -> str:
        """执行日期时间操作"""
        now = datetime.datetime.now()
        
        if action == "now":
            fmt = format or "%Y-%m-%d %H:%M:%S"
            return f"当前时间: {now.strftime(fmt)}"
        elif action == "date":
            fmt = format or "%Y-%m-%d"
            return f"当前日期: {now.strftime(fmt)}"
        elif action == "time":
            fmt = format or "%H:%M:%S"
            return f"当前时间: {now.strftime(fmt)}"
        elif action == "weekday":
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            return f"今天是: {weekdays[now.weekday()]}"
        else:
            return f"未知操作: {action}"


def register_common_tools():
    """注册通用工具"""
    ToolRegistry.register(CalculatorTool())
    ToolRegistry.register(DateTimeTool())
