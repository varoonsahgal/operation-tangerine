# MCP configs

Lab 3.4 / 3.5 write `my-mcp.json` here, and `labctl break mcp-config` writes
`broken-mcp.json` here. Both contain your account's ARNs, so they are git-ignored.

Print a known-good config (spoiler!) with:

    python3 labctl/labctl.py mcp-json            # Kiro / Claude Code / Amazon Q format
    python3 labctl/labctl.py mcp-json --client vscode
