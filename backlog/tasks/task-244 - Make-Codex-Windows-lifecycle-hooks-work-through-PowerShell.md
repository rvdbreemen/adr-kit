---
id: TASK-244
title: Make Codex Windows lifecycle hooks work through PowerShell
status: Done
assignee: []
created_date: '2026-11-19T06:59:00Z'
updated_date: '2026-11-19T07:21:00Z'
labels: []
dependencies: []
priority: high
type: bug
ordinal: 86000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Codex's environment executor pipelines hook input through PowerShell. ADR Kit 0.61.0 emits an unquoted cmd.exe control operator (& exit /b 0), which Windows PowerShell rejects before starting the hook. Codex reports hook exited with code 1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The generated Windows hook command runs through the Codex PowerShell stdin pipeline and the cmd.exe fallback, including paths with spaces.
- [x] #2 The launcher forwards JSON and returns zero when the plugin root or hook wrapper is missing.
- [x] #3 Verify the updated hook through the local Codex runtime and preserve hook trust review.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced exit 1 using Codex 0.170.0's PowerShell stdin pipeline with the installed 0.61.0 manifest. The patched launcher forwarded JSON and returned exit 0 with empty stderr through cmd.exe, Windows PowerShell, and PowerShell 7. The real installed Python hook returned valid context through all three shells. Local manifest backup was created before updating the seven commandWindows definitions. Codex hooks/list recognizes all seven replacements and marks them modified for regular trust review.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The native Windows command launches safely under both Codex PowerShell and cmd.exe. It forwards stdin explicitly and strips the optional UTF-8 BOM observed with Windows PowerShell 5. The regression runs the real batch dispatcher and requires valid JSON at its Python entry point. All 122 focused tests passed (one platform skip). After regular hook approval, a clean Codex 0.170.0 app-server turn completed ADR Kit SessionStart, UserPromptSubmit and Bash PreToolUse hooks and executed a shell command with no hook failure. The approved local launcher includes the explicit stdin fix; the last PowerShell 5 BOM compatibility change is covered by the repository regression.
<!-- SECTION:FINAL_SUMMARY:END -->
