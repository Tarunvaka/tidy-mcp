"""MCP server: thin wrapper over tidy_mcp.core."""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("tidy")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
