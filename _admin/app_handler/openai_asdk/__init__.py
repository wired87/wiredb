"""
OpenAI Apps SDK integration for BestBrain.

Publishes the project as a ChatGPT app via MCP (Model Context Protocol),
wrapped in Docker, and ready for OpenAI App Store submission.

Ref: https://developers.openai.com/apps-sdk/
"""

from _admin.app_handler.openai_asdk.app_publisher import (
    AppMetadata,
    AppPublisher,
    CSPConfig,
    ToolAnnotation,
)
from _admin.app_handler.openai_asdk.config import (
    AppConfig,
    MCPConfig,
    get_demo_paths,
    get_demo_video_path,
)
from _admin.app_handler.openai_asdk.workflow import run_workflow

__all__ = [
    "AppConfig",
    "AppMetadata",
    "AppPublisher",
    "CSPConfig",
    "MCPConfig",
    "ToolAnnotation",
    "get_demo_paths",
    "get_demo_video_path",
    "run_workflow",
]
