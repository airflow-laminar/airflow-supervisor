# Why Airflow delegates process ownership

Airflow is effective at scheduling and coordinating finite task instances, but
its worker process is not always the right owner for a long-running service or a
process tree. `airflow-supervisor` gives that ownership to a dedicated
supervisord instance while Airflow retains workflow control.

The DAG lifecycle first writes configuration and starts supervisord, then starts
the modeled programs. An `airflow-ha` check maps external states back to Airflow:
completed programs stop successfully, running programs continue, and failed
states retrigger through the restart path. Cleanup reverses the lifecycle.

## Why configuration is persisted

Lifecycle steps can execute in different Airflow task processes. The
`supervisor-pydantic` convenience model writes JSON beside `supervisord.conf`, so
later steps can reconstruct paths, endpoint settings, expected exit codes, and
program defaults without relying on Python object identity.

## Local and SSH execution

Local mode invokes convenience operations on the Airflow worker.
`SupervisorSSH` sends configuration and daemon commands through Airflow's SSH
provider, while program checks and control use supervisord's XML-RPC API. This
split avoids opening a new SSH process for every status poll.

## Comparison with systemd

[airflow-systemd](https://github.com/airflow-laminar/airflow-systemd) delegates
process ownership to the host's existing service manager. Supervisord creates an
application-owned manager with its own configuration, logs, PID, and control
endpoint. The former fits system-managed hosts; the latter is useful when a
self-contained supervisor is easier to deploy or behaves consistently across
hosts.
