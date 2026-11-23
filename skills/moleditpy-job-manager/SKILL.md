---
name: moleditpy-job-manager
description: Submit, monitor and collect computational chemistry jobs through a running MoleditPy Job Manager from an AI agent or script, using its local API command line. Use when a task needs a calculation run on a configured host, a queued job waited on, or its results downloaded.
---

# MoleditPy Job Manager

Job Manager submits calculations to hosts the user has already configured,
tracks them, and fetches the results. This skill drives it through the
script client for its local API. It does not configure hosts, and it never
submits through the GUI.

Read `docs/API.md` in this repository for the full field list and every
route. This file is the operating procedure, not a copy of that reference.

## 1. Confirm how the client is invoked on this machine

Do this first, every new environment. The same client is reachable through
several wrappers, and which ones exist depends on how Job Manager was
installed. Guessing wrong either fails outright or, worse, opens the GUI
instead of running the command.

Try the candidates in this order, with a harmless probe (`--help`, then
`ping`), and keep the first one that answers as the command line:

1. A wrapper the user or this environment already provides, such as a shell
   script, alias, batch file or virtualenv launcher that calls the client.
   Prefer it over a bare command. A wrapper usually carries the setup a
   direct call would miss, such as the virtualenv, `MOLEDITPY_JOB_MANAGER_DIR`,
   or `MOLEDITPY_JOB_API_URL` and `MOLEDITPY_JOB_API_TOKEN`. Bypassing it can
   point the client at a different data directory, and therefore at no
   running manager, or at a different one.
2. `moleditpy-job` — the console script, present only when the pip package
   `moleditpy-job-manager` is installed.
3. `python -m job_manager.api_client` — the same program, when the package
   or the unpacked release folder is importable.
4. `moleditpy -r job_manager <subcommand>` — the MoleditPy plugin route, for
   a registry-installed plugin where no console script exists. Verify that
   this build actually dispatches script subcommands before relying on it:
   on a build where it does not, the arguments go to the GUI entry point and
   a window opens instead. Probe with a read-only subcommand such as `ping`
   and check that the reply is the API reply, not a launched window.
5. A copied `job_manager/api_client.py` on its own. It uses only the Python
   standard library and imports nothing else from the plugin, so it can be
   copied next to the calling program and run from there.

Write the chosen form down as one prefix and use it unchanged for the whole
session. Do not mix forms: different forms can resolve to different
installs (the pip copy and the plugin copy are separate) even though they
share one data folder.

Do not confuse the script client with the GUI launchers, which take no
script subcommands: `moleditpy-job-manager`, `python -m job_manager`,
`python __main__.py` in the plugin folder, the `launch_job_manager.bat` and
`launch_host_monitor.bat` files, and `moleditpy -r job_manager` with no
subcommand. If a probe opens a window, that form is a GUI launcher in this
build, not the client.

## 2. Confirm the local API is answering

Run `<prefix> --json ping`. The global flags `--json`, `--url` and
`--token` belong to the client itself, so they come before the subcommand,
never after it: `--json submit ...`, not `submit ... --json`. Put after a
subcommand, `--json` is an unrecognised argument and the client exits with
a usage error before anything runs.

- A JSON reply means the API is up. Note the job and host counts it reports
  and check they are plausible for this user before submitting anything.
- An error saying the API is not running, or that
  `~/.moleditpy/job_manager/api.json` does not exist, means the manager is
  not running or its Local API is off. It is off by default and is a user
  setting: ask the user to start Job Manager and switch on
  **Extensions > Job Manager > Local API...** in MoleditPy, or
  **Settings... > Local API...** in the standalone manager. Do not try to
  switch it on by editing settings files.
- A connection error with `api.json` present usually means a stale file
  from a crashed instance, or a client and a manager pointed at different
  data directories. Check `MOLEDITPY_JOB_MANAGER_DIR` on both sides,
  especially when a wrapper from step 1 sets it for one side only.

The API listens on `127.0.0.1` only and every request carries its token.
Never print the token, copy it into a file, or send it anywhere else.

## 3. Discover before submitting

Never invent a host, preset or command. Read them first:

- `<prefix> --json hosts` for the configured hosts, their schedulers and
  which are enabled.
- `<prefix> --json presets --host <host>` for the saved presets on that
  host. A preset bundles the command and the scheduler settings the user
  already chose, so `submit --preset <name>` is the preferred short path
  when one fits.
- `<prefix> --json host-status <host>` before a large or urgent job, to see
  load, memory and what is already queued.
- When a host is a Job Server, that server also speaks for itself: its
  `GET /api/v1/health` is answered before sign-in and carries the server
  owner's own note in its `description`, saying what that PC is and what it
  is for. If you can reach the server directly, read that note before
  submitting to it and follow what it says about the machine.

## 4. Submit, wait, collect

```bash
<prefix> --json submit <input files> --host <host> --preset <preset>
<prefix> --json submit <input files> --host <host> \
    --command "/opt/orca/orca {input} > {stem}.out" \
    --cpus 8 --memory 16GB --fetch "*.out" --fetch "*.xyz"
<prefix> wait <job id> --download
<prefix> log <job id> --lines 100
<prefix> download <job id> --into <folder>
```

Rules that keep a submission correct:

- One of `--command` or `--preset` is required. The client refuses a
  submission with neither rather than guessing a default command. Naming a
  preset and a field together is fine: the field wins and the stored preset
  is not changed.
- Give the full path to a program, never a bare name. A job script runs in a
  non-login, non-interactive shell on the host, and a bare `orca` can be a
  different program entirely on some systems.
- Pass input files as absolute paths. The manager reads them off this
  machine's disk, and a relative path is resolved against the manager's
  working directory, not the caller's. The Python client absolutises them,
  a raw HTTP caller must do it itself.
- Declare `--cpus` and `--memory` to match what the calculation will
  actually use. On a helper-queue host those declarations are how several
  agents share one machine: jobs start only when their requests fit the
  remaining budget.
- A submit reply comes back while the job is still `UPLOADING`. Poll
  `job <id>`, or block with `wait`, before treating it as queued or done.
- `submit --wait` submits, waits and downloads in one call, when a single
  blocking call is what the task wants.

## 5. Read results by exit code and state, not by text

Always pass `--json` and parse the reply. The human-readable summary is for
people at a terminal.

Exit codes from the client: `0` success, and for `wait` a job that ended
`DONE`; `2` a job that ended in any other terminal state, or a `host-get`
where some files were skipped; `1` the API refused or could not be reached;
`130` interrupted. A bad command line also exits `2`, but it prints a usage
message to stderr and runs nothing, so check stderr before reading a `2`
as a job result.

Terminal states are `DONE`, `FAILED`, `CANCELLED` and `LOST`.

- `FAILED`: read `log <id>` and report the program's own error. Do not
  resubmit unchanged.
- `LOST`: run `recheck <id>` once. It looks for the job's exit-code file
  again and may resolve it to `DONE` or `FAILED`. If it stays `LOST`,
  report what `recheck` says it looked at instead of guessing.
- `BLOCKED` in the display state, or a `blocked_by` field, means a
  predecessor failed and this job cannot start. Report the predecessor
  rather than forcing this job.

## 6. Reading the results afterwards

If the matching MoleditPy result analyzer plugin is also installed, read a
downloaded output file with it instead of parsing the raw text yourself.
All three share the same shape, need no window, and answer in the terminal:

```bash
moleditpy -r orca_result_analyzer     parse <file.out> --json
moleditpy -r gaussian_result_analyzer parse <file.log> --json
moleditpy -r gamess_result_analyzer   parse <file.out> --json
```

Without `--json` each prints a short summary. With it, each prints the
parsed data its own analysis windows use: energies, convergence, frequencies
and the rest, as one JSON object a script can read directly. Check it is
installed first, for example with `moleditpy -r <name> --help`: when it is
not, fall back to the raw output file and say so.

## 7. Full command set

Job commands: `ping`, `hosts`, `presets`, `jobs`, `job`, `submit`,
`cancel`, `download`, `log`, `files`, `wait`, `forget`, `hold`, `release`,
`force`, `priority`, `recheck`.

Host commands: `host-queue`, `host-status`, `host-ls`, `host-stat`,
`host-get`.

Run `<prefix> <subcommand> --help` for the exact flags in this build rather
than relying on this list. Submission fields a build accepts are also
listed in the `ping` reply as `submit_fields`.

## 8. Actions that need the user's word first

The read-only commands above, `submit` of a job the user asked for, `wait`,
`log`, `files` and `download` are the normal working set. Stop and ask
before any of these, even when the user has asked for work in general:

- `cancel`, `forget`, `hold`, `release`, `force` or `priority` on a job you
  did not just submit in this session. It may be someone else's calculation.
- `force` in any case. It starts a job past the queue and past the core and
  memory budgets other agents are relying on. On a Job Server host, force
  run and `priority` are administrator operations, so the account the
  manager signs in with needs that role or the server refuses with an
  error saying so. Force there does not skip an After condition, and a
  held Job Server job does not start even when forced, so release it
  first. On a cluster host force is refused outright, because the
  scheduler owns the order.
- `host-queue` changes, which pause a host's queue or change its limits for
  everyone using that host.
- Submitting a job whose cost is plainly large for the host it targets,
  when the user has not named that scale themselves.

## 9. Python instead of the command line

When the calling program is Python, use the client class rather than
shelling out. It is the same API and the same discovery:

```python
from job_manager.api_client import JobManagerClient

client = JobManagerClient()
job = client.submit(host="myhost", files=["h2o.inp"],
                    command="/opt/orca/orca {input} > {stem}.out")
final = client.wait(job["id"])
if final["state"] != "DONE":
    raise RuntimeError(f"Job {final['id']}: {final['state']}")
paths = client.download(final["id"], wait=True)["files"]
```

## Alternatives for better results

- Prefer a saved preset over a hand-built command line whenever one matches
  the task. It carries the user's own tested settings for that host and
  program.
- Prefer `host-ls`, `host-stat` and `host-get` over submitting a throwaway
  job to look at a file on a host.
- Chain dependent calculations with `submit --after <job id>` instead of
  polling in the agent and submitting the next step by hand.
