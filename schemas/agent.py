"""
Agent的数据契约：分析请求/响应的统一格式。
"""
from typing import Any

from pydantic import BaseModel, Field


class AgentAnalyzeRequest(BaseModel):
    """
    输入统一格式，校验输入格式
    验证规则：
        question: 必填，长度限制 1-1000 字符，不能为空字符串
        session_id: 可选，如提供则长度限制 1-100 字符
    """
    question: str = Field(..., min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, min_length=1, max_length=100)


class AgentAnalyzeResponse(BaseModel):
    """
    Agent 分析响应数据类，用于统一数据格式,校验格式
    描述：
        作为 Agent 引擎各节点间传递数据的统一格式，涵盖从用户提问、
        任务规划、数据检索、分析推理到最终回答的完整链路。
    """
    task_id: str # 任务编号
    session_id: str # 对话编号
    question: str  # 问题

    task_type: str | None = None #任务类型
    route: str | None = None  # 节点
    plan: list[str] = Field(default_factory=list)  # 计划步骤

    sql: str | None = None # sql查询语句
    sql_result: dict[str, Any] | None = None # sql查询结果

    rag_context: list[dict[str, Any]] = Field(default_factory=list)
    # RAG检索增强上下文

    analysis: str | None = None # 中间推理内容
    final_answer: str | None = None # 最终答案
    status: str | None = None # 任务状态
    errors: list[str] = Field(default_factory=list) # 错误信息列表
