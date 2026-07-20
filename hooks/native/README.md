# Native ADR hook host

`adr-hook.rs` is a dependency-free, fail-open implementation of ADR Kit's
bounded hot-path outcomes. The Python implementation remains the portable
fallback and protocol oracle.

Windows release build:

```powershell
rustc -C opt-level=3 -C lto=fat -C codegen-units=1 `
  -C panic=abort -C strip=symbols hooks/native/adr-hook.rs `
  -o hooks/bin/windows-x64/adr-hook.exe
```

The Rust compiler is a release-build tool, not a runtime dependency. Native
hosts read at most 64 KiB from stdin, read only the generated ADR index, never
use the network or a model, never install/update anything, and always fail
open. Release certification compares their protocol behavior with the Python
core and measures the actual subprocess path including startup.
