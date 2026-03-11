# eq_storage MCP Server

Minimal MCP server for:
- upsert from files (`methods`, `params`, `files`)
- fetch by `entry_id`
- graph from all user methods
- delete single method or all user entries

## Hosted MCP (Streamable HTTP)

The project exposes a hosted MCP server using the official `mcp` library and Streamable HTTP transport.

### Install deps in root venv

```bash
pip install -r r.txt
```

### Start hosted MCP

```bash
python -m mcp_server.mcp_routes --host 0.0.0.0 --port 8787 --path /mcp
```

Environment variable overrides:

- `MCP_HOST` (default `0.0.0.0`)
- `MCP_PORT` (default `8787`)
- `MCP_PATH` (default `/mcp`)
- `MCP_STATELESS_HTTP` (default `true`)

### Validate with MCP Inspector

```bash
npx @modelcontextprotocol/inspector@latest --server-url http://localhost:8787/mcp --transport http
```

## MCP Tools

- `upsert(user_id, files?, equation?, module_id?)`
- `entry_get(entry_id, table?, user_id?)`
- `graph_get(user_id, test?)`
- `entries_delete(user_id, table?, entry_id?)`

Backward-compatible aliases:

- `graph(...)` -> `graph_get(...)`
- `delete(...)` -> `entries_delete(...)`

## Minimal flow

```mermaid
flowchart LR
    client[Client]
    mcp[MCP Tool Calls]
    service[ServerService]
    extract[File/Equation Extraction]
    db[(DuckDB methods params files)]
    graph[Graph Build with GUtils]
    response[JSON Response]

    client --> mcp
    mcp --> service
    service --> extract
    extract --> db
    service --> graph
    db --> graph
    service --> response
```

## Example payloads

`upsert`

```json
{
  "user_id": "u1",
  "module_id": "m1",
  "files": ["eT14KzIKej14Kng="],
  "equation": "f = m * a"
}
```

`graph_get`

```json
{"user_id": "u1"}
```
