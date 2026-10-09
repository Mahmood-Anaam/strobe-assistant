"""Local entry point for the MCP service."""

import uvicorn


def main() -> None:
    uvicorn.run("strobe_assistant.mcp_app:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
