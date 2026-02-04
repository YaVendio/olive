# olive-ai TypeScript Client Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a standalone TypeScript npm package that connects to Olive servers and converts tools to Vercel AI SDK format with remote execution.

**Architecture:** The client fetches tool definitions from `/olive/tools` endpoint (JSON Schema format), wraps each as a Vercel AI `tool()` object where `execute()` calls back to `/olive/tools/call` via HTTP. No server-side changes needed.

**Tech Stack:** TypeScript, Vercel AI SDK (`ai` package), Zod (for schema validation), Vitest (testing), tsup (bundling)

---

## Repository Setup

**New repo location:** `~/Dropbox/yv/yv-stack/olive-ai/`

**Package name:** `olive-ai` (npm: `@anthropic/olive-ai` or `olive-ai`)

---

### Task 1: Initialize Repository

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `tsup.config.ts`
- Create: `.gitignore`
- Create: `README.md`

**Step 1: Create directory and initialize git**

```bash
mkdir -p ~/Dropbox/yv/yv-stack/olive-ai
cd ~/Dropbox/yv/yv-stack/olive-ai
git init
```

**Step 2: Create package.json**

```json
{
  "name": "olive-ai",
  "version": "0.1.0",
  "description": "TypeScript client for Olive tools with Vercel AI SDK integration",
  "type": "module",
  "main": "./dist/index.cjs",
  "module": "./dist/index.js",
  "types": "./dist/index.d.ts",
  "exports": {
    ".": {
      "import": "./dist/index.js",
      "require": "./dist/index.cjs",
      "types": "./dist/index.d.ts"
    }
  },
  "files": ["dist"],
  "scripts": {
    "build": "tsup",
    "dev": "tsup --watch",
    "test": "vitest",
    "test:run": "vitest run",
    "lint": "tsc --noEmit",
    "prepublishOnly": "npm run build"
  },
  "keywords": ["olive", "vercel-ai", "ai-sdk", "tools", "langchain"],
  "license": "MIT",
  "peerDependencies": {
    "ai": ">=4.0.0",
    "zod": ">=3.0.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "ai": "^4.0.0",
    "tsup": "^8.0.0",
    "typescript": "^5.0.0",
    "vitest": "^2.0.0",
    "zod": "^3.23.0"
  }
}
```

**Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

**Step 4: Create tsup.config.ts**

```typescript
import { defineConfig } from "tsup";

export default defineConfig({
  entry: ["src/index.ts"],
  format: ["cjs", "esm"],
  dts: true,
  splitting: false,
  sourcemap: true,
  clean: true,
});
```

**Step 5: Create .gitignore**

```gitignore
node_modules/
dist/
*.log
.DS_Store
```

**Step 6: Create README.md**

```markdown
# olive-ai

TypeScript client for [Olive](https://github.com/YaVendio/olive) tools with Vercel AI SDK integration.

## Installation

\`\`\`bash
npm install olive-ai ai zod
\`\`\`

## Usage

\`\`\`typescript
import { OliveClient } from "olive-ai";
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

// Create client connected to your Olive server
const olive = new OliveClient("http://localhost:8000");

// Get tools as Vercel AI SDK tools
const tools = await olive.getTools();

// Use with Vercel AI SDK
const result = await generateText({
  model: openai("gpt-4"),
  tools,
  prompt: "What's the weather in Paris?",
});
\`\`\`

## License

MIT
\`\`\`

**Step 7: Install dependencies**

```bash
npm install
```

**Step 8: Commit**

```bash
git add .
git commit -m "chore: initialize olive-ai package"
```

---

### Task 2: Define Types

**Files:**
- Create: `src/types.ts`

**Step 1: Write the types file**

```typescript
// src/types.ts

/**
 * Tool definition as returned by Olive server GET /olive/tools
 */
export interface OliveToolDefinition {
  name: string;
  description: string;
  input_schema: JsonSchema;
  output_schema?: JsonSchema;
  injections?: OliveInjection[];
  temporal?: {
    enabled: boolean;
    timeout_seconds: number;
    retry_policy: { max_attempts: number };
  };
}

/**
 * Injection definition for context parameters
 */
export interface OliveInjection {
  param: string;
  config_key: string;
  required: boolean;
}

/**
 * JSON Schema type (simplified)
 */
export interface JsonSchema {
  type?: string;
  properties?: Record<string, JsonSchema>;
  required?: string[];
  items?: JsonSchema;
  description?: string;
  default?: unknown;
  enum?: unknown[];
  anyOf?: JsonSchema[];
  oneOf?: JsonSchema[];
  allOf?: JsonSchema[];
  nullable?: boolean;
  additionalProperties?: boolean | JsonSchema;
}

/**
 * Request body for POST /olive/tools/call
 */
export interface OliveToolCallRequest {
  tool_name: string;
  arguments: Record<string, unknown>;
  context?: Record<string, unknown>;
}

/**
 * Response from POST /olive/tools/call
 */
export interface OliveToolCallResponse {
  success: boolean;
  result?: unknown;
  error?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Configuration for OliveClient
 */
export interface OliveClientConfig {
  /** Base URL of the Olive server (e.g., "http://localhost:8000") */
  baseUrl: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** Default context to inject into all tool calls */
  context?: Record<string, unknown>;
  /** Custom fetch implementation (for testing or custom environments) */
  fetch?: typeof fetch;
}
```

**Step 2: Commit**

```bash
git add src/types.ts
git commit -m "feat: add type definitions"
```

---

### Task 3: Implement Schema Converter

**Files:**
- Create: `src/schema.ts`
- Create: `src/__tests__/schema.test.ts`

**Step 1: Write the failing test**

```typescript
// src/__tests__/schema.test.ts
import { describe, it, expect } from "vitest";
import { z } from "zod";
import { jsonSchemaToZod } from "../schema";

describe("jsonSchemaToZod", () => {
  it("converts string type", () => {
    const schema = jsonSchemaToZod({ type: "string" });
    expect(schema.parse("hello")).toBe("hello");
    expect(() => schema.parse(123)).toThrow();
  });

  it("converts integer type", () => {
    const schema = jsonSchemaToZod({ type: "integer" });
    expect(schema.parse(42)).toBe(42);
  });

  it("converts number type", () => {
    const schema = jsonSchemaToZod({ type: "number" });
    expect(schema.parse(3.14)).toBe(3.14);
  });

  it("converts boolean type", () => {
    const schema = jsonSchemaToZod({ type: "boolean" });
    expect(schema.parse(true)).toBe(true);
  });

  it("converts object with properties", () => {
    const schema = jsonSchemaToZod({
      type: "object",
      properties: {
        name: { type: "string" },
        age: { type: "integer" },
      },
      required: ["name"],
    });

    expect(schema.parse({ name: "Alice", age: 30 })).toEqual({
      name: "Alice",
      age: 30,
    });
    expect(schema.parse({ name: "Bob" })).toEqual({ name: "Bob" });
    expect(() => schema.parse({ age: 30 })).toThrow();
  });

  it("converts array type", () => {
    const schema = jsonSchemaToZod({
      type: "array",
      items: { type: "string" },
    });

    expect(schema.parse(["a", "b"])).toEqual(["a", "b"]);
  });

  it("handles optional fields with defaults", () => {
    const schema = jsonSchemaToZod({
      type: "object",
      properties: {
        limit: { type: "integer", default: 10 },
      },
    });

    expect(schema.parse({})).toEqual({ limit: 10 });
  });

  it("handles description metadata", () => {
    const schema = jsonSchemaToZod({
      type: "string",
      description: "A user name",
    });

    expect(schema.description).toBe("A user name");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/schema.test.ts`
Expected: FAIL with "Cannot find module '../schema'"

**Step 3: Write the implementation**

```typescript
// src/schema.ts
import { z, type ZodTypeAny } from "zod";
import type { JsonSchema } from "./types";

/**
 * Convert JSON Schema to Zod schema for Vercel AI SDK compatibility.
 * Vercel AI SDK accepts both JSON Schema and Zod schemas for inputSchema.
 */
export function jsonSchemaToZod(schema: JsonSchema): ZodTypeAny {
  // Handle nullable
  const makeNullable = (zodSchema: ZodTypeAny): ZodTypeAny => {
    return schema.nullable ? zodSchema.nullable() : zodSchema;
  };

  // Handle description
  const withDescription = (zodSchema: ZodTypeAny): ZodTypeAny => {
    return schema.description ? zodSchema.describe(schema.description) : zodSchema;
  };

  // Handle default
  const withDefault = (zodSchema: ZodTypeAny): ZodTypeAny => {
    return schema.default !== undefined ? zodSchema.default(schema.default) : zodSchema;
  };

  const wrap = (zodSchema: ZodTypeAny): ZodTypeAny => {
    return withDefault(withDescription(makeNullable(zodSchema)));
  };

  switch (schema.type) {
    case "string":
      return wrap(z.string());

    case "integer":
    case "number":
      return wrap(z.number());

    case "boolean":
      return wrap(z.boolean());

    case "array": {
      const itemSchema = schema.items ? jsonSchemaToZod(schema.items) : z.unknown();
      return wrap(z.array(itemSchema));
    }

    case "object": {
      if (!schema.properties) {
        return wrap(z.record(z.unknown()));
      }

      const shape: Record<string, ZodTypeAny> = {};
      const required = new Set(schema.required || []);

      for (const [key, propSchema] of Object.entries(schema.properties)) {
        let fieldSchema = jsonSchemaToZod(propSchema);
        if (!required.has(key)) {
          fieldSchema = fieldSchema.optional();
        }
        shape[key] = fieldSchema;
      }

      return wrap(z.object(shape));
    }

    case "null":
      return z.null();

    default:
      // Handle anyOf, oneOf, enum, etc.
      if (schema.enum) {
        return wrap(z.enum(schema.enum as [string, ...string[]]));
      }
      if (schema.anyOf) {
        const schemas = schema.anyOf.map(jsonSchemaToZod);
        return wrap(z.union(schemas as [ZodTypeAny, ZodTypeAny, ...ZodTypeAny[]]));
      }
      // Fallback to unknown
      return wrap(z.unknown());
  }
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/schema.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/schema.ts src/__tests__/schema.test.ts
git commit -m "feat: add JSON Schema to Zod converter"
```

---

### Task 4: Implement OliveClient Core

**Files:**
- Create: `src/client.ts`
- Create: `src/__tests__/client.test.ts`

**Step 1: Write the failing test**

```typescript
// src/__tests__/client.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OliveClient } from "../client";

describe("OliveClient", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe("fetchToolDefinitions", () => {
    it("fetches tools from /olive/tools endpoint", async () => {
      const mockTools = [
        {
          name: "get_weather",
          description: "Get weather for a city",
          input_schema: {
            type: "object",
            properties: { city: { type: "string" } },
            required: ["city"],
          },
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockTools,
      });

      const client = new OliveClient({
        baseUrl: "http://localhost:8000",
        fetch: mockFetch,
      });

      const tools = await client.fetchToolDefinitions();

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/olive/tools",
        expect.objectContaining({ method: "GET" })
      );
      expect(tools).toEqual(mockTools);
    });

    it("throws on non-ok response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });

      const client = new OliveClient({
        baseUrl: "http://localhost:8000",
        fetch: mockFetch,
      });

      await expect(client.fetchToolDefinitions()).rejects.toThrow(
        "Failed to fetch tools: 500 Internal Server Error"
      );
    });
  });

  describe("callTool", () => {
    it("calls /olive/tools/call with correct payload", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, result: { temp: 72 } }),
      });

      const client = new OliveClient({
        baseUrl: "http://localhost:8000",
        fetch: mockFetch,
      });

      const result = await client.callTool("get_weather", { city: "Paris" });

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/olive/tools/call",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tool_name: "get_weather",
            arguments: { city: "Paris" },
          }),
        })
      );
      expect(result).toEqual({ temp: 72 });
    });

    it("includes context when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, result: "ok" }),
      });

      const client = new OliveClient({
        baseUrl: "http://localhost:8000",
        fetch: mockFetch,
        context: { user_id: "123" },
      });

      await client.callTool("my_tool", {});

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({
            tool_name: "my_tool",
            arguments: {},
            context: { user_id: "123" },
          }),
        })
      );
    });

    it("throws on tool call failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: false, error: "Tool not found" }),
      });

      const client = new OliveClient({
        baseUrl: "http://localhost:8000",
        fetch: mockFetch,
      });

      await expect(client.callTool("unknown", {})).rejects.toThrow(
        "Tool call failed: Tool not found"
      );
    });
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/client.test.ts`
Expected: FAIL with "Cannot find module '../client'"

**Step 3: Write the implementation**

```typescript
// src/client.ts
import type {
  OliveClientConfig,
  OliveToolDefinition,
  OliveToolCallRequest,
  OliveToolCallResponse,
} from "./types";

export class OliveClient {
  private baseUrl: string;
  private timeout: number;
  private context?: Record<string, unknown>;
  private fetchFn: typeof fetch;

  constructor(config: OliveClientConfig | string) {
    if (typeof config === "string") {
      config = { baseUrl: config };
    }

    this.baseUrl = config.baseUrl.replace(/\/$/, ""); // Remove trailing slash
    this.timeout = config.timeout ?? 30000;
    this.context = config.context;
    this.fetchFn = config.fetch ?? fetch;
  }

  /**
   * Fetch all tool definitions from the Olive server.
   */
  async fetchToolDefinitions(): Promise<OliveToolDefinition[]> {
    const response = await this.fetchFn(`${this.baseUrl}/olive/tools`, {
      method: "GET",
      signal: AbortSignal.timeout(this.timeout),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to fetch tools: ${response.status} ${response.statusText}`
      );
    }

    return response.json();
  }

  /**
   * Call a tool on the Olive server.
   */
  async callTool(
    toolName: string,
    args: Record<string, unknown>,
    context?: Record<string, unknown>
  ): Promise<unknown> {
    const payload: OliveToolCallRequest = {
      tool_name: toolName,
      arguments: args,
    };

    // Merge default context with call-specific context
    const effectiveContext = { ...this.context, ...context };
    if (Object.keys(effectiveContext).length > 0) {
      payload.context = effectiveContext;
    }

    const response = await this.fetchFn(`${this.baseUrl}/olive/tools/call`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(this.timeout),
    });

    if (!response.ok) {
      throw new Error(
        `Failed to call tool: ${response.status} ${response.statusText}`
      );
    }

    const data: OliveToolCallResponse = await response.json();

    if (!data.success) {
      throw new Error(`Tool call failed: ${data.error ?? "Unknown error"}`);
    }

    return data.result;
  }

  /**
   * Set default context for all tool calls.
   */
  setContext(context: Record<string, unknown>): void {
    this.context = context;
  }
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/client.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/client.ts src/__tests__/client.test.ts
git commit -m "feat: add OliveClient core implementation"
```

---

### Task 5: Implement Vercel AI Tool Conversion

**Files:**
- Modify: `src/client.ts`
- Create: `src/__tests__/tools.test.ts`

**Step 1: Write the failing test**

```typescript
// src/__tests__/tools.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OliveClient } from "../client";
import { z } from "zod";

describe("OliveClient.getTools", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    mockFetch.mockReset();
  });

  it("returns Vercel AI SDK compatible tools", async () => {
    const mockToolDefs = [
      {
        name: "get_weather",
        description: "Get weather for a city",
        input_schema: {
          type: "object",
          properties: {
            city: { type: "string", description: "City name" },
          },
          required: ["city"],
        },
      },
    ];

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockToolDefs,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, result: { temp: 72 } }),
      });

    const client = new OliveClient({
      baseUrl: "http://localhost:8000",
      fetch: mockFetch,
    });

    const tools = await client.getTools();

    // Should have one tool
    expect(Object.keys(tools)).toEqual(["get_weather"]);

    // Tool should have correct structure
    const weatherTool = tools.get_weather;
    expect(weatherTool.description).toBe("Get weather for a city");
    expect(weatherTool.parameters).toBeDefined();
    expect(weatherTool.execute).toBeDefined();

    // Execute should call the server
    const result = await weatherTool.execute({ city: "Paris" });
    expect(result).toEqual({ temp: 72 });

    expect(mockFetch).toHaveBeenLastCalledWith(
      "http://localhost:8000/olive/tools/call",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          tool_name: "get_weather",
          arguments: { city: "Paris" },
        }),
      })
    );
  });

  it("filters tools by name when specified", async () => {
    const mockToolDefs = [
      { name: "tool_a", description: "A", input_schema: { type: "object", properties: {} } },
      { name: "tool_b", description: "B", input_schema: { type: "object", properties: {} } },
      { name: "tool_c", description: "C", input_schema: { type: "object", properties: {} } },
    ];

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockToolDefs,
    });

    const client = new OliveClient({
      baseUrl: "http://localhost:8000",
      fetch: mockFetch,
    });

    const tools = await client.getTools(["tool_a", "tool_c"]);

    expect(Object.keys(tools).sort()).toEqual(["tool_a", "tool_c"]);
  });
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- src/__tests__/tools.test.ts`
Expected: FAIL with "client.getTools is not a function"

**Step 3: Add getTools method to client**

Add to `src/client.ts`:

```typescript
// Add import at top
import { tool, type CoreTool } from "ai";
import { jsonSchemaToZod } from "./schema";

// Add method to OliveClient class
  /**
   * Get all Olive tools as Vercel AI SDK tools.
   *
   * @param toolNames - Optional list of tool names to include. If not provided, returns all tools.
   * @returns Object mapping tool names to Vercel AI SDK tool definitions
   */
  async getTools(toolNames?: string[]): Promise<Record<string, CoreTool>> {
    const definitions = await this.fetchToolDefinitions();

    // Filter by names if specified
    const filtered = toolNames
      ? definitions.filter((d) => toolNames.includes(d.name))
      : definitions;

    const tools: Record<string, CoreTool> = {};

    for (const def of filtered) {
      const inputSchema = jsonSchemaToZod(def.input_schema);

      tools[def.name] = tool({
        description: def.description,
        parameters: inputSchema,
        execute: async (args) => {
          return this.callTool(def.name, args as Record<string, unknown>);
        },
      });
    }

    return tools;
  }
```

**Step 4: Run test to verify it passes**

Run: `npm test -- src/__tests__/tools.test.ts`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add src/client.ts src/__tests__/tools.test.ts
git commit -m "feat: add getTools() for Vercel AI SDK integration"
```

---

### Task 6: Create Package Exports

**Files:**
- Create: `src/index.ts`

**Step 1: Write the exports file**

```typescript
// src/index.ts
export { OliveClient } from "./client";
export { jsonSchemaToZod } from "./schema";
export type {
  OliveClientConfig,
  OliveToolDefinition,
  OliveToolCallRequest,
  OliveToolCallResponse,
  OliveInjection,
  JsonSchema,
} from "./types";
```

**Step 2: Build the package**

Run: `npm run build`
Expected: Creates `dist/` with `.js`, `.cjs`, `.d.ts` files

**Step 3: Verify TypeScript types**

Run: `npm run lint`
Expected: No errors

**Step 4: Commit**

```bash
git add src/index.ts
git commit -m "feat: add package exports"
```

---

### Task 7: Add Integration Test

**Files:**
- Create: `src/__tests__/integration.test.ts`

**Step 1: Write integration test (skipped by default)**

```typescript
// src/__tests__/integration.test.ts
import { describe, it, expect } from "vitest";
import { OliveClient } from "../client";
import { generateText } from "ai";
// import { openai } from "@ai-sdk/openai"; // Uncomment when testing

describe.skip("Integration tests (requires running Olive server)", () => {
  const OLIVE_URL = process.env.OLIVE_URL ?? "http://localhost:8000";

  it("fetches tools from a real Olive server", async () => {
    const client = new OliveClient(OLIVE_URL);
    const definitions = await client.fetchToolDefinitions();

    expect(Array.isArray(definitions)).toBe(true);
    console.log("Available tools:", definitions.map((d) => d.name));
  });

  it("converts tools and uses with Vercel AI", async () => {
    const client = new OliveClient(OLIVE_URL);
    const tools = await client.getTools();

    console.log("Converted tools:", Object.keys(tools));

    // Uncomment to test with actual AI model:
    // const result = await generateText({
    //   model: openai("gpt-4"),
    //   tools,
    //   prompt: "What tools are available?",
    // });
    // console.log(result);
  });
});
```

**Step 2: Commit**

```bash
git add src/__tests__/integration.test.ts
git commit -m "test: add integration test scaffold"
```

---

### Task 8: Final Polish

**Files:**
- Update: `README.md`

**Step 1: Update README with full documentation**

```markdown
# olive-ai

TypeScript client for [Olive](https://github.com/YaVendio/olive) tools with Vercel AI SDK integration.

## Installation

\`\`\`bash
npm install olive-ai ai zod
\`\`\`

## Quick Start

\`\`\`typescript
import { OliveClient } from "olive-ai";
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";

// Create client connected to your Olive server
const olive = new OliveClient("http://localhost:8000");

// Get tools as Vercel AI SDK tools
const tools = await olive.getTools();

// Use with Vercel AI SDK
const result = await generateText({
  model: openai("gpt-4"),
  tools,
  prompt: "What's the weather in Paris?",
});

console.log(result.text);
\`\`\`

## API

### `new OliveClient(config)`

Create a new client instance.

\`\`\`typescript
// Simple usage
const client = new OliveClient("http://localhost:8000");

// With options
const client = new OliveClient({
  baseUrl: "http://localhost:8000",
  timeout: 30000,
  context: { user_id: "123" }, // Default context for all calls
});
\`\`\`

### `client.getTools(toolNames?)`

Get Olive tools as Vercel AI SDK tools.

\`\`\`typescript
// Get all tools
const allTools = await client.getTools();

// Get specific tools
const someTools = await client.getTools(["get_weather", "search"]);
\`\`\`

### `client.fetchToolDefinitions()`

Fetch raw tool definitions from the server.

\`\`\`typescript
const definitions = await client.fetchToolDefinitions();
// Returns: OliveToolDefinition[]
\`\`\`

### `client.callTool(name, args, context?)`

Call a tool directly.

\`\`\`typescript
const result = await client.callTool("get_weather", { city: "Paris" });
\`\`\`

### `client.setContext(context)`

Set default context for all tool calls (useful for injection).

\`\`\`typescript
client.setContext({ user_id: "123", session_id: "abc" });
\`\`\`

## Context Injection

Olive tools can declare injected parameters that are filled from context rather than LLM input:

\`\`\`python
# Server-side (Python)
@olive_tool
def get_user_data(
    query: str,
    user_id: Annotated[str, Inject("user_id")]  # Injected, not visible to LLM
):
    ...
\`\`\`

\`\`\`typescript
// Client-side (TypeScript)
const client = new OliveClient({
  baseUrl: "http://localhost:8000",
  context: { user_id: "current-user-123" },
});

// The user_id is automatically injected on every call
const tools = await client.getTools();
\`\`\`

## License

MIT
\`\`\`

**Step 2: Run all tests**

Run: `npm run test:run`
Expected: All tests PASS

**Step 3: Build final package**

Run: `npm run build`
Expected: Success

**Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: complete README documentation"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Initialize repository | package.json, tsconfig.json, tsup.config.ts, .gitignore, README.md |
| 2 | Define types | src/types.ts |
| 3 | Schema converter | `src/schema.ts`, `src/__tests__/schema.test.ts` |
| 4 | OliveClient core | `src/client.ts`, `src/__tests__/client.test.ts` |
| 5 | Vercel AI tools | `src/client.ts` (modify), `src/__tests__/tools.test.ts` |
| 6 | Package exports | `src/index.ts` |
| 7 | Integration test | `src/__tests__/integration.test.ts` |
| 8 | Documentation | README.md |

**Total estimated commits:** 8
