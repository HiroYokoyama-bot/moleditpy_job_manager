# Job Manager

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22671687.svg)](https://doi.org/10.5281/zenodo.22671687)
[![Tests](https://github.com/HiroYokoyama/moleditpy_job_manager/actions/workflows/tests.yml/badge.svg)](https://github.com/HiroYokoyama/moleditpy_job_manager/actions/workflows/tests.yml)
[![Codecov](https://codecov.io/gh/HiroYokoyama/moleditpy_job_manager/branch/main/graph/badge.svg)](https://app.codecov.io/gh/HiroYokoyama/moleditpy_job_manager)
[![GitHub tag](https://img.shields.io/github/v/tag/HiroYokoyama/moleditpy_job_manager?label=version)](https://github.com/HiroYokoyama/moleditpy_job_manager/tags)
[![GitHub Downloads](https://img.shields.io/github/downloads/HiroYokoyama/moleditpy_job_manager/total)](https://github.com/HiroYokoyama/moleditpy_job_manager/releases)
[![License: GPL v3](https://img.shields.io/badge/License-LGPLv3-blue.svg)](LICENSE)
[![MoleditPy](https://img.shields.io/badge/MoleditPy->=5.0.0-3577F7)](https://github.com/HiroYokoyama/python_molecular_editor)

A [MoleditPy](https://github.com/HiroYokoyama/python_molecular_editor) plugin for
running calculations over SSH, locally, inside WSL, or through a LAN Job Server.
Upload inputs, submit jobs, monitor progress, fetch results and open them in the
editor. It also runs as a standalone desktop application.

AI agents can submit calculations through the local HTTP API, monitor jobs and
retrieve results. Multiple agents can feed the same host-side helper queue,
which schedules jobs within configured CPU and memory budgets to help prevent
overloading a workstation.

![Job Manager with example jobs, signed priorities, and the Tail File action](img/website/job-monitor.png)
![Host Monitor](img/website/host-monitor.png)

## Features

- **Submit calculations** to SLURM, PBS/Torque, SGE/UGE, a background process,
  or [MoleditPy Job Server](https://github.com/HiroYokoyama/moleditpy_job_server). Native Windows jobs use PowerShell;
  WSL jobs use bash inside the selected Linux distribution.
- **Manage workstation resources** with a built-in queue that schedules by
  physical cores and memory. Pause the queue, change its limits, chain jobs,
  or schedule a later start. Jobs continue with MoleditPy closed.
- **Reuse inputs and settings.** Save command templates and resource presets,
  submit files already on the host, or relay a predecessor's outputs into a new
  job. ORCA, Gaussian, Psi4, NWChem, Q-Chem and GAMESS inputs can supply their own
  core and memory requests.
- **Monitor jobs and hosts.** Sort and filter jobs, browse remote files and logs,
  and view CPU, memory, load and every running job in each Host Monitor card.
  Desktop notifications,
  task-bar progress, a tray icon and Slack/Discord/Teams webhooks are available.
- **Collect results.** Download outputs automatically beside the input file and
  open them through the installed result analyzer. Save job lists as SQLite `.pmejdb` or legacy `.pmejbs`,
  export CSV, or rebuild a read-only list from existing result folders.
- **Submit from AI agents and other tools.** The optional [local HTTP API](docs/API.md)
  lets agents and scripts submit jobs, inspect status and logs, and retrieve
  results. Agents using the same helper queue share its resource budgets;
  jobs wait until their requested cores and memory fit.
  ORCA and Gaussian Input Generator Pro provide a **Submit to Cluster...** button.

Instance discovery writes one small registration file on startup and removes it
on shutdown. Liveness checks use an in-memory loopback socket, with no periodic
heartbeat writes. Window activation requests write only when requested. After
updating from 3.3.0 or earlier, quit all existing Job Manager monitors and tray
processes before restarting; the old file-heartbeat protocol is no longer used.

Downloaded files open in the bundled file browser and text viewer, covered
in [results](docs/WORKFLOW.md#5-results). How Job Server connections handle
credentials and reuse authentication is in the [security model](docs/SECURITY_MODEL.md).

Detailed instructions: [Standard workflow](docs/WORKFLOW.md).

## Requirements

- MoleditPy 5.x, or Python 3.10+ with PySide6-Essentials for standalone use.
- **SSH destinations:** an SSH client for OpenSSH, or `pip install paramiko`
  for the optional backend with password authentication.
- **Local destinations:** bash, or the Windows scheduler with PowerShell.
- **WSL destinations:** Windows with a WSL distribution that contains bash.
- **Job Server destinations:** the optional `cryptography>=50.0.2` package.
  The HTTP client is bundled; see [Job Server setup](docs/JOB_SERVER.md).

## Usage

1. Open **Extensions → Job Manager → Job Monitor**, then **Hosts...**.
   Add a host, choose its backend and scheduler, configure its working directory,
   and press **Test Connection**.
2. Select **New Job...**, add inputs, set resources, and choose a command from
   **Template...**. Check **Script preview** before submitting. Save a preset
   to reuse the settings.
3. Watch the job table or open its log. Completed outputs can be downloaded
   automatically and opened in the appropriate result analyzer.

Drop an input file onto the Job Monitor to open a prefilled submission. Dropping
several files opens one submission window per file, each with its own command;
hold **Shift** to submit them together as one job.
For staged inputs, select **Work already on the host** and check the existing
remote directory. Command-only jobs need no input file.

Inputs must not use the same names as Job Manager's execution wrapper, log or
completion files. Conflicts are reported before uploading. Fetching a file that
is no longer available on the host reports an error instead of showing an old
cached copy. Downloading a running job keeps its status monitoring active.

### Command templates and file paths

Templates cover ORCA, Gaussian, CP2K, GAMESS, MOPAC, NWChem, Psi4, PySCF,
Quantum ESPRESSO, VASP and xTB. Use the full executable path when needed,
especially for ORCA: a bare `orca` can resolve to the Linux screen reader.

Placeholders are written in braces, e.g. `{input}`. Save custom commands
through **Template... → Save current command as...**.

The input table shows **File**, **Folder** and **Status**. Add or paste paths,
or drag files onto the dialog. **Move up / Move down** selects the first input
used by `{input}`. Inputs with the same upload filename must be renamed or
submitted separately.

See [command placeholders](docs/COMMAND_PLACEHOLDERS.md) and the
[standard workflow](docs/WORKFLOW.md#3-submit) for examples and program-specific
requirements.

## Backends

Five backends: OpenSSH (the default), paramiko, this machine, WSL and Job
Server over HTTPS. They differ in where the job runs, how you sign in and
what has to be installed, and each one has been checked with real jobs.

The full comparison, the password and host-key behaviour, the WSL path
rules and the verification record are in [backends](docs/BACKENDS.md).

## Scheduling and monitoring

On a host without a cluster scheduler, the built-in helper queue dispatches
jobs within physical-core and memory budgets, with priorities, holds,
dependencies and scheduled starts. Cluster hosts use their scheduler's own
flags instead. Polling, job states and the completion sentinel are covered
in [scheduling and monitoring](docs/SCHEDULING.md).

## Standalone mode

Launch the full Job Manager without opening MoleditPy, or without installing
it at all — see [Job Manager without MoleditPy](docs/STANDALONE.md):

```bash
pip install moleditpy-job-manager
moleditpy-job-manager
moleditpy-job-manager --host-monitor
```

From the plugin folder or the release zip, `python -m job_manager` does the same.
With MoleditPy 5.3 or later, the installed plugin starts the same way without
opening the editor: `moleditpy -r job_manager` (add `-m` for the Host Monitor).
Followed by a command, such as `moleditpy -r job_manager submit ...`, it runs the
script command line described below instead and opens no window.

Standalone uses the same hosts, job list, downloads and notifications as
the plugin. The Windows launchers, the tray option and what a second launch
does are in [Job Manager without MoleditPy](docs/STANDALONE.md).

## Integrations

### AI agents and automation

An AI agent running on the same machine as Job Manager can use the HTTP API,
Python client or command-line client to submit calculations without opening the
submission dialog. It can list configured hosts and presets, check host load
and queue status, submit jobs, read logs, cancel jobs and download results.
A ready-made operating procedure for agents is kept as a skill:
[moleditpy-job-manager](skills/moleditpy-job-manager/SKILL.md).

For multiple agents targeting one workstation, use the same host profile
with **Queueing** set to **Queue them with a helper on the host**: the shared
queue starts each job only when its declared CPU and memory requests fit the
remaining budget. How the budgets work is in the
[helper queue guide](docs/RUNNER.md#scheduling-on-resources).

Enable **Local API...** under **Extensions → Job Manager**, or under
**Settings...** in the standalone Job Manager, and keep Job Manager running. The API is off by default, requires a token and binds only to
`127.0.0.1`. The bundled client discovers the active endpoint and token.

### Input generators and scripts

ORCA and Gaussian Input Generator Pro offer **Submit to Cluster...** beside
Save when Job Manager is installed. Other plugins can call
`job_manager.submit_file(paths, name="")` through the host's plugin list.

External programs and AI agents can use the bundled command-line or Python
client. The same commands are reachable however Job Manager was installed:
`moleditpy-job submit ...` after `pip install`, and
`moleditpy -r job_manager submit ...` for the plugin installed in MoleditPy
5.3+. Given a command, Job Manager opens no window; it talks to the one
already running, whose Local API must be switched on. Command-line and
Python examples are in the [API documentation](docs/API.md).

### Web monitor and notifications

Enable **Serve the Host Monitor to a browser** in **Settings... → Web Monitor**
for a read-only browser dashboard. It binds to `127.0.0.1`; **Links and
Tailscale...** can publish it to your tailnet after HTTPS certificates are
enabled. The monitor works from the tray process too, and samples hosts only
while someone is viewing the page.

See the [web monitor guide](docs/WEB_MONITOR.md) for setup, access controls,
refresh intervals and data usage. For desktop alerts and Slack/Discord/Teams
webhooks, see [notifications](docs/WORKFLOW.md#being-told-when-a-job-ends).

## Where your data lives

Persistent state is stored in `~/.moleditpy/job_manager/`, outside the plugin
folder so updates preserve it: settings, the job list, downloads and the API
tokens. The file-by-file list, the job-list formats and the conversion rules
are in [data files](docs/DATA_FILES.md).

## Documentation

| Guide | Covers |
|---|---|
| [Standard workflow](docs/WORKFLOW.md) | Setup, submission, results, notifications and troubleshooting |
| [Backends](docs/BACKENDS.md) | The five backends compared, sign-in behaviour and the verification record |
| [Scheduling and monitoring](docs/SCHEDULING.md) | Helper queue priorities and holds, polling, job states and the completion sentinel |
| [Data files](docs/DATA_FILES.md) | Where settings, job lists and tokens live, and the job-list formats |
| [Without MoleditPy](docs/STANDALONE.md) | pip install, the standalone app and command line, sharing data with the plugin |
| [Job Server](docs/JOB_SERVER.md) | LAN server setup, authentication and supported operations |
| [Helper queue](docs/RUNNER.md) | Dispatch, dependencies, resource budgets and queue files |
| [Command placeholders](docs/COMMAND_PLACEHOLDERS.md) | Command fields and expansion rules |
| [Local API](docs/API.md) | AI agents, external clients, endpoints and authentication |
| [Web monitor](docs/WEB_MONITOR.md) | Browser dashboard, Tailscale and data usage |
| [Architecture](docs/ARCHITECTURE.md) | Service layers, threading, polling and plugin integration |
| [Security model](docs/SECURITY_MODEL.md) | Credentials, host keys, downloads and trust boundaries |
| [Development](docs/DEVELOPMENT.md) | Test tiers, CI coverage and the release workflow |

## Development

```bash
pip install -e ".[all]" -r requirements-test.txt
python -m pytest tests/ -q -n auto --cov=job_manager --cov-report=term-missing --cov-report=xml
ruff format job_manager tests
ruff check job_manager tests
```

Test tiers, CI coverage and the release workflow are described in
[development notes](docs/DEVELOPMENT.md) and [CLAUDE.md](CLAUDE.md).

## License

GNU Lesser General Public License v3.0. See [LICENSE](LICENSE).

## Licensing scope

First-party code in this migration is LGPL-3.0-or-later. See [LICENSE](LICENSE), [COPYING](COPYING) and [dependency/provenance terms](LICENSING.md). Third-party components and historical releases retain their own terms.
