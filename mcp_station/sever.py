"""
自建 MCP 服务端：数值计算通用工具（Skill）。

这些工具经 FastMCP 暴露为本地 MCP server，与远程 chart_mcp 一起
被 tools/mcp_tools.py 的 MultiServerMCPClient 统一拉取，agent 不感知差异。

启动：
    直接运行本文件
    服务地址：http://localhost:8848/streamable  （streamable-http）

工具：
    compute_statistics      统计描述（均值/中位数/标准差/求和/最值/计数）
    calculate_growth_rate   增长率/环比计算
    format_number           数值格式化（千分位/百分比/固定小数位）
"""
from statistics import mean, median, stdev
from typing import Annotated

from fastmcp import FastMCP

mcp = FastMCP(
    name="station_mcp",
    instructions="企业数据分析自建工具服务端：数值计算通用 Skill",
)


@mcp.tool
def compute_statistics(
    numbers: Annotated[list[float], "待统计的数值序列，如 [10, 20, 30, 40]"],
) -> dict:
    """计算数值序列的统计描述：均值、中位数、标准差、求和、最小值、最大值、计数。

    SQL 拿到原始数值后，交给本工具做集中趋势与离散程度计算，避免大模型手算出错。
    """
    nums = [float(n) for n in numbers if n is not None]
    if not nums:
        return {"error": "numbers is empty"}
    return {
        "count": len(nums),
        "sum": sum(nums),
        "mean": mean(nums),
        "median": median(nums),
        "stdev": stdev(nums) if len(nums) >= 2 else 0.0,
        "min": min(nums),
        "max": max(nums),
    }


@mcp.tool
def calculate_growth_rate(
    current: Annotated[float, "本期数值"],
    previous: Annotated[float, "上期数值（基期）"],
) -> dict:
    """计算增长率/环比：本期相对上期的增长率、增长率百分比与绝对增量。

    基期为 0 时增长率无定义，返回 None 并给出说明，避免除零。
    """
    delta = current - previous
    if previous == 0:
        return {
            "current": current,
            "previous": previous,
            "delta": delta,
            "growth_rate": None,
            "growth_rate_pct": None,
            "note": "基期为 0，增长率无法计算",
        }
    rate = delta / previous
    return {
        "current": current,
        "previous": previous,
        "delta": delta,
        "growth_rate": rate,
        "growth_rate_pct": f"{rate * 100:.2f}%",
    }


@mcp.tool
def format_number(
    value: Annotated[float, "待格式化的数值"],
    format_type: Annotated[str, "格式类型：thousands(千分位) / percent(百分比) / fixed(固定小数位)"] = "thousands",
    decimals: Annotated[int, "保留小数位"] = 2,
) -> str:
    """数值格式化：千分位、百分比（传入小数，如 0.1234 -> 12.34%）、或固定小数位。

    用于把 SQL/统计结果整理成可读的展示文本。
    """
    if format_type == "percent":
        return f"{value * 100:.{decimals}f}%"
    if format_type == "thousands":
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="localhost",  # 本地测试，打包再用 0.0.0.0
        port=8848,
        path="/streamable",
        log_level="debug",
    )
