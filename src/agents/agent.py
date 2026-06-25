import os
import json
from typing import Annotated, Sequence, Union
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, AnyMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40


def _windowed_messages(
    old: Union[Sequence[BaseMessage], Sequence[AnyMessage]], 
    new: Union[Sequence[BaseMessage], Sequence[AnyMessage]]
) -> Sequence[AnyMessage]:
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    result = add_messages(old, new)
    return list(result)[-MAX_MESSAGES:]


class AgentState(MessagesState):
    pass


def build_agent(ctx=None):
    """
    构建毛球医生（FluffDoc）宠物健康顾问 Agent
    
    Args:
        ctx: 请求上下文，用于链路追踪
        
    Returns:
        配置好的 Agent 实例
    """
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    # 创建 LLM 实例
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )

    # 构建 Agent
    agent = create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=[],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
    
    return agent
