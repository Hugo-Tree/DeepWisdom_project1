# 通用对话 Agent

一个具备多轮对话、智能搜索、记忆系统等能力的通用对话Agent。

## 功能特性

### 功能

1. **多轮对话能力**
   - 理解用户文本输入
   - 输出连贯、符合上下文的回复
   - 保持最近对话的语境（默认10轮）

2. **搜索能力**
   - 自动判断何时需要搜索
   - 本地文档关键词检索
   - 根据搜索结果更新回复

3. **Memory 记忆系统**
   - 记忆存储：本地JSON文件持久化
   - 记忆管理：按类型分类（偏好、信息、兴趣、事实）
   - 记忆读取：相关性搜索，自动注入上下文

4. **工具使用**
   - 工具注册机制：支持自定义工具
   - 内置工具：搜索、计算器、日期时间
   - 自动决策：LLM自主决定是否调用工具

5. **LLM管理**
   - 统一接口：支持多家Provider（OpenAI、Anthropic、DeepSeek等）
   - 配置管理：环境变量统一管理API Key
   - 易于扩展：添加新Provider只需实现简单接口

## 项目结构

```
project1/
├── main.py                 # 主入口
├── requirements.txt        # 依赖
├── .env.example           # 环境变量示例
├── README.md              # 项目文档
├── agent/
│   ├── __init__.py
│   ├── config/            # 配置管理
│   │   ├── __init__.py
│   │   └── settings.py    # 全局配置、LLM配置
│   ├── core/              # 核心Agent
│   │   ├── __init__.py
│   │   └── agent.py       # Agent主逻辑
│   ├── llm/               # LLM管理
│   │   ├── __init__.py
│   │   └── manager.py     # 多Provider统一管理
│   ├── memory/            # 记忆模块
│   │   ├── __init__.py
│   │   └── manager.py     # 记忆存储、管理、读取
│   └── tools/             # 工具模块
│       ├── __init__.py
│       ├── base.py        # 工具基类、注册机制
│       ├── search.py      # 搜索工具
│       └── common.py      # 通用工具
└── data/
    └── docs/              # 搜索文档目录
        ├── python_intro.md
        ├── machine_learning.md
        ├── llm_intro.md
        └── agent_concept.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env，填入你的API Key
# 至少需要配置一个LLM Provider
```

支持的LLM Provider：
- OpenAI (`OPENAI_API_KEY`)
- Anthropic (`ANTHROPIC_API_KEY`)
- DeepSeek (`DEEPSEEK_API_KEY`)
- 智谱AI (`ZHIPU_API_KEY`)
- 通义千问 (`QWEN_API_KEY`)

### 3. 运行

```bash
python main.py
```

或指定Provider：

```bash
python main.py --provider deepseek
```

## 使用方法

### 命令行交互

```
👤 你: 你好，我是小明，我喜欢学习Python
🤖 助手: 你好小明！很高兴认识你...

👤 你: 什么是机器学习？
🔧 调用工具: search_documents
📋 工具结果: 找到 3 条相关结果...
🤖 助手: 机器学习是人工智能的一个分支...

👤 你: /memory
📝 用户记忆：
  user_info:
    - 我是小明
  user_preference:
    - 我喜欢学习Python
```

### 可用命令

| 命令 | 说明 |
|------|------|
| `/clear` | 清空对话历史 |
| `/memory` | 查看已保存的记忆 |
| `/history` | 显示当前对话历史 |
| `/reload` | 重新加载文档 |
| `/help` | 显示帮助 |
| `/quit` | 退出程序 |

## 代码使用示例

```python
import asyncio
from agent import Agent, LLMProvider

async def main():
    # 创建Agent
    agent = Agent(
        llm_provider=LLMProvider.OPENAI,
        enable_memory=True,
        enable_tools=True,
        docs_path="./data/docs",
    )
    
    # 对话
    response = await agent.chat("你好，请介绍一下Python")
    print(response)
    
    # 继续对话（保持上下文）
    response = await agent.chat("它有什么特点？")
    print(response)

asyncio.run(main())
```

### 自定义工具

```python
from agent.tools import BaseTool, ToolParameter, ToolRegistry

class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "我的自定义工具"
    
    @property
    def parameters(self) -> list:
        return [
            ToolParameter(
                name="param1",
                type="string",
                description="参数说明",
            )
        ]
    
    async def execute(self, param1: str, **kwargs) -> str:
        return f"执行结果: {param1}"

# 注册工具
ToolRegistry.register(MyTool())
```

## 设计说明

### LLM管理设计

```
┌─────────────────────────────────────────┐
│              LLMManager                 │
│  ┌─────────────────────────────────┐   │
│  │         统一接口                  │   │
│  │    chat(messages, tools)        │   │
│  └─────────────────────────────────┘   │
│                 │                       │
│    ┌────────────┼────────────┐         │
│    ▼            ▼            ▼         │
│ ┌──────┐   ┌──────┐    ┌──────┐       │
│ │OpenAI│   │Claude│    │DeepSeek│      │
│ │Client│   │Client│    │Client │      │
│ └──────┘   └──────┘    └──────┘       │
└─────────────────────────────────────────┘
```

### Memory 设计

```
记忆模块 = 记忆存储 + 记忆管理 + 记忆读取

记忆类型:
├── USER_PREFERENCE  # 用户偏好
├── USER_INFO        # 用户信息
├── TOPIC_INTEREST   # 话题兴趣
├── FACT             # 相关事实
└── INTERACTION      # 交互记录

存储: LocalFileStorage (JSON)
管理: MemoryManager (CRUD + 搜索)
读取: 相关性匹配 → 注入System Prompt
```

### 工具调用流程

```
用户输入 → Agent
    │
    ▼
构建Messages（含System Prompt + Memory）
    │
    ▼
LLM调用（带Tools定义）
    │
    ▼
判断是否需要工具 ─── 否 ──→ 返回回复
    │
    是
    ▼
执行工具调用 → 获取结果
    │
    ▼
将结果加入Messages
    │
    ▼
再次调用LLM（最多5轮）
    │
    ▼
返回最终回复
```

## License

MIT
