"""
通用对话Agent - 命令行入口

使用方法：
    python main.py
    
或者指定LLM Provider：
    python main.py --provider openai
    python main.py --provider deepseek
"""

import asyncio
import argparse
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import Agent, LLMProvider, settings


def print_banner():
    """打印欢迎信息"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                    🤖 通用对话 Agent                           ║
║                                                               ║
║  功能特性:                                                     ║
║  • 多轮对话 - 保持上下文连贯                                    ║
║  • 智能搜索 - 自动检索本地文档                                  ║
║  • 记忆系统 - 记住用户偏好和信息                                ║
║  • 工具调用 - 计算器、日期时间等                                ║
║                                                               ║
║  命令:                                                         ║
║  • /clear  - 清空对话历史                                      ║
║  • /memory - 查看记忆内容                                      ║
║  • /help   - 显示帮助                                          ║
║  • /quit   - 退出程序                                          ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_help():
    """打印帮助信息"""
    help_text = """
可用命令：
  /clear    清空当前对话历史，开始新对话
  /memory   显示已保存的用户记忆
  /history  显示当前对话历史
  /reload   重新加载文档
  /help     显示此帮助信息
  /quit     退出程序

提示：
  - 可以询问任何问题，Agent会尝试回答
  - 当需要查找信息时，Agent会自动搜索本地文档
  - 分享你的偏好，Agent会记住它们
"""
    print(help_text)


async def handle_command(agent: Agent, command: str) -> bool:
    """
    处理特殊命令
    
    Returns:
        True 表示继续对话，False 表示退出
    """
    cmd = command.lower().strip()
    
    if cmd == "/quit" or cmd == "/exit":
        print("\n再见！👋")
        return False
    
    elif cmd == "/clear":
        agent.reset_conversation()
        print("\n✅ 对话历史已清空\n")
    
    elif cmd == "/memory":
        profile = await agent.get_user_profile()
        print("\n📝 用户记忆：")
        if any(profile.values()):
            for key, values in profile.items():
                if values:
                    print(f"  {key}:")
                    for v in values:
                        print(f"    - {v}")
        else:
            print("  (暂无记忆)")
        print()
    
    elif cmd == "/history":
        history = agent.get_conversation_history()
        print("\n📜 对话历史：")
        if history:
            for msg in history:
                role = "👤 用户" if msg["role"] == "user" else "🤖 助手"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                print(f"  {role}: {content}")
        else:
            print("  (暂无历史)")
        print()
    
    elif cmd == "/help":
        print_help()
    
    elif cmd == "/reload":
        from agent.tools import ToolRegistry
        search_tool = ToolRegistry.get("search_documents")
        if search_tool:
            search_tool.reload_documents()
            print("\n✅ 文档已重新加载\n")
        else:
            print("\n❌ 搜索工具未启用\n")
    
    else:
        print(f"\n❓ 未知命令: {command}")
        print("输入 /help 查看可用命令\n")
    
    return True


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="通用对话Agent")
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic", "deepseek", "zhipu", "qwen"],
        default=None,
        help="LLM Provider"
    )
    parser.add_argument(
        "--docs",
        type=str,
        default="./data/docs",
        help="文档搜索路径"
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="禁用记忆功能"
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="禁用工具功能"
    )
    
    args = parser.parse_args()
    
    # 确定LLM Provider
    llm_provider = None
    if args.provider:
        llm_provider = LLMProvider(args.provider)
    
    # 检查可用的Provider
    available = settings.list_available_providers()
    if not available:
        print("\n❌ 错误: 未配置任何LLM API Key")
        print("请设置以下环境变量之一：")
        print("  - OPENAI_API_KEY")
        print("  - ANTHROPIC_API_KEY")
        print("  - DEEPSEEK_API_KEY")
        print("  - ZHIPU_API_KEY")
        print("  - QWEN_API_KEY")
        return
    
    if llm_provider and llm_provider not in available:
        print(f"\n❌ 错误: {llm_provider.value} 未配置API Key")
        print(f"可用的Provider: {[p.value for p in available]}")
        return
    
    # 打印欢迎信息
    print_banner()
    
    # 显示当前配置
    current_provider = llm_provider or settings.agent_settings.default_llm_provider
    if current_provider in available:
        config = settings.get_llm_config(current_provider)
        print(f"当前模型: {current_provider.value} ({config.model_name})")
    else:
        # 使用第一个可用的provider
        current_provider = available[0]
        config = settings.get_llm_config(current_provider)
        print(f"当前模型: {current_provider.value} ({config.model_name})")
        llm_provider = current_provider
    
    print(f"文档路径: {args.docs}")
    print(f"记忆功能: {'启用' if not args.no_memory else '禁用'}")
    print(f"工具功能: {'启用' if not args.no_tools else '禁用'}")
    print("\n" + "="*60 + "\n")
    
    # 创建Agent
    agent = Agent(
        llm_provider=llm_provider,
        enable_memory=not args.no_memory,
        enable_tools=not args.no_tools,
        docs_path=args.docs,
    )
    
    # 设置工具调用回调
    def on_tool_call(name, args):
        print(f"\n🔧 调用工具: {name}")
    
    def on_tool_result(name, result):
        # 截断过长的结果
        display = result[:200] + "..." if len(result) > 200 else result
        print(f"📋 工具结果: {display}\n")
    
    agent.on_tool_call = on_tool_call
    agent.on_tool_result = on_tool_result
    
    # 主对话循环
    while True:
        try:
            user_input = input("👤 你: ").strip()
            
            if not user_input:
                continue
            
            # 处理命令
            if user_input.startswith("/"):
                should_continue = await handle_command(agent, user_input)
                if not should_continue:
                    break
                continue
            
            # 获取回复
            print("\n🤖 助手: ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\n再见！👋")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            print("请重试或输入 /quit 退出\n")


if __name__ == "__main__":
    asyncio.run(main())
