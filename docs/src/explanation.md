---
myst:
  heading_anchors: 3
---

# Why Airflow delegates process ownership

An Airflow task instance owns a worker process for part of a workflow. A job
that spawns children or keeps running between DAG runs needs a process manager
with a longer lifetime. `airflow-supervisor` gives supervisord ownership of that
process tree while Airflow schedules, monitors, and stops the workload.

Each lifecycle manages a dedicated supervisord instance. Airflow first writes
its configuration and starts the daemon, then starts the configured programs.
An `airflow-ha` operator checks their state. Successful completion takes the
shutdown path; a running program keeps monitoring active; a failed check takes
the restart and retrigger path.

The convenience configuration disables supervisord's program autostart and
automatic restart. Airflow therefore controls when programs start and when a
failed workload is retriggered. Supervisord still manages process groups and
startup retries.

## Why local execution depends on worker placement

In local mode, lifecycle tasks launch commands and access files on their Airflow
worker. Their XML-RPC client connects to the configured host, usually localhost.
If a later task runs on another host, localhost points to another machine and
the task cannot control the original daemon. Sharing a working directory does
not share the daemon or its network endpoint.

Local execution fits a single worker host. SSH execution fits workloads that
need a stable target host while Airflow tasks may run on different workers.

## Why SSH execution also needs XML-RPC

`SupervisorSSH` uses SSH to write configuration, start and stop the daemon, and
remove files on the remote host. Program start, restart, stop, and status checks
use XML-RPC from the Airflow worker to supervisord. This avoids launching an SSH
command for each status poll.

The two transports have separate addresses and credentials. An Airflow SSH
connection identifies the remote account. The supervisor configuration
identifies the XML-RPC host, listen port, username, and password. SSH access
alone cannot make a remote lifecycle work: the workers also need a route to
the XML-RPC endpoint.

## Why configuration is persisted

Lifecycle steps execute in separate task processes. `supervisor-pydantic`
writes `pydantic.json` beside `supervisord.conf` so later commands can recover
paths, endpoint settings, expected exit codes, and program defaults. The working
directory identifies the instance across those steps and across DAG runs when
cleanup is disabled.

Stopping programs and retaining configuration serve different needs. Finite
batch jobs normally stop the daemon and remove their files. Persistent services
retain the instance between runs, so a later run can monitor or restart it.
Their Airflow monitoring window needs its own end condition because a healthy
service may never exit.

## Python and airflow-config describe the same lifecycle

Inline Python constructs `Supervisor` or `SupervisorSSH` with a typed
configuration model. It keeps the definition beside other Airflow code and
works without `airflow-config`.

`airflow-config` loads YAML into `SupervisorTask` or `SupervisorSSHTask`. Those
models construct the same lifecycle classes. YAML is useful when DAGs share
configuration or use Hydra composition; it adds configuration loading to the
DAG parsing environment. It does not change where jobs execute or how they are
monitored. Local versus SSH execution and Python versus YAML configuration are
independent choices.

## Supervisord and systemd

[airflow-systemd](https://github.com/airflow-laminar/airflow-systemd) delegates
process ownership to the host's existing service manager. Supervisord runs an
application-owned manager with its own configuration, logs, PID, and endpoint.
Systemd fits hosts where services belong in system administration; supervisord
fits workloads that need a separate manager installed with the application.

## Why the viewer uses snapshots

The Supervisor viewer separates observation from web requests. A scheduled task
contacts instances independently and stores the latest snapshot. The page can
then show an unreachable instance without making its connection timeout part of
every page load. Probe timestamps also distinguish failed observation from a
stopped collector. Retained process states are explicitly last-known data.

Multivisor was the first option evaluated for the multi-instance proof of
concept. Version 7.1.0 successfully connected three instances through its
event-listener integration using `supervisor-pydantic` configuration. The
listeners need `SUPERVISOR_USERNAME` and `SUPERVISOR_PASSWORD` when Supervisor's
HTTP interface requires credentials. The SDK's workload controls exclude these
event listeners, so starting or stopping configured programs leaves them running.

Multivisor supplies live state updates and native process logs. Its
[authenticated API](https://github.com/tiagocoutinho/multivisor/blob/55dccb3b6a16a9cb2cb0cca975224daffc687f46/multivisor/server/web.py)
also permits stop, restart, and daemon-shutdown actions. A runtime test confirmed
that a user named `reader` could invoke process stop after login. There is no
separate read-only role in the evaluated version. Keeping its existing UI would
therefore require an additional authorization layer and changes for Airflow
workload links. The Airflow proof of concept uses a smaller view with no control
routes instead.

The snapshot is an operations view for users with Airflow website-view access.
It does not implement per-program visibility rules. Credentials stay in the
collection configuration; only process observations and links reach the viewer.
Airflow's own run/log pages continue to enforce their DAG access rules.

This proof of concept does not establish minimum-ready counts, recover failed
hosts, or coordinate deployments. It also does not infer the latest workload
run: supplied associations can become outdated. Shared workload observations
and host identity can replace these manual associations in the fleet roadmap.
