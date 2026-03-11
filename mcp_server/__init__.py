from mcp_server.mcp_routes import create_mcp_server


def create_app():
    # Lazy import avoids creating the app as a package import side-effect.
    from mcp_server.app import create_app as _create_app

    return _create_app()


def __getattr__(name: str):
    if name == "app":
        # Keep compatibility for callers importing `mcp_server.app`.
        from mcp_server.app import app as _app

        return _app
    raise AttributeError(f"module 'mcp_server' has no attribute '{name}'")


__all__ = ["app", "create_app", "create_mcp_server"]
