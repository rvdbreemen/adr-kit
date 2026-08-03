#![cfg_attr(target_os = "windows", windows_subsystem = "windows")]
//! Dependency-free native hot-path host for ADR Kit lifecycle hooks.
//!
//! This deliberately implements only bounded, read-only retrieval from the
//! generated ADR index. Any malformed input or missing file exits successfully
//! without output; deterministic pre-commit enforcement remains separate.

use std::cmp::Reverse;
use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::{self, Read};
use std::path::{Component, Path, PathBuf};
use std::time::{Duration, SystemTime};

const MAX_INPUT: u64 = 64 * 1024;
const MAX_CONTEXT: usize = 4 * 1024;
const MAX_PARENT: usize = 8 * 1024;
// spec R5: five, matching adr_hook_core.DEFAULT_MAX_RESULTS. A test asserts
// the two stay equal, because a platform-dependent difference in what an
// agent is told is worse than a missing feature: nobody sees it happen.
const MAX_RESULTS: usize = 5;
const QUEUE_MAX_BYTES: u64 = 256 * 1024;

#[derive(Clone)]
struct Record {
    id: String,
    title: String,
    path: String,
    status: String,
    summary: String,
    context_scope: String,
    globs: Vec<String>,
    verified: Vec<String>,
    topics: Vec<String>,
    aliases: Vec<String>,
    components: Vec<String>,
    symbols: Vec<String>,
    contract: Vec<String>,
}

fn json_string(input: &str, key: &str) -> Option<String> {
    let marker = format!("\"{}\"", key);
    let mut cursor = input.find(&marker)? + marker.len();
    cursor += input[cursor..].find(':')? + 1;
    let bytes = input.as_bytes();
    while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() {
        cursor += 1;
    }
    if cursor >= bytes.len() || bytes[cursor] != b'"' {
        return None;
    }
    cursor += 1;
    let mut result = String::new();
    let mut escaped = false;
    while cursor < bytes.len() {
        let value = bytes[cursor];
        cursor += 1;
        if escaped {
            match value {
                b'"' => result.push('"'),
                b'\\' => result.push('\\'),
                b'/' => result.push('/'),
                b'b' => result.push('\u{0008}'),
                b'f' => result.push('\u{000c}'),
                b'n' => result.push('\n'),
                b'r' => result.push('\r'),
                b't' => result.push('\t'),
                b'u' => {
                    if cursor + 4 <= bytes.len() {
                        if let Ok(hex) = u16::from_str_radix(&input[cursor..cursor + 4], 16) {
                            if let Some(ch) = char::from_u32(hex as u32) {
                                result.push(ch);
                            }
                        }
                        cursor += 4;
                    }
                }
                _ => return None,
            }
            escaped = false;
        } else if value == b'\\' {
            escaped = true;
        } else if value == b'"' {
            return Some(result);
        } else {
            result.push(value as char);
        }
    }
    None
}

fn json_true(input: &str, key: &str) -> bool {
    let marker = format!("\"{}\"", key);
    input.find(&marker).and_then(|start| {
        let tail = &input[start + marker.len()..];
        tail.find(':').map(|colon| tail[colon + 1..].trim_start().starts_with("true"))
    }).unwrap_or(false)
}

fn array_section<'a>(input: &'a str, key: &str) -> Option<&'a str> {
    let marker = format!("\"{}\"", key);
    let start = input.find(&marker)? + marker.len();
    let tail = &input[start..];
    let open = start + tail.find('[')?;
    let mut depth = 0usize;
    let mut quoted = false;
    let mut escaped = false;
    for (offset, ch) in input[open..].char_indices() {
        if escaped {
            escaped = false;
            continue;
        }
        if ch == '\\' && quoted {
            escaped = true;
        } else if ch == '"' {
            quoted = !quoted;
        } else if !quoted && ch == '[' {
            depth += 1;
        } else if !quoted && ch == ']' {
            depth -= 1;
            if depth == 0 {
                return Some(&input[open + 1..open + offset]);
            }
        }
    }
    None
}

fn top_level_objects(input: &str) -> Vec<&str> {
    let mut objects = Vec::new();
    let mut start = None;
    let mut depth = 0usize;
    let mut quoted = false;
    let mut escaped = false;
    for (offset, ch) in input.char_indices() {
        if escaped {
            escaped = false;
            continue;
        }
        if ch == '\\' && quoted {
            escaped = true;
        } else if ch == '"' {
            quoted = !quoted;
        } else if !quoted && ch == '{' {
            if depth == 0 {
                start = Some(offset);
            }
            depth += 1;
        } else if !quoted && ch == '}' && depth > 0 {
            depth -= 1;
            if depth == 0 {
                if let Some(begin) = start.take() {
                    objects.push(&input[begin..offset + 1]);
                }
            }
        }
    }
    objects
}

fn string_array(input: &str, key: &str) -> Vec<String> {
    array_section(input, key).map(|section| {
        let mut values = Vec::new();
        let mut rest = section;
        loop {
            let Some(open) = rest.find('"') else { break };
            rest = &rest[open + 1..];
            let Some(close) = rest.find('"') else { break };
            values.push(rest[..close].to_string());
            rest = &rest[close + 1..];
        }
        values
    }).unwrap_or_default()
}

fn load_records(workspace: &Path) -> Vec<Record> {
    let candidates = [
        workspace.join("docs/adr/ADR-INDEX.json"),
        workspace.join("adr/ADR-INDEX.json"),
    ];
    let Some(path) = candidates.iter().find(|path| path.is_file()) else {
        return Vec::new();
    };
    let Ok(metadata) = fs::metadata(path) else { return Vec::new() };
    if metadata.len() > 2 * 1024 * 1024 {
        return Vec::new();
    }
    let Ok(text) = fs::read_to_string(path) else { return Vec::new() };
    let Some(adrs) = array_section(&text, "adrs") else { return Vec::new() };
    top_level_objects(adrs).into_iter().filter_map(|object| {
        Some(Record {
            id: json_string(object, "id")?,
            title: json_string(object, "title").unwrap_or_default(),
            path: json_string(object, "path").unwrap_or_default(),
            status: json_string(object, "status").unwrap_or_default(),
            summary: json_string(object, "decision_summary").unwrap_or_default(),
            context_scope: json_string(object, "context_scope").unwrap_or_else(|| "selective".to_string()),
            globs: string_array(object, "path_globs"),
            verified: string_array(object, "verified_in"),
            topics: string_array(object, "topics"),
            aliases: string_array(object, "aliases"),
            components: string_array(object, "components"),
            symbols: string_array(object, "symbols"),
            contract: ["must", "must_not", "exceptions", "verification"].iter()
                .flat_map(|key| string_array(object, key))
                .collect(),
        })
    }).collect()
}

fn load_queue_context(workspace: &Path) -> String {
    let path = workspace.join("docs/adr/.adr-kit-readiness.json");
    let Ok(metadata) = fs::metadata(&path) else { return String::new() };
    if metadata.len() > QUEUE_MAX_BYTES {
        return String::new();
    }
    let fresh = metadata.modified().ok().and_then(|modified| {
        SystemTime::now().duration_since(modified).ok()
    }).map(|age| age < Duration::from_secs(24 * 60 * 60)).unwrap_or(false);
    if !fresh {
        return String::new();
    }
    let Ok(text) = fs::read_to_string(path) else { return String::new() };
    if !text.contains("\"schema_version\": 1") && !text.contains("\"schema_version\":1") {
        return String::new();
    }
    let Some(actions) = array_section(&text, "actions") else { return String::new() };
    let mut lines = vec!["Proposed ADR decision queue (derived, non-authoritative):".to_string()];
    for object in top_level_objects(actions).into_iter().take(MAX_RESULTS) {
        let Some(adr_id) = json_string(object, "adr_id") else { continue };
        let Some(command) = json_string(object, "command") else { continue };
        let digits = adr_id.strip_prefix("ADR-").map(|value| {
            (3..=4).contains(&value.len()) && value.chars().all(|ch| ch.is_ascii_digit())
        }).unwrap_or(false);
        if !digits || command != format!("/adr-kit:grill {}", adr_id) {
            continue;
        }
        let reasons = string_array(object, "reasons").into_iter().take(2)
            .map(|reason| reason.replace(['\r', '\n'], " "))
            .collect::<Vec<_>>()
            .join(", ");
        lines.push(format!("- {}: {} -> {}", adr_id, reasons, command));
    }
    if lines.len() == 1 {
        String::new()
    } else {
        let mut output = lines.join("\n");
        output.truncate(output.len().min(MAX_CONTEXT));
        output
    }
}

fn tokens(value: &str) -> Vec<String> {
    value.split(|ch: char| !ch.is_ascii_alphanumeric() && !"._/-".contains(ch))
        .filter(|word| word.len() >= 3)
        .map(|word| word.to_ascii_lowercase())
        .filter(|word| !matches!(word.as_str(), "the" | "and" | "for" | "with" | "from" | "this" | "that"))
        .collect()
}

fn rank(records: &[Record], query: &str) -> Vec<Record> {
    let query_tokens: HashSet<String> = tokens(query).into_iter().collect();
    let overlap = |values: &[String]| -> usize {
        let value_tokens: HashSet<String> = values.iter()
            .flat_map(|value| tokens(value))
            .collect();
        query_tokens.intersection(&value_tokens).count()
    };
    let mut scored: Vec<(usize, String, Record)> = records.iter().map(|record| {
        let score =
            overlap(&record.symbols) * 95
            + overlap(&record.components) * 90
            + overlap(&record.topics) * 75
            + overlap(&record.aliases) * 70
            + overlap(&[record.title.clone()]) * 60
            + overlap(&record.contract) * 50
            + overlap(&[record.summary.clone()]) * 40;
        (score, record.id.clone(), record.clone())
    }).collect();
    scored.sort_by_key(|(score, id, _)| (Reverse(*score), id.clone()));
    scored.into_iter()
        .filter(|item| item.0 > 0)
        .map(|item| item.2)
        .take(MAX_RESULTS)
        .collect()
}

fn glob_match(pattern: &[u8], value: &[u8]) -> bool {
    if pattern.is_empty() {
        return value.is_empty();
    }
    if pattern[0] == b'*' {
        let mut next = 1;
        while next < pattern.len() && pattern[next] == b'*' {
            next += 1;
        }
        if next == pattern.len() {
            return true;
        }
        for index in 0..=value.len() {
            if glob_match(&pattern[next..], &value[index..]) {
                return true;
            }
            if next == 1 && index < value.len() && value[index] == b'/' {
                break;
            }
        }
        false
    } else if !value.is_empty() && (pattern[0] == b'?' || pattern[0].eq_ignore_ascii_case(&value[0])) {
        glob_match(&pattern[1..], &value[1..])
    } else {
        false
    }
}

fn safe_relative(workspace: &Path, value: &str) -> Option<String> {
    if value.len() > 4096 {
        return None;
    }
    let candidate = PathBuf::from(value);
    let joined = if candidate.is_absolute() { candidate } else { workspace.join(candidate) };
    let mut normalized = PathBuf::new();
    for component in joined.components() {
        match component {
            Component::Prefix(_) | Component::RootDir | Component::Normal(_) => normalized.push(component),
            Component::CurDir => {}
            Component::ParentDir => {
                if !normalized.pop() {
                    return None;
                }
            }
        }
    }
    normalized.strip_prefix(workspace).ok().map(|path| path.to_string_lossy().replace('\\', "/"))
}

fn escape_json(value: &str) -> String {
    let mut escaped = String::new();
    for ch in value.chars() {
        match ch {
            '"' => escaped.push_str("\\\""),
            '\\' => escaped.push_str("\\\\"),
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            ch if ch < ' ' => escaped.push(' '),
            ch => escaped.push(ch),
        }
    }
    escaped
}

fn duplicate_event(payload: &str, event: &str) -> bool {
    let Some(session) = json_string(payload, "session_id")
        .or_else(|| json_string(payload, "sessionId")) else {
        return false;
    };
    let signature = format!(
        "{}|{}|{}|{}|{}",
        event,
        json_string(payload, "tool_name")
            .or_else(|| json_string(payload, "toolName"))
            .unwrap_or_default(),
        json_string(payload, "file_path")
            .or_else(|| json_string(payload, "filePath"))
            .or_else(|| json_string(payload, "path"))
            .unwrap_or_default(),
        json_string(payload, "prompt").unwrap_or_default(),
        json_string(payload, "agent_id")
            .or_else(|| json_string(payload, "agentId"))
            .unwrap_or_default(),
    );
    let hash = signature.bytes().fold(0xcbf29ce484222325u64, |value, byte| {
        (value ^ byte as u64).wrapping_mul(0x100000001b3)
    });
    let safe_session: String = session.chars().take(80).map(|ch| {
        if ch.is_ascii_alphanumeric() || "._-".contains(ch) { ch } else { '_' }
    }).collect();
    let state = env::temp_dir().join(format!("adr-kit-hook-{}.seen", safe_session));
    let encoded = format!("{:016x}", hash);
    if fs::read_to_string(&state).ok().as_deref() == Some(encoded.as_str()) {
        return true;
    }
    let temporary = state.with_extension(format!("{}.tmp", std::process::id()));
    if fs::write(&temporary, &encoded).is_ok() {
        let _ = fs::rename(&temporary, &state);
    }
    false
}

fn render(records: &[Record], heading: &str) -> String {
    if records.is_empty() {
        return String::new();
    }
    let mut output = String::from(heading);
    for record in records.iter().take(MAX_RESULTS) {
        output.push_str(&format!(
            "\n- {}: {} — {} (source: docs/adr/{})",
            record.id, record.title, record.summary, record.path
        ));
        if output.len() >= MAX_CONTEXT {
            output.truncate(MAX_CONTEXT);
            break;
        }
    }
    output
}

fn client_grill(client: &str, arguments: &str) -> String {
    let prefix = match client {
        "claude-code-cli" => "/adr-kit:grill",
        "codex-cli" => "$adr-kit:grill",
        "github-copilot-cli" => "adr-kit:grill",
        _ => "adr-kit:grill",
    };
    format!("{} {}", prefix, arguments)
}

fn proposed_advisory(records: &[Record], relative: &str, client: &str) -> String {
    let mut linked: Vec<&Record> = records.iter().filter(|record| {
        record.status == "Proposed" && record.globs.iter().chain(record.verified.iter())
            .any(|pattern| glob_match(pattern.replace('\\', "/").as_bytes(), relative.as_bytes()))
    }).collect();
    linked.sort_by_key(|record| record.id.clone());
    let mut lines: Vec<String> = linked.into_iter().take(MAX_RESULTS).filter_map(|record| {
        let digits = record.id.strip_prefix("ADR-").map(|value| {
            (3..=4).contains(&value.len()) && value.chars().all(|ch| ch.is_ascii_digit())
        }).unwrap_or(false);
        digits.then(|| format!(
            "Proposed ADR implementation link: {} -> {}",
            record.id,
            client_grill(client, &record.id),
        ))
    }).collect();
    let folded = relative.to_ascii_lowercase();
    let sensitive = [
        "architecture/", "infra/", "infrastructure/", "migration/", "migrations/",
        "schema/", "schemas/", "api/", "contract/", "contracts/", "config/",
        "deploy/", "security/", "dockerfile", "compose.yml", "compose.yaml",
        "pyproject.toml", "package.json", "cargo.toml", "go.mod",
    ].iter().any(|marker| folded.contains(marker));
    let source_safe = relative.chars().all(|ch| {
        ch.is_ascii_alphanumeric() || "_./\\ -".contains(ch)
    });
    if lines.is_empty() && sensitive && source_safe {
        lines.push(format!(
            "Possible durable architecture decision -> {}",
            client_grill(client, &format!("--source \"{}\"", relative.replace('\\', "/"))),
        ));
    }
    let mut output = lines.join("\n");
    output.truncate(output.len().min(MAX_CONTEXT));
    output
}

fn normalized_event(value: &str) -> String {
    let compact: String = value.chars().filter(|ch| ch.is_ascii_alphabetic()).map(|ch| ch.to_ascii_lowercase()).collect();
    match compact.as_str() {
        "sessionstart" => "SessionStart",
        "userpromptsubmit" | "userpromptsubmitted" => "UserPromptSubmit",
        "pretooluse" => "PreToolUse",
        "posttooluse" => "PostToolUse",
        "subagentstart" => "SubagentStart",
        "precompact" => "PreCompact",
        "stop" => "Stop",
        "subagentstop" => "SubagentStop",
        "sessionend" => "SessionEnd",
        "permissionrequest" => "PermissionRequest",
        "notification" => "Notification",
        "interrupt" => "Interrupt",
        "postcompact" => "PostCompact",
        _ => value,
    }.to_string()
}

fn response(client: &str, event: &str, context: &str, pre_edit: bool) -> String {
    if context.is_empty() || (client == "github-copilot-cli" && pre_edit) {
        return String::new();
    }
    let context = escape_json(context);
    if client == "claude-code-cli" {
        format!("{{\"suppressOutput\":true,\"hookSpecificOutput\":{{\"hookEventName\":\"{}\",\"additionalContext\":\"{}\"}}}}", event, context)
    } else if client == "codex-cli" {
        format!("{{\"hookSpecificOutput\":{{\"hookEventName\":\"{}\",\"additionalContext\":\"{}\"}}}}", event, context)
    } else {
        format!("{{\"additionalContext\":\"{}\"}}", context)
    }
}

fn run() -> Option<String> {
    let args: Vec<String> = env::args().collect();
    let client = args.windows(2).find(|pair| pair[0] == "--client").map(|pair| pair[1].as_str())?;
    let explicit_event = args.windows(2).find(|pair| pair[0] == "--event").map(|pair| pair[1].clone());
    let mut bytes = Vec::new();
    io::stdin().take(MAX_INPUT + 1).read_to_end(&mut bytes).ok()?;
    if bytes.len() > MAX_INPUT as usize {
        return None;
    }
    let payload = String::from_utf8(bytes).ok()?;
    if json_true(&payload, "adr_kit_disabled") {
        return None;
    }
    let event_raw = explicit_event.or_else(|| {
        json_string(&payload, "hook_event_name")
            .or_else(|| json_string(&payload, "hookEventName"))
            .or_else(|| json_string(&payload, "event"))
    }).unwrap_or_else(|| "Unknown".to_string());
    let event = normalized_event(&event_raw);
    if matches!(event.as_str(), "Stop" | "SubagentStop" | "SessionEnd" | "PermissionRequest" | "Notification" | "Interrupt" | "PostCompact") {
        return None;
    }
    if duplicate_event(&payload, &event) {
        return None;
    }
    let workspace_text = json_string(&payload, "cwd")
        .or_else(|| json_string(&payload, "workspace"))
        .or_else(|| json_string(&payload, "workspace_root"))
        .unwrap_or_else(|| env::current_dir().unwrap_or_default().to_string_lossy().to_string());
    let workspace = fs::canonicalize(&workspace_text).unwrap_or_else(|_| PathBuf::from(workspace_text));
    if event == "SubagentStart" || event == "PreCompact" {
        let parent = json_string(&payload, "parent_context")
            .or_else(|| json_string(&payload, "parentContext"))
            .or_else(|| json_string(&payload, "adr_context"))
            .unwrap_or_default();
        let bounded: String = parent.chars().take(MAX_PARENT.min(MAX_CONTEXT)).collect();
        return Some(response(client, &event, &bounded, false));
    }
    let all_records = load_records(&workspace);
    let records: Vec<Record> = all_records.iter()
        .filter(|record| record.status == "Accepted").cloned().collect();
    let proposed: Vec<Record> = all_records.iter()
        .filter(|record| record.status == "Proposed").cloned().collect();
    if records.is_empty() && proposed.is_empty() && event != "SessionStart" {
        return None;
    }
    let (context, pre_edit) = if event == "SessionStart" {
        let global: Vec<Record> = records.iter()
            .filter(|record| record.context_scope == "global")
            .cloned()
            .collect();
        let orientation = render(&global, "Global Accepted ADR orientation:");
        let queue = load_queue_context(&workspace);
        let context = match (orientation.is_empty(), queue.is_empty()) {
            (false, false) => format!("{}\n\n{}", orientation, queue),
            (false, true) => orientation,
            (true, false) => queue,
            (true, true) => return None,
        };
        (context, false)
    } else if event == "UserPromptSubmit" {
        let prompt = json_string(&payload, "prompt")
            .or_else(|| json_string(&payload, "user_prompt"))
            .or_else(|| json_string(&payload, "userPrompt"))
            .unwrap_or_default();
        let current: Vec<Record> = all_records.iter()
            .filter(|record| matches!(record.status.as_str(), "Accepted" | "Proposed"))
            .cloned()
            .collect();
        let selected = rank(&current, &prompt);
        let governing: Vec<Record> = selected.iter()
            .filter(|record| record.status == "Accepted").cloned().collect();
        let advisory: Vec<Record> = selected.iter()
            .filter(|record| record.status == "Proposed").cloned().collect();
        let governed = render(&governing, "Governing Accepted ADRs relevant to this prompt:");
        let advised = render(&advisory, "Advisory Proposed ADRs relevant to this prompt:");
        let context = match (governed.is_empty(), advised.is_empty()) {
            (false, false) => format!("{}\n{}", governed, advised),
            (false, true) => governed,
            (true, false) => advised,
            (true, true) => return None,
        };
        (context, false)
    } else if event == "PreToolUse" || event == "PostToolUse" {
        let tool = json_string(&payload, "tool_name")
            .or_else(|| json_string(&payload, "toolName"))
            .unwrap_or_default()
            .to_ascii_lowercase()
            .replace('_', "");
        if !matches!(tool.as_str(), "edit" | "multiedit" | "write" | "applypatch" | "create" | "notebookedit") {
            return None;
        }
        let path = json_string(&payload, "file_path")
            .or_else(|| json_string(&payload, "filePath"))
            .or_else(|| json_string(&payload, "notebook_path"))
            .or_else(|| json_string(&payload, "path"))?;
        let relative = safe_relative(&workspace, &path)?;
        let current: Vec<Record> = all_records.iter()
            .filter(|record| matches!(record.status.as_str(), "Accepted" | "Proposed"))
            .cloned()
            .collect();
        let scoped: Vec<Record> = current.iter().filter(|record| {
            record.globs.iter().any(|glob| glob_match(glob.as_bytes(), relative.as_bytes()))
        }).cloned().collect();
        let selected = if scoped.is_empty() { rank(&current, &relative) } else { scoped };
        let governing: Vec<Record> = selected.iter()
            .filter(|record| record.status == "Accepted").cloned().collect();
        let advisory_records: Vec<Record> = selected.iter()
            .filter(|record| record.status == "Proposed").cloned().collect();
        let heading = if event == "PreToolUse" {
            "Governing Accepted ADRs before this edit:"
        } else {
            "Post-edit ADR backstop; verify this change against:"
        };
        let governed = render(&governing, heading);
        let proposed_context = render(&advisory_records, "Advisory Proposed ADRs for this edit:");
        let grill = proposed_advisory(&proposed, &relative, client);
        let advisory = match (proposed_context.is_empty(), grill.is_empty()) {
            (false, false) => format!("{}\n{}", proposed_context, grill),
            (false, true) => proposed_context,
            (true, false) => grill,
            (true, true) => String::new(),
        };
        let context = match (governed.is_empty(), advisory.is_empty()) {
            (false, false) => format!("{}\n{}", governed, advisory),
            (false, true) => governed,
            (true, false) => advisory,
            (true, true) => return None,
        };
        (context, event == "PreToolUse")
    } else {
        return None;
    };
    Some(response(client, &event, &context, pre_edit))
}

fn main() {
    if let Some(output) = run() {
        if !output.is_empty() {
            println!("{}", output);
        }
    }
}
