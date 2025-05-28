# Multi-Agent Team Agents

This repository contains a multi-agent system with both Python and Node.js components.

## Python Multi-Agent Runner

To run the main multi-agent system:

```sh
uv run main.py
```

## Node.js MCP Stdio Server

The stdio MCP server is implemented in TypeScript and can be found in `stdio_server/`.

### Install dependencies

```sh
cd stdio_server
npm install
```

### Build the server

```sh
npm run build
```

### Run the server

```sh
node build/index.js
```

---

- Python code is in the root and `app/` directories.
- Node.js MCP server code is in `stdio_server/`.
- See `requirements.txt` and `pyproject.toml` for Python dependencies.
- See `stdio_server/package.json` for Node.js dependencies.


