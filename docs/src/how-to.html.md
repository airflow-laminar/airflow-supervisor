# How-to guides

These guides cover persistent services, monitoring, remote hosts, and task
composition.

## How to keep programs running after the DAG finishes

Disable stop and cleanup, then configure restart behavior:

```yaml
cfg:
  stop_on_exit: false
  cleanup: false
  restart_on_initial: true
  restart_on_retrigger: true
  working_dir: /var/tmp/api-supervisor
  port: "127.0.0.1:9001"
  program:
    api:
      command: /opt/services/api
```

The supervisord instance and program remain active between DAG runs.

## How to limit monitoring

Set Airflow-specific timing fields:

```yaml
cfg:
  check_interval: 00:00:10
  check_timeout: 08:00:00
  runtime: 04:00:00
  maxretrigger: 3
  working_dir: /var/tmp/batch-supervisor
  program:
    batch:
      command: /opt/jobs/batch
```

`check_interval` controls polling, `check_timeout` controls the sensor timeout,
and `runtime` controls the allowed external job duration.

## How to manage a remote host

Use `SupervisorSSHTask` and an Airflow SSH connection:

```yaml
dags:
  remote-supervisor:
    schedule: "@daily"
    tasks:
      run-remote:
        _target_: airflow_supervisor.SupervisorSSHTask
        cfg:
          working_dir: /var/tmp/report-supervisor
          port: "*:9001"
          host: jobs.example.com
          command_prefix: source /etc/profile
          ssh_operator_args:
            ssh_conn_id: supervisor-host
          program:
            report:
              command: /opt/jobs/report
```

SSH tasks manage configuration and the daemon. Program state and control use the
supervisord XML-RPC endpoint configured by `host` and `port`.

## How to use a balanced host

Pass an `airflow-pydantic` `Host` or `HostQuery` through
`SupervisorSSHTask.host`. When the selected host has a pool and the supervisor
configuration does not, the integration uses that pool for its Airflow tasks.

## How to chain the lifecycle with other tasks

The `Supervisor` object behaves like a task group boundary:

```python
prepare >> supervisor >> publish
```

Upstream dependencies attach to `configure_supervisor`. Downstream dependencies
attach to `unconfigure_supervisor`, including when cleanup is represented by a
skip task.
