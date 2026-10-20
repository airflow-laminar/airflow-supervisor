---
myst:
  heading_anchors: 3
---

# API reference

## Lifecycle classes and task models

All names below are exported from `airflow_supervisor`.

| Execution | Lifecycle class | Configuration model                 | `airflow-config` task model |
| --------- | --------------- | ----------------------------------- | --------------------------- |
| Local     | `Supervisor`    | `SupervisorAirflowConfiguration`    | `SupervisorTask`            |
| SSH       | `SupervisorSSH` | `SupervisorSSHAirflowConfiguration` | `SupervisorSSHTask`         |

`Supervisor(dag, cfg, **kwargs)` adds lifecycle tasks to an existing Airflow DAG.
`cfg` accepts a configuration model or a dictionary validated as that model.
Construction requires an active DAG context for internally created tasks.

`SupervisorSSH(dag, cfg, host=None, port=None, **kwargs)` adds the same lifecycle
with SSH operators for remote configuration and daemon commands. Program
operations and checks use XML-RPC. A supplied `Host` overrides the SSH target
and XML-RPC host; a supplied `Port` overrides the supervisord listen port. A
host's pool is used when `cfg.pool` is unset. `command_prefix` can also be passed
as a constructor keyword.

`SupervisorTaskArgs` contains `cfg` and inherited Airflow task arguments.
`SupervisorSSHTaskArgs` adds `host` and `port`, accepting `Host`/`Port` models,
queries of kind `select`, or callables and their import paths. `SupervisorTask`
and `SupervisorSSHTask` resolve their default `operator` to the corresponding
lifecycle class.

The `SupervisorOperator`, `SupervisorOperatorArgs`, `SupervisorSSHOperator`, and
`SupervisorSSHOperatorArgs` names are aliases for the corresponding task models.

### DAG constraints and boundaries

Both lifecycle classes set `catchup=False`, `concurrency=1`,
`max_active_tasks=1`, and `max_active_runs=1` on their DAG.
Generated task IDs use `<dag_id>-<step>`, independent of a task model's `task_id`.
A DAG supports one supervisor lifecycle; multiple programs belong in its
`cfg.program` mapping.

The exposed boundaries are `configure_supervisor`, `start_supervisor`,
`start_programs`, `check_programs`, `restart_programs`, `stop_programs`,
`stop_supervisor`, and `unconfigure_supervisor`. Dependency operators connect
upstream tasks to configuration and downstream tasks to unconfiguration.
`supervisor_client` returns an XML-RPC client for the lifecycle's configuration.

Stop and cleanup steps follow the successful monitoring branch. They are not a
general failure finalizer. With `cleanup=False`, unconfiguration is a skipped
task. With `stop_on_exit=False`, both program stop and unconfiguration are
skipped, and the default downstream trigger rules skip daemon shutdown.

## Configuration models

`SupervisorAirflowConfiguration` extends the re-exported
`SupervisorConvenienceConfiguration`. `SupervisorSSHAirflowConfiguration`
extends it with SSH settings.

### Supervisor fields

| Field                        | Default                     | Meaning                                                                          |
| ---------------------------- | --------------------------- | -------------------------------------------------------------------------------- |
| `program`                    | Required                    | Mapping of program names to `ProgramConfiguration` models.                       |
| `working_dir`                | Derived temporary directory | Instance directory on the worker or SSH host.                                    |
| `config_path`                | `supervisord.conf`          | Configuration path resolved under `working_dir`.                                 |
| `host`                       | `localhost`                 | Host used by the XML-RPC client.                                                 |
| `port`                       | `*:9001`                    | Supervisord HTTP/XML-RPC listen address. Integer ports normalize to `*:<port>`.  |
| `username`, `password`       | `None`                      | Supervisord HTTP/XML-RPC credentials.                                            |
| `protocol`                   | `http`                      | XML-RPC protocol; client ports 80 and 443 select HTTP and HTTPS respectively.    |
| `rpcpath`                    | `/RPC2`                     | XML-RPC request path.                                                            |
| `startsecs`                  | `1`                         | Required startup duration, applied to all programs. `0` permits immediate exits. |
| `startretries`               | `None`                      | Startup retries; when set, overrides each program's value.                       |
| `exitcodes`                  | `[0]`                       | Accepted program exit statuses, applied to all programs.                         |
| `stopsignal`                 | `TERM`                      | Stop signal, applied to all programs.                                            |
| `stopwaitsecs`               | `30`                        | Wait before forced termination.                                                  |
| `stopasgroup`, `killasgroup` | `True`                      | Stop and kill the process group.                                                 |
| `command_timeout`            | `60`                        | Convenience-command timeout in seconds.                                          |

The convenience model forces program `autostart=False` and `autorestart=False`.
Program stdout and stderr files are `<working_dir>/<program>/output.log` and
`error.log`. The daemon log and PID file default to `supervisord.log` and
`supervisord.pid` in the working directory. Serialized configuration is stored
as `pydantic.json`; cleanup removes the working directory, including logs.

### Monitoring and lifecycle fields

| Field                  | Default             | Meaning                                                                                                |
| ---------------------- | ------------------- | ------------------------------------------------------------------------------------------------------ |
| `check_interval`       | 5 seconds           | Polling interval for the `airflow-ha` sensor.                                                          |
| `check_timeout`        | 8 hours             | Sensor timeout.                                                                                        |
| `forward_logs`         | `False`             | Forwards workload stdout and stderr through the Airflow task logger.                                   |
| `log_chunk_size`       | `65536`             | Byte budget per stream per poll; `1`–`1048576`, plus up to 3 bytes for a UTF-8 boundary.               |
| `runtime`              | `None`              | Monitoring end condition relative to `reference_date`.                                                 |
| `endtime`              | `None`              | Time-of-day end condition passed to `airflow-ha`.                                                      |
| `maxretrigger`         | `None`              | Retrigger limit passed to `airflow-ha`.                                                                |
| `reference_date`       | `data_interval_end` | Reference for end conditions; also accepts `start_date` or `logical_date`.                             |
| `pool`                 | `None`              | Airflow pool name or `airflow-pydantic` `Pool`.                                                        |
| `stop_on_exit`         | `True`              | Enables program stop on the success path.                                                              |
| `cleanup`              | `True`              | Enables directory removal when `stop_on_exit` is also true.                                            |
| `restart_on_initial`   | `False`             | Restarts existing programs on an initial Airflow run.                                                  |
| `restart_on_retrigger` | `False`             | Restarts programs in the startup step on retriggered runs; takes precedence over `restart_on_initial`. |

Duration fields accept Python `timedelta` values or numeric seconds and duration
strings in YAML. These fields are passed to `HighAvailabilityOperator` as
`poke_interval`, `timeout`, `runtime`, `endtime`, `maxretrigger`, and
`reference_date`. The sensor uses `mode="poke"`.

### SSH fields

| Field               | Default      | Meaning                                                                                             |
| ------------------- | ------------ | --------------------------------------------------------------------------------------------------- |
| `command_prefix`    | Empty string | Shell commands prepended to remote lifecycle commands.                                              |
| `ssh_operator_args` | `None`       | `airflow-pydantic` `SSHOperatorArgs`, including `ssh_conn_id`, `remote_host`, and command timeouts. |
| `local_or_remote`   | `remote`     | Overrides the local model's `local` default.                                                        |

`ssh_operator_args.ssh_conn_id` selects an Airflow SSH connection. Its port is
the SSH port; `cfg.port` remains the supervisord listen port. `cfg.host` sets the
XML-RPC target and does not by itself select an SSH connection.

`load_airflow_config` aliases `SupervisorAirflowConfiguration.load`.
`load_airflow_ssh_config` aliases `SupervisorSSHAirflowConfiguration.load`.
These load supervisor configuration models. The `airflow_config.load_config`
function loads a collection of declarative DAGs; the
[how-to guides](how-to.md) show that workflow.

## Health checks and diagnostics

`check_supervisor_health(cfg, require_running=True, supervisor_client=None, **context)`
checks an existing instance without configuration, startup, stop, or cleanup.
`cfg` accepts `SupervisorAirflowConfiguration` or a dictionary validated as that
model. `supervisor_client` optionally supplies the XML-RPC client.

With `require_running=True`, every workload must be `STARTING` or `RUNNING`.
With `False`, the configured exit codes and successful completion states are
accepted. Unhealthy, empty, and unreachable instances raise `AirflowException`.
A successful result contains `host`, `healthy`, and a `processes` summary.
Event listeners are excluded from workload health and completion checks.

`supervisor_process_status` XCom contains process `name`, `group`, `state`,
`exitstatus`, `spawnerr`, and `pid`. `supervisor_failure` stores the last unhealthy
process snapshot. `supervisor_log_offsets` stores byte cursors and the run ID;
log contents are written to task logs rather than XCom. Final drains read at
most 16 chunks per stream. The [observability guide](observability.md) provides
Python and YAML configurations.

## Generated API

```{eval-rst}
.. currentmodule:: airflow_supervisor

.. autosummary::
   :toctree: _build

   Supervisor
   SupervisorSSH
   SupervisorAirflowConfiguration
   SupervisorSSHAirflowConfiguration
   SupervisorTask
   SupervisorTaskArgs
   SupervisorSSHTask
   SupervisorSSHTaskArgs
   load_airflow_config
   load_airflow_ssh_config
   check_supervisor_health
```

### Re-exported supervisor models

```{eval-rst}
.. currentmodule:: airflow_supervisor

.. autosummary::
   :toctree: _build

   SupervisorConfiguration
   SupervisorConvenienceConfiguration
   ProgramConfiguration
   SupervisorRemoteXMLRPCClient
   ProcessInfo
```
