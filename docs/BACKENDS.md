# Backends

| Backend | Runs on | Requirements and authentication |
|---|---|---|
| OpenSSH (default) | Remote Linux or Windows host | `ssh` and `scp`; keys and ssh-agent; inherits `~/.ssh/config` and supports `ProxyJump` |
| paramiko | Remote Linux or Windows host | Optional `paramiko` package; keys, agent or passwords; `ProxyJump` is refused |
| This machine | Local Linux, macOS or Windows | No network or authentication; bash or the Windows PowerShell scheduler |
| WSL | A Linux distribution on this Windows machine | WSL with bash; no SSH or authentication |
| Job Server (HTTPS) | A LAN computational helper | Optional `cryptography>=50.0.2`; registered device key; bundled HTTP client |

OpenSSH uses batch mode so a background operation cannot wait for an invisible
password prompt. For password-only hosts, choose paramiko and enable **Ask for a
password when connecting**. SSH passwords stay in session memory and are never
written to disk. Unknown host keys require fingerprint approval.

For WSL, choose the distribution in **Hosts...** and use a Linux **Remote root**
such as `~/moleditpy_jobs`. Inputs are copied into the distribution and results
back to Windows. Files within the selected distribution can also be supplied
through `\\wsl.localhost\Ubuntu\...` paths.

See [WSL setup](WORKFLOW.md#running-inside-wsl),
[Job Server setup](JOB_SERVER.md), and the
[security model](SECURITY_MODEL.md).

# Verified backends

These configurations have been checked with real jobs through submission,
completion tracking, log reading and result download. Local and WSL checks
cover both direct background mode and the built-in helper queue.

| Backend | Verified environment | Evidence |
|---|---|---|
| OpenSSH | Linux hosts without a cluster scheduler | Verified in real use |
| paramiko | Linux hosts without a cluster scheduler | Verified in real use |
| This machine — bash | Linux and Git Bash on Windows | Real shell execution in the test suite and CI |
| This machine — Windows scheduler | Native Windows PowerShell | Real direct and queued job execution in Windows CI |
| WSL | Windows with Ubuntu, using real `wsl.exe` and bash | Verified locally with version **3.0.0** on **2026-10-14** |

The Ubuntu checks include Windows input files, `\\wsl.localhost` paths, existing
job directories, failed-command exit codes and jobs that continue after
submission returns. Version **3.0.0** fixes a WSL launch race that could leave a
job pending without a log. Real WSL tests run when a distribution with bash is
available; Windows CI also tests the transport through a shell-backed stand-in.

OpenSSH and paramiko are verified against real hosts; their automated transport
tests additionally use mocked connections. A separate, manually dispatched
[real scheduler workflow](../tests/real_schedulers/README.md) provisions SLURM,
OpenPBS and Grid Engine daemons in disposable environments and exercises them
through real SSH, using synthetic inputs. It covers submission, result transfer,
CPU allocation, cancellation, dependencies and scheduled starts. It does not run
on routine pushes, PRs or releases.

**Verified with real scheduler daemons on 2026-10-25:** all cases passed on
SLURM 21.08.5, OpenPBS 23.06.06, and Debian Grid Engine 8.1.9.
These used synthetic jobs, real SSH and single-node disposable environments.
Single-node lab results do not certify every
Torque/commercial UGE version, multinode MPI/GPU setup or site-specific policy.
