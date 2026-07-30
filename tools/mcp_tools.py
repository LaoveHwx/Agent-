"""
MCP 客户端：统一拉取多个 MCP 服务端的工具。

注意：get_mcp_tools 为 async，graph 全程走 ainvoke。
"""
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

# # 配置连接本地自建 MCP 服务的信息
# station_mcp_config = {
#     "url": "http://localhost:8848/streamable",
#     "transport": "streamable-http",
# }
# 魔搭社区工具 MCP
# 1.
chart_mcp_config = {
    "url": "https://mcp.api-inference.modelscope.ai/3ab2a73a151d45/mcp",
    "transport": "streamable-http",
}
# 2.


# 创建客户端：可同时连多个 MCP 服务端
# tool_name_prefix=True 会给工具名加 "服务名_" 前缀，防止多 server 工具名冲突。
client = MultiServerMCPClient(
    {
        # "station_mcp": station_mcp_config,
        "chart_mcp": chart_mcp_config,
    },
    tool_name_prefix=True,
)


# 魔搭 chart_mcp 共 27 个图表工具，全绑给模型会撑爆工具 schema、干扰路由，按需筛留。
# chart_mcp_ 前缀（由 tool_name_prefix=True 产生）。
WANTED_MCP_TOOLS = {
    # -- 核心保留（覆盖大部分数据分析需求）--
    "chart_mcp_generate_column_chart",     # 柱状：类别数值比较
    "chart_mcp_generate_line_chart",       # 折线：时间趋势
    "chart_mcp_generate_pie_chart",        # 饼图：占比
    "chart_mcp_generate_scatter_chart",    # 散点：两变量关系
    "chart_mcp_generate_bar_chart",        # 条形：类别名长时
    "chart_mcp_generate_spreadsheet",      # 表格/透视表
    "chart_mcp_generate_dual_axes_chart",  # 双轴：两指标同图
    "chart_mcp_generate_histogram_chart",  # 直方图：数据分布
    # -- 按需（业务相关再开）--
    "chart_mcp_generate_funnel_chart",     # 漏斗：阶段转化
    "chart_mcp_generate_waterfall_chart",  # 瀑布：累计增减（财务）
}


async def get_mcp_tools():
    """拉取所有已配置 MCP 服务的工具，按白名单 WANTED_MCP_TOOLS 过滤后返回。"""
    tools = await client.get_tools()
    return [t for t in tools if t.name in WANTED_MCP_TOOLS]


async def _main():
    """打印当前可用的所有 MCP 工具，供联调使用。"""
    tools = await get_mcp_tools()
    if not tools:
        print("（未获取到任何 MCP 工具，请确认 station_mcp 与魔搭服务已启动且 url 正确）")
        return
    print('\n'.join(f"{i}. {t.name} - {t.description}" for i, t in enumerate(tools)))


if __name__ == '__main__':
    asyncio.run(_main())
