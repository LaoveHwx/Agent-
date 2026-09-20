"""
MCP 客户端：统一拉取自建 station_mcp 与远程 chart_mcp 的工具。

自建 station_mcp（数值计算）与远程 chart_mcp（图表）各自独立 client，
单 server 连不上不影响另一侧；get_mcp_tools 为 async，graph 全程走 ainvoke。
"""
import os
import time

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.logger import setup_logger

logger = setup_logger(__name__)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _create_direct_mcp_http_client(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    """Create an MCP HTTP client that ignores system proxy settings."""
    verify_ssl = _env_bool("CHART_MCP_VERIFY_SSL", False)
    kwargs = {
        "follow_redirects": True,
        "trust_env": False,
        "verify": verify_ssl,
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    if headers is not None:
        kwargs["headers"] = headers
    if auth is not None:
        kwargs["auth"] = auth
    return httpx.AsyncClient(**kwargs)

# 自建本地 MCP server：数值计算通用工具
# （compute_statistics / calculate_growth_rate / format_number，见 mcp_station/sever.py）
station_mcp_config = {
    "url": os.getenv("STATION_MCP_URL", "http://localhost:8848/streamable"),
    "transport": "streamable-http",
}
# 魔搭社区图表 MCP
chart_mcp_url = os.getenv("CHART_MCP_URL", "").strip()
chart_mcp_config = {
    "url": chart_mcp_url,
    "transport": "streamable-http",
    "httpx_client_factory": _create_direct_mcp_http_client,
} if chart_mcp_url else None

# 各 server 独立 client，避免单 server 连不上拖垮全局工具拉取
_station_client = MultiServerMCPClient({"station_mcp": station_mcp_config}, tool_name_prefix=True)
_chart_client = (
    MultiServerMCPClient({"chart_mcp": chart_mcp_config}, tool_name_prefix=True)
    if chart_mcp_config else None
)


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

MCP_TOOLS_CACHE_SECONDS = 300
_cached_tools: list = []
_cached_at = 0.0


async def _safe_get_tools(client: MultiServerMCPClient, server_tag: str):
    """拉取单个 MCP server 的工具，失败降级为空列表并告警，不阻断其余 server。"""
    try:
        return await client.get_tools()
    except Exception as exc:
        logger.warning("MCP 工具拉取失败 server=%s err=%r", server_tag, exc, exc_info=True)
        return []


async def get_mcp_tools():
    """拉取自建 + 远程 MCP 工具，按白名单过滤后返回；单 server 失败不阻断其余。"""
    global _cached_tools, _cached_at
    now = time.monotonic()
    if _cached_tools and now - _cached_at < MCP_TOOLS_CACHE_SECONDS:
        return _cached_tools

    tools: list = []
    tools += await _safe_get_tools(_station_client, "station_mcp")
    if _chart_client is not None:
        tools += await _safe_get_tools(_chart_client, "chart_mcp")
    selected_tools = [t for t in tools if t.name in WANTED_MCP_TOOLS]
    if selected_tools:
        _cached_tools = selected_tools
        _cached_at = now
    return selected_tools


# ---------------------------------------------------------------------------
# 自测：直接运行本文件即可分别探测两个 MCP server 的连通性与工具拉取情况。
#   python tools/mcp_tools.py
# 输出：每个 server 是否连上、可用工具列表、白名单命中/缺失明细。
# ---------------------------------------------------------------------------
# if __name__ == "__main__":
#     import asyncio
#     import traceback

#     PROBE_TIMEOUT_SECONDS = 30

#     def _format_exception(exc: BaseException) -> str:
#         lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
#         return "".join(lines).rstrip()

#     async def _probe(client: MultiServerMCPClient, tag: str):
#         print(f"\n===== {tag} =====")
#         try:
#             tools = await asyncio.wait_for(client.get_tools(), timeout=PROBE_TIMEOUT_SECONDS)
#         except Exception as exc:
#             print(f"[失败] {type(exc).__name__}: {exc}")
#             print(_format_exception(exc))
#             return []
#         print(f"[连通] 拉取到 {len(tools)} 个工具:")
#         for t in tools:
#             print(f"  - {t.name}")
#         return tools

#     async def _main() -> None:
#         station_tools = await _probe(_station_client, "station_mcp (本地 8848)")
#         chart_tools = await _probe(_chart_client, "chart_mcp (魔搭远程)")

#         names = {t.name for t in station_tools + chart_tools}
#         print("\n===== 白名单命中情况 =====")
#         wanted = sorted(WANTED_MCP_TOOLS)
#         missing = [n for n in wanted if n not in names]
#         for name in wanted:
#             print(f"  {'[OK]  ' if name in names else '[MISS]'} {name}")
#         if missing:
#             print(f"\n共 {len(missing)}/{len(wanted)} 个白名单工具缺失。")
#             print("提示：station_mcp 缺失通常是本地服务未启动（python mcp_station/sever.py）；")
#             print("      chart_mcp 缺失通常是网络/鉴权/服务端问题，看上方 [失败] 行的具体异常。")
#         else:
#             print("\n白名单工具全部就绪。")

#     asyncio.run(_main())
