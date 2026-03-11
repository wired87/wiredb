"""
Global registry for WebSocket connections: frontend clients and GPU links per env.
Used by Relay for LIVE_DATA relay and cleanup.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional, Set

# Key: (user_id, env_id) or env_id string for shared env
def _channel_key(user_id: Optional[str], env_id: Optional[str]) -> str:
    if user_id and env_id:
        return f"{user_id}:{env_id}"
    return str(env_id or user_id or "default")


class LiveDataRegistry:
    """
    Registry of frontend clients and GPU WebSocket per channel (user_id:env_id).
    Thread-safe for async; one registry instance shared by Relay.
    """

    def __init__(self):
        self._channels: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    def _ensure_channel(self, channel: str) -> dict:
        if channel not in self._channels:
            self._channels[channel] = {
                "gpu_ws": None,
                "qdash": None,
                "grid": None,
                "created_at": time.time(),
                "last_frame_id": None,
            }
        return self._channels[channel]

    async def register_con(self, user_id: Optional[str], consumer: Any, con:"qdash" or "grid", env_id: Optional[str]=None) -> None:
        """Add a frontend Relay consumer to the channel so it receives LIVE_DATA."""
        async with self._lock:
            if env_id:
                ch = _channel_key(user_id, env_id)
            else:
                ch = user_id
            entry = self._ensure_channel(ch)
            entry[con] = consumer

    async def unregister_con(self, consumer: Any, con:"qdash" or "grid") -> None:
        """Remove a frontend consumer from all channels (on disconnect)."""
        async with self._lock:
            for entry in self._channels.values():
                entry[con] = None

    async def register_gpu(
        self,
        user_id: Optional[str],
        env_id: Optional[str],
        consumer: Any,
    ) -> None:
        """Register this connection as the GPU link for the channel."""
        async with self._lock:
            ch = _channel_key(user_id, env_id)
            entry = self._ensure_channel(ch)
            entry["gpu_ws"] = consumer

    async def unregister_gpu(self, consumer: Any) -> Optional[str]:
        """Remove GPU registration for the channel that had this consumer. Returns channel key if found."""
        async with self._lock:
            for ch, entry in list(self._channels.items()):
                if entry.get("gpu_ws") is consumer:
                    entry["gpu_ws"] = None
                    return ch
        return None

    async def get_clients_for_channel(self, user_id: Optional[str], env_id: Optional[str]) -> Set[Any]:
        """Return set of frontend consumers for this channel (copy)."""
        async with self._lock:
            ch = _channel_key(user_id, env_id)
            entry = self._channels.get(ch)
            if not entry:
                return set()
            return set(entry["clients"])

    async def cleanup_empty(self) -> None:
        """Remove channels that have no clients and no GPU."""
        async with self._lock:
            for ch in list(self._channels.keys()):
                e = self._channels[ch]
                if not e["clients"] and e.get("gpu_ws") is None:
                    del self._channels[ch]


# Singleton used by Relay
live_data_registry = LiveDataRegistry()
