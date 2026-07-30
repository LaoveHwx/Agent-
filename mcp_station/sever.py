"""
自建 MCP 服务端：放自己写的工具。

这些工具经 FastMCP 暴露为本地 MCP server，与远程 MCP一起
被 tools/mcp_tools.py的 MultiServerMCPClient 统一拉取，agent 不感知差异。

启动：
    直接运行本文件
    服务地址：http://localhost:8848/streamable  （streamable-http）
"""
from fastmcp import FastMCP

mcp = FastMCP(name="station_mcp", instructions="绘图自建工具服务端")


if __name__ == '__main__':
    mcp.run(
        transport="streamable-http",
        host="localhost",  # 本地测试，打包再用 0.0.0.0
        port=8848,
        path="/streamable",
        log_level="debug",
    )
