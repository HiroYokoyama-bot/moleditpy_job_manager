# Scheduling and monitoring

On hosts without a cluster scheduler, the helper queue dispatches jobs within
physical-core and memory budgets. It runs only while work remains, keeps its
queue in readable files on the host, and supports dependencies, pausing and
scheduled starts. **Priority** is a number from −1000 to 1000 (default 0): higher
numbers run first, with submission order preserved for equal values. Use
**Set Priority...** or the **Details** window to change it. **Hold** keeps an
individual waiting helper job from starting; **Release** removes that manual
hold while preserving After conditions and priority. Manual holds and After
waits both display **HELD**, with their reasons. A chained-lanes mode is also available.

Use **Wait for previous forced job** with **Force run** to serialize forced jobs on a host.
**Tail File** beside **Tail Log** opens the existing file chooser and tail viewer.

Double-click a waiting job to see its status, priority, and dependencies.
Running jobs open their log; finished jobs open their results.

Cluster jobs use the scheduler's own dependency and submission flags. Configure
**Submit options** on the host or preset for billing groups, resource groups or
other arguments that belong on the `sbatch`/`qsub` command line. Host options
come first; arguments are parsed and quoted individually.

Polling uses one queue-status request per host per cycle. The default is
**120 seconds**, with a minimum of 5 seconds and a warning below 30 seconds.
Polling stops when no jobs are active; connection failures trigger backoff.
Use a longer per-host interval for shared login nodes and disable or slow host
CPU/memory sampling where appropriate. **Refresh Now** requests an update;
**View → Reload List** (`Ctrl+R`) rereads the saved job list.

Generated wrappers write an exit-code sentinel atomically when they exit:
zero means **DONE**, a nonzero code means **FAILED**, and a missing sentinel
after the job disappears means **LOST**. Signal traps record termination codes
such as 143 for SIGTERM. Jobs blocked by a failed dependency show **BLOCKED**.

See the [helper queue](RUNNER.md),
[job states](WORKFLOW.md#reading-job-states), and
[troubleshooting](WORKFLOW.md#troubleshooting).

Dependencies form a chain, with one predecessor per job. There is no workflow
graph or automatic retry; complex cluster dependencies can be supplied through
extra scheduler directives. Job Server has its own queue and feature limits,
described in [its setup guide](JOB_SERVER.md).
