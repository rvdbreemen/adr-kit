: << 'CMDBLOCK'
@echo off
REM Cross-platform fail-open dispatcher for ADR Kit's normalized hook core.
set "HOOK_DIR=%~dp0"
set "ADR_HOOK=%HOOK_DIR%adr-hook.py"
set "ADR_HOOK_NATIVE=%HOOK_DIR%bin\windows-x64\adr-hook.exe"
set "ADR_KIT_EMBEDDED_PYTHON=__ADR_KIT_PYTHON__"
set "ADR_HOOK_EVENT=%~1"
set "ADR_HOOK_CLIENT=%~2"
if "%ADR_HOOK_EVENT%"=="" exit /b 0
if "%ADR_HOOK_CLIENT%"=="" set "ADR_HOOK_CLIENT=claude-code-cli"
REM The native host is opt-in until it passes the parity certification its own
REM README describes. Measured on this repository at v0.44.0: it returned one of
REM four governing ADRs on an edit, four of five at prompt time, and nothing at
REM all for ExitPlanMode. Preferring it silently narrowed governance on Windows.
if "%ADR_KIT_NATIVE_HOOK%"=="1" if exist "%ADR_HOOK_NATIVE%" (
    "%ADR_HOOK_NATIVE%" --client "%ADR_HOOK_CLIENT%" --event "%ADR_HOOK_EVENT%"
    exit /b 0
)
if defined ADR_KIT_PYTHON (
    "%ADR_KIT_PYTHON%" "%ADR_HOOK%" --client "%ADR_HOOK_CLIENT%" --event "%ADR_HOOK_EVENT%"
    exit /b 0
)
if exist "%ADR_KIT_EMBEDDED_PYTHON%" (
    "%ADR_KIT_EMBEDDED_PYTHON%" "%ADR_HOOK%" --client "%ADR_HOOK_CLIENT%" --event "%ADR_HOOK_EVENT%"
    exit /b 0
)
where python3 >nul 2>nul && python3 "%ADR_HOOK%" --client "%ADR_HOOK_CLIENT%" --event "%ADR_HOOK_EVENT%" && exit /b 0
where python >nul 2>nul && python "%ADR_HOOK%" --client "%ADR_HOOK_CLIENT%" --event "%ADR_HOOK_EVENT%" && exit /b 0
where py >nul 2>nul && py -3 "%ADR_HOOK%" --client "%ADR_HOOK_CLIENT%" --event "%ADR_HOOK_EVENT%"
exit /b 0
CMDBLOCK

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
EVENT="${1:-}"
CLIENT="${2:-claude-code-cli}"
[ -n "$EVENT" ] || exit 0
ARCH="$(uname -m 2>/dev/null || true)"
OS="$(uname -s 2>/dev/null || true)"
case "$ARCH" in
  x86_64|amd64) ARCH="x64" ;;
  arm64|aarch64) ARCH="arm64" ;;
esac
case "$OS" in
  Darwin) NATIVE="$SCRIPT_DIR/bin/darwin-$ARCH/adr-hook" ;;
  Linux) NATIVE="$SCRIPT_DIR/bin/linux-$ARCH/adr-hook" ;;
  *) NATIVE="" ;;
esac
# Opt-in for the same reason as the Windows branch above: the native host has
# not passed the parity certification, and a hook that returns fewer governing
# ADRs than the oracle is worse than one that is simply slower.
if [ "${ADR_KIT_NATIVE_HOOK:-}" = "1" ] && [ -n "$NATIVE" ] && [ -x "$NATIVE" ]; then
  "$NATIVE" --client "$CLIENT" --event "$EVENT" || true
  exit 0
fi
PYTHON="${ADR_KIT_PYTHON:-}"
EMBEDDED_PYTHON='__ADR_KIT_PYTHON__'
if [ -z "$PYTHON" ] && [ -x "$EMBEDDED_PYTHON" ]; then
  PYTHON="$EMBEDDED_PYTHON"
fi
if [ -z "$PYTHON" ]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
fi
[ -n "$PYTHON" ] || exit 0
"$PYTHON" "$SCRIPT_DIR/adr-hook.py" --client "$CLIENT" --event "$EVENT" || true
exit 0
