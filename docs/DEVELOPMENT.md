# Development

Most protocol and transport tests use fakes or mocks. Execution tests run actual
bash or PowerShell scripts; WSL tests use a stand-in or a real installed
distribution. GUI tests require PySide6. Tests with the real MoleditPy
`PluginContext` also require a main-app checkout and `rdkit`.

CI covers Python 3.11–3.13, real Qt, native Windows and integration with
MoleditPy. Optional test tiers skip when their prerequisites are absent; CI
enforces the tiers assigned to each job. See [CLAUDE.md](../CLAUDE.md) for the
development and release workflow.

The Codecov badge combines the full Linux Qt suite, Windows (including native
desktop tests), and real MoleditPy integration reports. CI preserves each XML
report for comparison with the local `coverage.xml`. Coverage jobs check required
dependencies and a usable Bash; the native Windows and real-context gates fail
if their required tiers skip. Pinned test tooling and shared coverage settings measure the complete
`job_manager` package, without additional coverage exclusions. A combined cross-platform
report can cover more lines than a single-platform local run.
