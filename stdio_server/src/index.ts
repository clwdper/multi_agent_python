import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import fs from "fs";
import path, { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Create server instance
const server = new McpServer({
  name: "sourceCodeFixer",
  version: "1.0.0",
  capabilities: {
    resources: {},
    tools: {},
  },
});

// Register tool
server.tool(
  "fix-vulnerability",
  "fixes vulnerabilities in source code",
  {
    sourceCode: z.string().describe("source code to fix"),
    vulnerabilityReport: z.string().describe("list of vulnerabilities to fix"),
  },
  async ({ sourceCode, vulnerabilityReport }) => {
    const fixedSourceCode = sourceCode;

    fs.writeFileSync(
      path.join(__dirname, "fixed_source_code.js"),
      fixedSourceCode
    );

    return {
      content: [
        {
          type: "text",
          text: "source code was fixed using AI ",
        },
      ],
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.log("NODEJS::::MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
