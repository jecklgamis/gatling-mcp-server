# Connecting Clients

## Claude Code

Once the server is running, register it as a project-scoped MCP server in any repo you work from (e.g.
[gatling-scala-example](https://github.com/jecklgamis/gatling-scala-example) or
[gatling-java-example](https://github.com/jecklgamis/gatling-java-example)):

```bash
cd /path/to/gatling-scala-example
claude mcp add --transport http gatling-mcp-server http://localhost:58090/gatling_mcp -s project \
  -H "Authorization: Bearer \${GATLING_MCP_API_TOKEN}"
```

This writes a `.mcp.json` in that repo:

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "type": "http",
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer ${GATLING_MCP_API_TOKEN}"
      }
    }
  }
}
```

`${GATLING_MCP_API_TOKEN}` is expanded from your own shell environment at connect time, not stored literally - so
`.mcp.json` itself contains no secret and is safe to commit and share with the team. Whoever opens Claude Code in
that repo just needs `GATLING_MCP_API_TOKEN` set in their own environment; they're then prompted to trust/enable the
`gatling-mcp-server` server automatically. Run `claude mcp list` to confirm it connects.

Omit `-s project` (or use `-s user`) to register it in your personal config instead, if you'd rather it be available
across every project rather than shared via the repo.

## Other MCP Clients

Any MCP client that supports the streamable-http transport can call this server the same way - point it at
`http://localhost:58090/gatling_mcp` with an `Authorization: Bearer <GATLING_MCP_API_TOKEN>` header. A few common
ones:

**Claude Desktop** - add to `claude_desktop_config.json` (Settings -> Developer -> Edit Config):

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "type": "http",
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

**Cursor** - add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

**Windsurf** - add to `~/.codeium/windsurf/mcp_config.json` (Windsurf Settings -> Cascade -> MCP Servers -> View raw
config), same shape as Cursor's above.

**Cline** (VS Code extension) - open the MCP Servers panel -> Configure MCP Servers, which opens
`cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "type": "streamableHttp",
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

**Gemini CLI** - add via `gemini mcp add`, or edit `~/.gemini/settings.json` (global) / `.gemini/settings.json`
(project) directly. Gemini CLI distinguishes streamable-http servers with `httpUrl` (as opposed to `url`, which is
SSE):

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "httpUrl": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

or equivalently: `gemini mcp add --transport http gatling-mcp-server http://localhost:58090/gatling_mcp -H "Authorization: Bearer <GATLING_MCP_API_TOKEN>"`.

**JetBrains AI Assistant** (IntelliJ IDEA, PyCharm, etc.) - Settings -> Tools -> AI Assistant -> Model Context
Protocol (MCP) -> Add, then switch the dialog to "As JSON":

```json
{
  "mcpServers": {
    "gatling-mcp-server": {
      "url": "http://localhost:58090/gatling_mcp",
      "headers": {
        "Authorization": "Bearer <GATLING_MCP_API_TOKEN>"
      }
    }
  }
}
```

Unlike Claude Code's `${GATLING_MCP_API_TOKEN}` shell expansion, these clients don't expand env vars in their config
files - substitute the actual token value, and avoid committing it to a shared/project-scoped config.
