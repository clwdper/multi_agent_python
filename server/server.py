# File server.py

import contextlib
import logging
from collections.abc import AsyncIterator

import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send
import uvicorn

logger = logging.getLogger(__name__)


app = Server("mcp-streamable-http-stateless-demo")


@app.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    # Check if the tool is extract-wikipedia-article
    if name == "extract-wikipedia-article":
        # Return dummy content for the Wikipedia article
        return [
            types.TextContent(
                type="text",
                text="This is the article ...",
            )
        ]

    # For other tools, keep the existing notification logic
    ctx = app.request_context
    interval = arguments.get("interval", 1.0)
    count = arguments.get("count", 5)
    caller = arguments.get("caller", "unknown")

    # Send the specified number of notifications with the given interval
    for i in range(count):
        await ctx.session.send_log_message(
            level="info",
            data=f"Notification {i + 1}/{count} from caller: {caller}",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )
        if i < count - 1:  # Don't wait after the last notification
            await anyio.sleep(interval)

    return [
        types.TextContent(
            type="text",
            text=(
                f"Sent {count} notifications with {interval}s interval"
                f" for caller: {caller}"
            ),
        )
    ]


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="extract-wikipedia-article",
            description=("Extracts the main content of a Wikipedia article"),
            inputSchema={
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the Wikipedia article to extract",
                    },
                },
            },
        )
    ]


session_manager = StreamableHTTPSessionManager(
    app=app,
    event_store=None,
    stateless=True,
)


async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
    await session_manager.handle_request(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette) -> AsyncIterator[None]:
    """Context manager for session manager."""
    async with session_manager.run():
        logger.info("Application started with StreamableHTTP session manager!")
        try:
            yield
        finally:
            logger.info("Application shutting down...")


app = Starlette(
    debug=True,
    routes=[
        Mount("/mcp", app=handle_streamable_http),
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=3000)
