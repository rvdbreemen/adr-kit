import { existsSync, readFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

type AnyRecord = Record<string, any>

type PluginOptions = {
  root?: string
  python?: string
  mcp?: boolean
  skills?: boolean
  commands?: boolean
  instructions?: boolean
  references?: boolean
  hooks?: boolean
  hookTimeoutMs?: number
}

type HookResult = {
  context: string
  denied: boolean
  reason: string
}

type SessionState = {
  context: string
  contextKind: string
}

declare const Bun: {
  spawn(
    command: string[],
    options: {
      cwd: string
      stdin: "pipe"
      stdout: "pipe"
      stderr: "ignore"
    },
  ): {
    stdin: { write(value: string): void; end(): void }
    stdout: ReadableStream<Uint8Array>
    exited: Promise<number>
    kill(): void
  }
}

const PACKAGE_DIR = dirname(fileURLToPath(import.meta.url))
const PACKAGE_ROOT = dirname(PACKAGE_DIR)
const MAX_CONTEXT_CHARS = 4096
const MAX_INPUT_CHARS = 8192
const MAX_OUTPUT_CHARS = 16384
const DEFAULT_HOOK_TIMEOUT_MS = 2000
const PR_HOOK_TIMEOUT_MS = 5000
const ADR_CONTEXT_MARKER = "<adr-kit-context>"
const ADR_SYSTEM_MARKER = "<adr-kit-instructions>"
const WRITE_TOOLS = new Set(["edit", "multiedit", "write", "patch", "apply_patch"])
const SHELL_TOOLS = new Set(["bash", "shell", "terminal", "run"])

const STATIC_INSTRUCTIONS = `${ADR_SYSTEM_MARKER}
ADR Kit is active for this OpenCode project. Use the adr-kit MCP server to find
the governing Accepted ADRs before implementation and to judge diffs when asked.
Hook context is advisory and fail-open. The deterministic pre-commit and CI
judge remain the only normal enforcement floor. Never treat a retrieval result
as binding until you read the linked Markdown ADR.
</adr-kit-instructions>`

function isRuntimeRoot(path: string): boolean {
  return (
    existsSync(join(path, "bin", "adr-mcp")) &&
    existsSync(join(path, "hooks", "adr-hook.py")) &&
    existsSync(join(path, "skills"))
  )
}

function ancestors(start: string): string[] {
  const result: string[] = []
  let current = resolve(start)
  while (!result.includes(current)) {
    result.push(current)
    const parent = dirname(current)
    if (parent === current) break
    current = parent
  }
  return result
}

function findRuntimeRoot(
  explicit: string | undefined,
  directory: string,
  worktree: string,
): string | undefined {
  const candidates = [explicit, process.env.ADR_KIT_ROOT, PACKAGE_ROOT, directory, worktree]
    .filter((value): value is string => Boolean(value))
    .map((value) => (explicit === value && !value.startsWith("/") && !/^[A-Za-z]:[\\/]/.test(value)
      ? resolve(directory, value)
      : resolve(value)))

  for (const candidate of candidates) {
    for (const path of ancestors(candidate)) {
      if (isRuntimeRoot(path)) return path
    }
  }
  return undefined
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)))
}

function bounded(value: unknown, limit: number): string {
  return typeof value === "string" ? value.slice(0, limit) : ""
}

function sessionKey(sessionID: string | undefined): string {
  return sessionID || "__workspace__"
}

function stateFor(sessions: Map<string, SessionState>, sessionID: string | undefined): SessionState {
  const key = sessionKey(sessionID)
  let state = sessions.get(key)
  if (!state) {
    state = { context: "", contextKind: "" }
    sessions.set(key, state)
  }
  return state
}

function promptText(parts: unknown): string {
  if (!Array.isArray(parts)) return ""
  return parts
    .filter((part): part is AnyRecord => Boolean(part) && typeof part === "object")
    .filter((part) => part.type === "text")
    .map((part) => bounded(part.text, MAX_INPUT_CHARS))
    .filter(Boolean)
    .join("\n")
    .slice(0, MAX_INPUT_CHARS)
}

function readJson(path: string): AnyRecord | undefined {
  try {
    const value = JSON.parse(readFileSync(path, "utf8"))
    return value && typeof value === "object" ? value : undefined
  } catch {
    return undefined
  }
}

function extractHookResult(raw: string): HookResult {
  for (const line of raw.split(/\r?\n/).filter(Boolean)) {
    try {
      const value = JSON.parse(line) as AnyRecord
      const specific = value.hookSpecificOutput && typeof value.hookSpecificOutput === "object"
        ? value.hookSpecificOutput
        : {}
      const context = bounded(
        specific.additionalContext || value.additionalContext,
        MAX_CONTEXT_CHARS,
      )
      const denied = specific.permissionDecision === "deny" || value.permissionDecision === "deny"
      const reason = bounded(
        specific.permissionDecisionReason || value.permissionDecisionReason || context,
        MAX_CONTEXT_CHARS,
      )
      return { context, denied, reason }
    } catch {
      // The shared hook is fail-open. Ignore malformed output and continue.
    }
  }
  return { context: "", denied: false, reason: "" }
}

async function runHook(
  runtimeRoot: string | undefined,
  python: string,
  cwd: string,
  event: string,
  sessionID: string | undefined,
  payload: AnyRecord,
  timeoutMs: number,
): Promise<HookResult> {
  if (!runtimeRoot) return { context: "", denied: false, reason: "" }
  const hook = join(runtimeRoot, "hooks", "adr-hook.py")
  if (!existsSync(hook)) return { context: "", denied: false, reason: "" }

  let child: ReturnType<typeof Bun.spawn>
  try {
    child = Bun.spawn(
      [python, hook, "--client", "claude-code-cli", "--event", event],
      { cwd, stdin: "pipe", stdout: "pipe", stderr: "ignore" },
    )
    child.stdin.write(JSON.stringify({
      cwd,
      hook_event_name: event,
      session_id: sessionID,
      ...payload,
    }))
    child.stdin.end()
  } catch {
    return { context: "", denied: false, reason: "" }
  }

  let timer: ReturnType<typeof setTimeout> | undefined
  const output = new Response(child.stdout).text().catch(() => "")
  const completed = Promise.all([
    output,
    child.exited.catch(() => -1),
  ]).then(([value, exitCode]) => ({ timedOut: false, value, exitCode }))
  const result = await Promise.race([
    completed,
    new Promise<{ timedOut: true; value: string }>((resolveResult) => {
      timer = setTimeout(() => resolveResult({ timedOut: true, value: "" }), timeoutMs)
    }),
  ])
  if (timer) clearTimeout(timer)
  if (result.timedOut) {
    try { child.kill() } catch { /* fail open */ }
    return { context: "", denied: false, reason: "" }
  }

  if (result.exitCode !== 0) return { context: "", denied: false, reason: "" }
  return extractHookResult(result.value.slice(0, MAX_OUTPUT_CHARS))
}

function toolName(value: unknown): string {
  return bounded(value, 80).toLowerCase().replace(/[^a-z0-9_]/g, "")
}

function toolPath(args: AnyRecord): string {
  for (const key of ["filePath", "file_path", "path", "notebook_path"]) {
    if (typeof args[key] === "string") return args[key]
  }
  return ""
}

function hookTimeout(options: PluginOptions, fallback: number): number {
  const configured = options.hookTimeoutMs
  if (!Number.isInteger(configured)) return fallback
  return Math.max(100, Math.min(PR_HOOK_TIMEOUT_MS, configured))
}

function addContext(sessions: Map<string, SessionState>, sessionID: string | undefined, result: HookResult, kind: string): void {
  if (!result.context) return
  const state = stateFor(sessions, sessionID)
  state.context = result.context
  state.contextKind = kind
}

function commandTemplate(root: string, workflow: AnyRecord): string {
  const procedure = Array.isArray(workflow.procedure)
    ? workflow.procedure.map((item) => `- ${String(item).replaceAll("<plugin-root>", root)}`).join("\n")
    : "- Follow the ADR Kit documentation and use the adr-kit MCP tools."
  return [
    `Run the ADR Kit '${workflow.id}' workflow in OpenCode.`,
    "",
    "User task or arguments:",
    "$ARGUMENTS",
    "",
    "Use the active project's adr-kit MCP server and read linked Markdown ADRs before treating a decision as binding.",
    "",
    "Procedure:",
    procedure,
  ].join("\n")
}

export default async function AdrKitOpenCodePlugin(
  input: { directory: string; worktree: string },
  rawOptions: AnyRecord = {},
) {
  const options = rawOptions as PluginOptions
  const runtimeRoot = findRuntimeRoot(options.root, input.directory, input.worktree)
  const python = options.python || process.env.ADR_KIT_PYTHON || "python"
  const sessions = new Map<string, SessionState>()

  return {
    config: async (rawConfig: AnyRecord) => {
      if (!runtimeRoot) return
      const config = rawConfig as AnyRecord

      if (options.skills !== false) {
        config.skills ||= {}
        config.skills.paths = unique([...(Array.isArray(config.skills.paths) ? config.skills.paths : []), join(runtimeRoot, "skills")])
      }

      if (options.instructions !== false) {
        const instructions = Array.isArray(config.instructions) ? config.instructions : []
        const candidates = [
          join(runtimeRoot, "instructions", "ADR-guide.md"),
          join(input.directory, ".adr-kit", "ADR-guide.md"),
        ].filter((path) => existsSync(path))
        config.instructions = unique([...instructions, ...candidates])
      }

      if (options.references !== false && existsSync(join(input.directory, "docs", "adr"))) {
        config.references ||= {}
        if (!config.references["adr-decisions"]) {
          config.references["adr-decisions"] = join(input.directory, "docs", "adr")
        }
      }

      if (options.mcp !== false && process.env.ADR_KIT_OPENCODE_MCP !== "0") {
        config.mcp ||= {}
        if (!config.mcp["adr-kit"]) {
          config.mcp["adr-kit"] = {
            type: "local",
            command: [python, join(runtimeRoot, "bin", "adr-mcp"), "--root", input.directory],
            cwd: input.directory,
            enabled: true,
            timeout: 60000,
            environment: { PROJECT_ROOT: input.directory },
          }
        }
      }

      if (options.commands !== false) {
        const workflows = readJson(join(runtimeRoot, "clients", "workflows.json"))
        if (Array.isArray(workflows?.workflows)) {
          config.command ||= {}
          for (const workflow of workflows.workflows) {
            if (!workflow || typeof workflow.id !== "string") continue
            const name = `adr-kit-${workflow.id}`
            if (config.command[name]) continue
            config.command[name] = {
              description: `ADR Kit: ${workflow.description || workflow.title || workflow.id}`,
              template: commandTemplate(runtimeRoot, workflow),
            }
          }
        }
      }
    },

    "shell.env": async (_hookInput: { cwd: string }, output: { env: Record<string, string> }) => {
      if (runtimeRoot && !output.env.ADR_KIT_ROOT) output.env.ADR_KIT_ROOT = runtimeRoot
    },

    "chat.message": async (
      hookInput: { sessionID: string },
      output: { parts: unknown[] },
    ) => {
      if (options.hooks === false) return
      const prompt = promptText(output.parts)
      if (!prompt) return
      const result = await runHook(
        runtimeRoot,
        python,
        input.directory,
        "UserPromptSubmit",
        hookInput.sessionID,
        { prompt },
        hookTimeout(options, DEFAULT_HOOK_TIMEOUT_MS),
      )
      addContext(sessions, hookInput.sessionID, result, "prompt")
    },

    "experimental.chat.system.transform": async (
      hookInput: { sessionID?: string },
      output: { system: string[] },
    ) => {
      if (!output.system.some((item) => item.includes(ADR_SYSTEM_MARKER))) {
        output.system.push(STATIC_INSTRUCTIONS)
      }
      const state = sessions.get(sessionKey(hookInput.sessionID))
      if (state?.context && !output.system.some((item) => item.includes(ADR_CONTEXT_MARKER))) {
        output.system.push(`${ADR_CONTEXT_MARKER}\n${state.context}\n</adr-kit-context>`)
      }
    },

    "experimental.session.compacting": async (
      hookInput: { sessionID: string },
      output: { context: string[] },
    ) => {
      const state = sessions.get(sessionKey(hookInput.sessionID))
      if (state?.context) output.context.push(`${ADR_CONTEXT_MARKER}\n${state.context}\n</adr-kit-context>`)
      output.context.push("Keep ADR Kit's governing decisions, open questions, and the rule that the pre-commit/CI judge is the enforcement floor.")
    },

    "tool.definition": async (
      hookInput: { toolID: string },
      output: { description: string },
    ) => {
      if (WRITE_TOOLS.has(toolName(hookInput.toolID)) && !output.description.includes("adr-kit MCP")) {
        output.description += " Before editing, use the adr-kit MCP server to check governing ADRs."
      }
    },

    "tool.execute.before": async (
      hookInput: { tool: string; sessionID: string },
      output: { args: AnyRecord },
    ) => {
      if (options.hooks === false) return
      const normalized = toolName(hookInput.tool)
      const args = output.args || {}
      if (SHELL_TOOLS.has(normalized) && typeof args.command === "string") {
        const result = await runHook(
          runtimeRoot,
          python,
          input.directory,
          "PreToolUse",
          hookInput.sessionID,
          { tool_name: "Bash", tool_input: { command: bounded(args.command, MAX_INPUT_CHARS) } },
          hookTimeout(options, PR_HOOK_TIMEOUT_MS),
        )
        addContext(sessions, hookInput.sessionID, result, "shell")
        if (result.denied) throw new Error(result.reason || "ADR Kit blocked this pull-request command.")
        return
      }
      if (!WRITE_TOOLS.has(normalized) || !toolPath(args)) return
      const result = await runHook(
        runtimeRoot,
        python,
        input.directory,
        "PreToolUse",
        hookInput.sessionID,
        { tool_name: normalized === "write" ? "Write" : "Edit", tool_input: args },
        hookTimeout(options, DEFAULT_HOOK_TIMEOUT_MS),
      )
      addContext(sessions, hookInput.sessionID, result, "edit")
    },

    "tool.execute.after": async (
      hookInput: { tool: string; sessionID: string; args: AnyRecord },
    ) => {
      if (options.hooks === false) return
      const normalized = toolName(hookInput.tool)
      if (!WRITE_TOOLS.has(normalized) || !toolPath(hookInput.args || {})) return
      const result = await runHook(
        runtimeRoot,
        python,
        input.directory,
        "PostToolUse",
        hookInput.sessionID,
        { tool_name: normalized === "write" ? "Write" : "Edit", tool_input: hookInput.args || {} },
        hookTimeout(options, DEFAULT_HOOK_TIMEOUT_MS),
      )
      addContext(sessions, hookInput.sessionID, result, "post-edit")
    },

    event: async ({ event }: { event: AnyRecord }) => {
      const properties = event.properties && typeof event.properties === "object" ? event.properties : {}
      const id = properties.sessionID || properties.session_id || properties.info?.id
      if (event.type === "session.created" && typeof id === "string") stateFor(sessions, id)
      if (event.type === "session.deleted" && typeof id === "string") sessions.delete(id)
    },

    dispose: async () => {
      sessions.clear()
    },
  }
}
