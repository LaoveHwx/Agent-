"""
任务分类 + 步骤生成
"""
from schemas.planner import PlannerRequest, PlannerResponse


def create_plan(request: PlannerRequest) -> PlannerResponse:
    question = request.question.strip()
    task_type = "complex_analysis"

    if any(keyword in question for keyword in ("是什么意思", "定义", "口径", "规则")):
        task_type = "knowledge_query"
        steps = [
            "识别业务知识问题",
            "检索企业知识库",
            "整理来源并生成回答",
        ]
    elif any(keyword in question for keyword in ("查询", "统计", "排名", "最高", "最低", "多少", "销售额", "订单数")):
        task_type = "data_query"
        steps = [
            "识别结构化数据查询问题",
            "读取数据库表结构",
            "生成并执行只读 SQL",
            "整理查询结果",
        ]
    else:
        steps = [
            "理解用户业务问题",
            "拆解复杂分析任务",
            "准备调用 SQL 和 RAG 工具",
            "汇总分析结论",
        ]

    return PlannerResponse(
        question=question,
        task_type=task_type,
        steps=steps,
    )
