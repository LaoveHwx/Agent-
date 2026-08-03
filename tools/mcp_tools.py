"""
MCP 客户端：统一拉取自建 station_mcp 与远程 chart_mcp 的工具。

自建 station_mcp（数值计算）与远程 chart_mcp（图表）各自独立 client，
单 server 连不上不影响另一侧；get_mcp_tools 为 async，graph 全程走 ainvoke。
"""
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.logger import setup_logger

logger = setup_logger(__name__)

# 自建本地 MCP server：数值计算通用工具
# （compute_statistics / calculate_growth_rate / format_number，见 mcp_station/sever.py）
station_mcp_config = {
    "url": "http://localhost:8848/streamable",
    "transport": "streamable-http",
}
# 魔搭社区图表 MCP
chart_mcp_config = {
    "url": "https://mcp.api-inference.modelscope.ai/3ab2a73a151d45/mcp",
    "transport": "streamable-http",
}

# 各 server 独立 client，避免单 server 连不上拖垮全局工具拉取
_station_client = MultiServerMCPClient({"station_mcp": station_mcp_config}, tool_name_prefix=True)
_chart_client = MultiServerMCPClient({"chart_mcp": chart_mcp_config}, tool_name_prefix=True)


# 工具白名单：全量绑定会撑爆工具 schema、干扰路由，按需筛留。
# tool_name_prefix=True 会给工具名加 "服务名_" 前缀。
WANTED_MCP_TOOLS = {
    # 自建数值计算 Skill
    "station_mcp_compute_statistics",
    "station_mcp_calculate_growth_rate",
    "station_mcp_format_number",
    # 远程图表（覆盖大部分数据分析需求）
    "chart_mcp_generate_column_chart",     # 柱状：类别数值比较
    "chart_mcp_generate_line_chart",       # 折线：时间趋势
    "chart_mcp_generate_pie_chart",        # 饼图：占比
    "chart_mcp_generate_scatter_chart",    # 散点：两变量关系
    "chart_mcp_generate_bar_chart",        # 条形：类别名长时
    "chart_mcp_generate_spreadsheet",      # 表格/透视表
    "chart_mcp_generate_dual_axes_chart",  # 双轴：两指标同图
    "chart_mcp_generate_histogram_chart",  # 直方图：数据分布
}


async def _safe_get_tools(client: MultiServerMCPClient, server_tag: str):
    """拉取单个 MCP server 的工具，失败降级为空列表并告警，不阻断其余 server。"""
    try:
        return await client.get_tools()
    except Exception as exc:
        logger.warning("MCP 工具拉取失败 server=%s err=%s", server_tag, exc)
        return []


async def get_mcp_tools():
    """拉取自建 + 远程 MCP 工具，按白名单过滤后返回；单 server 失败不阻断其余。"""
    tools: list = []
    tools += await _safe_get_tools(_station_client, "station_mcp")
    tools += await _safe_get_tools(_chart_client, "chart_mcp")
    return [t for t in tools if t.name in WANTED_MCP_TOOLS]