# MCPMaster Multi-Client Config

`MCPMaster` now generates client-specific MCP config artifacts from one canonical
service registry.

## Canonical Source

- `services/mcp_services.json` is the single source of truth for MCP services.
- Service entries support command-based and URL-based transports.
- Environment values are stored as placeholders (for example `${MCP_PORT}`) by
  default to avoid committing secrets.

## Generated Outputs

All generated files are written under `clients/`:

- `clients/cursor/mcp.json`
- `clients/gemini/gemini-extension.json`
- `clients/gemini/GEMINI.md`
- `clients/gemini/settings.json`
- `clients/claude/claude_desktop_config.json`
- `clients/openai/openai_connector_manifest.json`
- `clients/openai/app_submission_manifest.json`

## Usage

Programmatic:

```python
from _admin.mcp_master import MCPMaster

master = MCPMaster()
result = master.generate_multi_client_configs(resolve_env=False)
print(result)
```

Validation:

```python
report = master.validate_generated_configs()
print(report)
```

## Auto-Discovery for FastMCP Tools

`_admin.mcp_master.mcp_server.main.create_mcp_server()` now performs automatic tool discovery and registration:

- Classes must contain `MCP` in the class name.
- Classes and methods starting with `_` are ignored.
- Methods are introspected for signatures, type hints, docstrings, and inline comments.
- Discovered methods are registered as FastMCP tools with stable names.
- A read-only tool `mcp_master_tools_manifest` exposes source mapping and derived input schemas.
