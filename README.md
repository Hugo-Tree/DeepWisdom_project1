# 通用对话 Agent（多模态版）

一个具备多轮对话、智能搜索、记忆系统、**多模态理解与生成**能力的通用对话Agent。

## 功能特性

### ✅ 核心功能

1. **多轮对话能力**
   - 理解用户文本输入
   - 输出连贯、符合上下文的回复
   - 保持最近对话的语境（默认10轮）

2. **搜索能力**
   - 自动判断何时需要搜索
   - 本地文档关键词检索
   - 根据搜索结果更新回复

### ⭐ 高级功能

3. **Memory 记忆系统**
   - 记忆存储：本地JSON文件持久化
   - 记忆管理：按类型分类（偏好、信息、兴趣、事实）
   - 记忆读取：相关性搜索，自动注入上下文

4. **工具使用**
   - 工具注册机制：支持自定义工具
   - 内置工具：搜索、计算器、日期时间、**图片工具**
   - 自动决策：LLM自主决定是否调用工具

5. **LLM管理**
   - 统一接口：支持多家Provider（OpenAI、Anthropic、DeepSeek、通义千问等）
   - 配置管理：环境变量统一管理API Key
   - 易于扩展：添加新Provider只需实现简单接口

6. **🎨 多模态功能** ⭐ NEW
   - **图片理解**：支持分析图片内容（jpg/png/gif/webp）
   - **图片生成**：根据文本描述生成图片（通义万相API）
   - **图片搜索**：搜索相关图片资源
   - **多模态对话**：在对话中混合文本和图片

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
- OpenAI (`OPENAI_API_KEY`) - 支持 GPT-4o 多模态
- Anthropic (`ANTHROPIC_API_KEY`) - 支持 Claude 3 多模态
- DeepSeek (`DEEPSEEK_API_KEY`)
- 智谱AI (`ZHIPU_API_KEY`)
- **通义千问 (`QWEN_API_KEY`) - 推荐使用 qwen-vl-plus 多模态模型** ⭐

**多模态配置（可选）：**
```bash
# 使用多模态模型
QWEN_MODEL=qwen-vl-plus

# 图片生成功能（可选）
DASHSCOPE_API_KEY=你的通义万相API_Key
```

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
| `/image <路径>` | 分析指定图片 ⭐ |
| `/reload` | 重新加载文档 |
| `/help` | 显示帮助 |
| `/quit` | 退出程序 |

### 多模态使用示例 🎨

#### 图片理解
```
👤 你: /image ./data/images/cat.jpg

🤖 助手: 这是一张可爱的橘猫图片。猫咪正趴在阳光下...
```

或在对话中：
```
👤 你: 这张图片里有什么？[image:./photos/sunset.jpg]

🤖 助手: 这是一张美丽的日落照片，天空呈现出橙红色渐变...
```

#### 图片生成
```
👤 你: 帮我生成一张未来城市的图片，赛博朋克风格

🔧 调用工具: generate_image
🤖 助手: ✅ 图片已生成并保存至 ./data/generated_images/...
```

## 多模态功能详解 🎨

### 图片理解

**支持的图片格式：** jpg/jpeg, png, gif, webp

**使用方法：**

1. **使用命令**
   ```bash
   /image path/to/your/image.jpg
   ```

2. **在对话中使用标记**
   ```
   这张图片显示了什么？[image:path/to/image.jpg]
   ```

3. **通过代码调用**
   ```python
   response = await agent.chat("描述这张图片", image_path="path/to/image.jpg")
   ```

**注意事项：**
- 需要使用支持视觉的模型（如 `qwen-vl-plus`, `gpt-4o`, `claude-3-opus`）
- 图片文件路径必须存在且可访问
- 建议图片大小不超过5MB

### 图片生成

Agent可以根据文本描述生成图片（使用通义万相API）。

**配置：**
```bash
# 在 .env 文件中添加
DASHSCOPE_API_KEY=你的API_Key
```

**使用方法：**

直接在对话中描述你想要的图片：
```
帮我生成一张日落海滩的图片
画一只可爱的小猫，卡通风格
创作一幅未来城市的画，赛博朋克风格
```

**支持的风格：**
- auto（自动）
- photography（摄影）
- portrait（肖像）
- 3d（三维）
- anime（动漫）
- oil painting（油画）
- watercolor（水彩）
- sketch（素描）

生成的图片会自动保存到 `./data/generated_images/` 目录。

### 图片搜索

**使用方法：**
```
搜索一些关于人工智能的图片
找一张猫的图片
```

**扩展方案：**
- 集成 Bing Image Search API
- 集成 Unsplash API（高质量免费图片）
- 集成 Pexels API（免费图片和视频）

### 技术实现

**多模态消息格式：**
```python
# 纯文本消息
message = {
    "role": "user",
    "content": "你好"
}

# 多模态消息（文本+图片）
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "这是什么？"},
        {"type": "image_url", "image_url": {"url": "path/to/image.jpg"}}
    ]
}
```

**工具集成：**
- `ImageSearchTool`: 图片搜索工具
- `ImageGenerationTool`: 图片生成工具（通义万相API）
- `ImageAnalysisTool`: 图片分析辅助工具

### 常见问题

**Q: 图片理解不准确怎么办？**

A: 
1. 确保使用支持视觉的模型（qwen-vl-plus）
2. 提供更具体的问题描述
3. 确保图片清晰且文件大小合适

**Q: 图片生成失败？**

A: 
1. 检查 DASHSCOPE_API_KEY 是否配置
2. 确认账户余额充足
3. 检查提示词是否符合内容安全规范

**Q: 如何批量处理图片？**

A: 可以编写脚本循环调用 `agent.chat()` 方法，传入不同的图片路径。

### 未来可扩展

**支持更多模态：**
1. **音频理解**：集成 Whisper API 进行语音转文字，使用 qwen-audio 模型
2. **视频理解**：提取关键帧进行分析，使用专门的视频理解模型
3. **文档理解**：PDF、Word 等文档的图片提取和理解，表格识别和数据提取

**增强图片生成：**
1. **图片编辑**：局部修改（inpainting）、风格迁移、图片放大增强
2. **高级控制**：ControlNet 精确控制、参考图生成、多轮迭代优化

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
