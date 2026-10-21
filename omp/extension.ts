// Native OMP (oh-my-pi) extension for ADR Kit (ADR-050).
//
// OMP installs this repository as a Claude-format marketplace plugin and reads
// its skills, agent and `.mcp.json` itself. What it does not do is run the
// command hooks in `hooks/hooks.json` or provide `${CLAUDE_PLUGIN_ROOT}`. This
// module, declared in `package.json` under `omp.extensions`, fills those two
// gaps and nothing else: every ADR decision is made by `hooks/adr-hook.py`.
import { existsSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

type AnyRecord = Record<string, any>

type HookResult = {
  context: string
  denied: boolean
  reason: string
}

type AgentIdentity = { kind?: string }

type HandlerContext = {
  cwd: string
  agent?: AgentIdentity
  sessionManager?: { getSessionId?(): string }
}

type Handler = (event: AnyRecord, ctx: HandlerContext) => Promise<AnyRecord | void>

type ExtensionAPI = {
  on(event: string, handler: Handler): void
  setLabel?(label: string): void
}

type HookProcess = {
  stdin: { write(value: string): void; end(): void }
  stdout: ReadableStream<Uint8Array>
  exited: Promise<number>
  kill(): void
}

type HookOutcome = { timedOut: boolean; value: string; exitCode: number }

declare const Bun: {
  spawn(
    command: string[],
    options: {
      cwd: string
      stdin: "pipe"
      stdout: "pipe"
      stderr: "ignore"
      env: Record<string, string | undefined>
    },
  ): HookProcess
  spawnSync(
    command: string[],
    options: { stdout: "ignore"; stderr: "ignore"; timeout: number },
  ): { exitCode: number | null }
  which(name: string): string | null
}

const PACKAGE_ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const MAX_CONTEXT_CHARS = 4096
const MAX_INPUT_CHARS = 8192
const MAX_OUTPUT_CHARS = 16384
const MAX_EDIT_PATHS = 32
const DEFAULT_HOOK_TIMEOUT_MS = 2000
const PR_HOOK_TIMEOUT_MS = 5000
const CONTEXT_MESSAGE_TYPE = "adr-kit-context"
const SYSTEM_MARKER = "<adr-kit-instructions>"
// The OMP tools that write files. `ast_edit` rewrites code in place.
const WRITE_TOOLS: Record<string, string> = { edit: "Edit", write: "Write", ast_edit: "Edit" }
const SHELL_TOOL = "bash"
const NO_RESULT: HookResult = { context: "", denied: false, reason: "" }

const STATIC_INSTRUCTIONS = `${SYSTEM_MARKER}
ADR Kit is active in this OMP session. Use the adr-kit MCP tools to find the
governing Accepted ADRs before implementation and to judge diffs when asked;
read the linked Markdown ADR before treating a result as binding. ADR Kit
workflows are skills: invoke them as /skill:<name>, for example /skill:grill.
Hook context is advisory and fail-open; the pre-commit and CI judge are the
enforcement floor.
</adr-kit-instructions>`

// Child sessions (task subagents) rebind this factory but share module state,
// so the latest context of a workspace's main session is kept here for the
// subagent and compaction hooks, which only forward what they are given.
const lastContext = new Map<string, string>()

// ADR-044: an explicit ADR_KIT_ROOT wins; otherwise the plugin this module
// was installed with.
function findRuntimeRoot(): string | undefined {
  for (const candidate of [process.env.ADR_KIT_ROOT, PACKAGE_ROOT]) {
    if (!candidate) continue
    const root = resolve(candidate)
    if (
      existsSync(join(root, "bin", "adr-mcp")) &&
      existsSync(join(root, "hooks", "adr-hook.py")) &&
      existsSync(join(root, "skills"))
    ) return root
  }
  return undefined
}

// ADR-044's interpreter order, as in the OpenCode plugin: ADR_KIT_PYTHON, then
// the first of python3, python and, on Windows, py -3 that runs Python 3.10+.
function resolvePython(): string[] {
  if (process.env.ADR_KIT_PYTHON) return [process.env.ADR_KIT_PYTHON]
  const candidates = [["python3"], ["python"]]
  if (process.platform === "win32") candidates.push(["py", "-3"])
  for (const [name, ...args] of candidates) {
    const executable = Bun.which(name)
    if (!executable) continue
    try {
      const probe = Bun.spawnSync(
        [executable, ...args, "-c", "import sys; sys.exit(sys.version_info < (3, 10))"],
        { stdout: "ignore", stderr: "ignore", timeout: 5000 },
      )
      if (probe.exitCode === 0) return [executable, ...args]
    } catch {
      // Not runnable here; try the next candidate.
    }
  }
  return []
}

function bounded(value: unknown, limit: number): string {
  return typeof value === "string" ? value.slice(0, limit) : ""
}

function extractHookResult(raw: string): HookResult {
  for (const line of raw.split(/\r?\n/).filter(Boolean)) {
    try {
      const value = JSON.parse(line) as AnyRecord
      const specific = value.hookSpecificOutput && typeof value.hookSpecificOutput === "object"
        ? value.hookSpecificOutput
        : {}
      const context = bounded(specific.additionalContext, MAX_CONTEXT_CHARS)
      const denied = specific.permissionDecision === "deny"
      const reason = bounded(specific.permissionDecisionReason || context, MAX_CONTEXT_CHARS)
      return { context, denied, reason }
    } catch {
      // The shared hook is fail-open. Ignore malformed output and continue.
    }
  }
  return NO_RESULT
}

// The hook renders Claude Code's grill command; OMP exposes it as a skill.
function ompCommands(context: string): string {
  return context
    .replaceAll("/adr-kit:grill", "/skill:grill")
    .replaceAll("$adr-kit:grill", "/skill:grill")
    .replaceAll("adr-kit:grill", "/skill:grill")
}

// Only the paths an edit touches go to the hook: a written file's content can
// exceed the hook's 64 KiB input bound, which would drop the whole event. One
// path is sent as `file_path`; several as apply_patch headers, the shape the
// hook core already reads for multi-file edits.
function editInput(input: AnyRecord): AnyRecord | undefined {
  const paths: string[] = []
  for (const value of [input.path, input.file_path, ...(Array.isArray(input.paths) ? input.paths : [])]) {
    if (typeof value === "string" && value && !paths.includes(value)) paths.push(value)
  }
  if (!paths.length) return undefined
  if (paths.length === 1) return { file_path: paths[0] }
  return {
    patchText: paths
      .slice(0, MAX_EDIT_PATHS)
      .map((path) => `*** Update File: ${path}`)
      .join("\n"),
  }
}

function sessionId(ctx: HandlerContext): string | undefined {
  try {
    return ctx.sessionManager?.getSessionId?.() || undefined
  } catch {
    return undefined
  }
}

function isSubagent(ctx: HandlerContext): boolean {
  return ctx.agent?.kind === "sub"
}

function wrap(context: string): string {
  return `<adr-kit-context>\n${context}\n</adr-kit-context>`
}

export default function adrKitOmpExtension(pi: ExtensionAPI): void {
  const runtimeRoot = findRuntimeRoot()
  if (!runtimeRoot) return
  // Skills resolve the engine as ${ADR_KIT_ROOT:-${CLAUDE_PLUGIN_ROOT}}; OMP
  // provides neither, and its shell tools inherit this process's environment.
  if (!process.env.ADR_KIT_ROOT) process.env.ADR_KIT_ROOT = runtimeRoot
  const hook = join(runtimeRoot, "hooks", "adr-hook.py")
  let python: string[] | undefined
  pi.setLabel?.("ADR Kit")

  async function runHook(
    cwd: string,
    event: string,
    session: string | undefined,
    payload: AnyRecord,
    timeoutMs: number,
  ): Promise<HookResult> {
    python ??= resolvePython()
    if (!python.length) return NO_RESULT
    let child: HookProcess
    try {
      child = Bun.spawn([...python, hook, "--client", "claude-code-cli", "--event", event], {
        cwd,
        stdin: "pipe",
        stdout: "pipe",
        stderr: "ignore",
        // The hook renders Claude-shaped output for this adapter, but the LLM
        // layers must run on OMP's own model (ADR-049, ADR-050).
        env: { ...process.env, ADR_KIT_HOST_CLIENT: "omp-cli" },
      })
      child.stdin.write(JSON.stringify({ cwd, hook_event_name: event, session_id: session, ...payload }))
      child.stdin.end()
    } catch {
      return NO_RESULT
    }

    const deadline = Promise.withResolvers<HookOutcome>()
    const timer = setTimeout(() => deadline.resolve({ timedOut: true, value: "", exitCode: -1 }), timeoutMs)
    const completed = Promise.all([
      new Response(child.stdout).text().catch(() => ""),
      child.exited.catch(() => -1),
    ]).then(([value, exitCode]): HookOutcome => ({ timedOut: false, value, exitCode }))
    const result = await Promise.race([completed, deadline.promise])
    clearTimeout(timer)
    if (result.timedOut) {
      try { child.kill() } catch { /* fail open */ }
      return NO_RESULT
    }
    if (result.exitCode !== 0) return NO_RESULT
    const parsed = extractHookResult(result.value.slice(0, MAX_OUTPUT_CHARS))
    return { ...parsed, context: ompCommands(parsed.context) }
  }

  // A fault in a handler must never surface: OMP treats a throwing tool_call
  // handler as a block, and every other moment here is advisory.
  function on(event: string, handler: Handler): void {
    pi.on(event, async (payload, ctx) => {
      try {
        return await handler(payload, ctx)
      } catch {
        return undefined
      }
    })
  }

  // Session context waits here until the first prompt, the first moment OMP
  // lets an extension add a message to the conversation.
  let pending = ""
  let subagentStarted = false

  on("session_start", async (_event, ctx) => {
    if (isSubagent(ctx)) return
    const result = await runHook(ctx.cwd, "SessionStart", sessionId(ctx), {}, DEFAULT_HOOK_TIMEOUT_MS)
    pending = result.context
  })

  on("before_agent_start", async (event, ctx) => {
    const parts: string[] = []
    if (isSubagent(ctx)) {
      const parent = lastContext.get(ctx.cwd)
      if (!subagentStarted && parent) {
        subagentStarted = true
        const result = await runHook(
          ctx.cwd,
          "SubagentStart",
          sessionId(ctx),
          { parent_context: parent },
          DEFAULT_HOOK_TIMEOUT_MS,
        )
        if (result.context) parts.push(result.context)
      }
    } else {
      if (pending) parts.push(pending)
      pending = ""
      const prompt = bounded(event.prompt, MAX_INPUT_CHARS)
      if (prompt.trim()) {
        const result = await runHook(
          ctx.cwd,
          "UserPromptSubmit",
          sessionId(ctx),
          { prompt },
          DEFAULT_HOOK_TIMEOUT_MS,
        )
        if (result.context) parts.push(result.context)
      }
    }
    const systemPrompt = Array.isArray(event.systemPrompt) ? event.systemPrompt : []
    const output: AnyRecord = {}
    if (!systemPrompt.some((item: unknown) => typeof item === "string" && item.includes(SYSTEM_MARKER))) {
      output.systemPrompt = [...systemPrompt, STATIC_INSTRUCTIONS]
    }
    const context = parts.join("\n\n").slice(0, MAX_CONTEXT_CHARS)
    if (context) {
      if (!isSubagent(ctx)) lastContext.set(ctx.cwd, context)
      output.message = { customType: CONTEXT_MESSAGE_TYPE, content: wrap(context), display: false }
    }
    return output
  })

  on("tool_call", async (event, ctx) => {
    const tool = String(event.toolName || "").toLowerCase()
    const input = event.input && typeof event.input === "object" ? event.input : {}
    if (tool === SHELL_TOOL && typeof input.command === "string") {
      const result = await runHook(
        ctx.cwd,
        "PreToolUse",
        sessionId(ctx),
        { tool_name: "Bash", tool_input: { command: bounded(input.command, MAX_INPUT_CHARS) } },
        PR_HOOK_TIMEOUT_MS,
      )
      if (result.denied) return { block: true, reason: result.reason || "ADR Kit blocked this pull-request command." }
      return result.context ? { additionalContext: wrap(result.context) } : undefined
    }
    const toolName = WRITE_TOOLS[tool]
    const toolInput = toolName ? editInput(input) : undefined
    if (!toolName || !toolInput) return undefined
    const result = await runHook(
      ctx.cwd,
      "PreToolUse",
      sessionId(ctx),
      { tool_name: toolName, tool_input: toolInput },
      DEFAULT_HOOK_TIMEOUT_MS,
    )
    return result.context ? { additionalContext: wrap(result.context) } : undefined
  })

  on("tool_result", async (event, ctx) => {
    if (event.isError) return undefined
    const toolName = WRITE_TOOLS[String(event.toolName || "").toLowerCase()]
    const toolInput = toolName && event.input && typeof event.input === "object" ? editInput(event.input) : undefined
    if (!toolName || !toolInput) return undefined
    const result = await runHook(
      ctx.cwd,
      "PostToolUse",
      sessionId(ctx),
      { tool_name: toolName, tool_input: toolInput },
      DEFAULT_HOOK_TIMEOUT_MS,
    )
    return result.context ? { additionalContext: wrap(result.context) } : undefined
  })

  on("session.compacting", async (_event, ctx) => {
    const parent = lastContext.get(ctx.cwd)
    if (!parent) return undefined
    const result = await runHook(
      ctx.cwd,
      "PreCompact",
      sessionId(ctx),
      { parent_context: parent },
      DEFAULT_HOOK_TIMEOUT_MS,
    )
    return result.context ? { context: [wrap(result.context)] } : undefined
  })
}
