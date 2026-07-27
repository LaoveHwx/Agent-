from utils.llm_client import chat_completion


ANALYST_SYSTEM_PROMPT = """
你是企业数据分析系统中的 Analyst Agent。
你需要结合 SQL 查询结果和 RAG 业务知识，输出清晰、可解释、可追溯的业务分析结论。
如果信息不足，要明确说明缺口，不要编造数据。
"""


def run_analyst_agent(state: dict) -> dict:
    question = state.get("question", "")
    sql_result = state.get("sql_result")
    rag_context = state.get("rag_context", [])
    errors = state.get("errors", [])

    user_prompt = f"""
用户问题：
{question}

SQL结果：
{sql_result}

知识库上下文：
{rag_context}

已有错误：
{errors}

请输出最终分析结论。
"""
    content = chat_completion(ANALYST_SYSTEM_PROMPT, user_prompt, temperature=0.2)
    if content:
        return {"final_answer": content}

    answer_parts = [f"问题：{question}"]
    if sql_result:
        answer_parts.append(
            f"SQL 查询已执行，返回 {sql_result.get('row_count', 0)} 行数据。"
        )
    if rag_context:
        answer_parts.append(f"知识库检索命中 {len(rag_context)} 条。")
    if errors:
        answer_parts.append("当前链路存在问题：" + "；".join(errors))
    if not sql_result and not rag_context:
        answer_parts.append("当前缺少可用于分析的数据结果或知识库上下文。")

    return {"final_answer": "\n".join(answer_parts)}
