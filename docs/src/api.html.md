# API reference

## Airflow lifecycle

| [`Supervisor`](_build/airflow_supervisor.Supervisor.md#airflow_supervisor.Supervisor)(dag, cfg, \*\*kwargs)                                                |                                                   |
|------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| [`SupervisorSSH`](_build/airflow_supervisor.SupervisorSSH.md#airflow_supervisor.SupervisorSSH)(dag, cfg[, host, port])                                     |                                                   |
| [`SupervisorAirflowConfiguration`](_build/airflow_supervisor.SupervisorAirflowConfiguration.md#airflow_supervisor.SupervisorAirflowConfiguration)          | Settings that MUST be set when running in airflow |
| [`SupervisorSSHAirflowConfiguration`](_build/airflow_supervisor.SupervisorSSHAirflowConfiguration.md#airflow_supervisor.SupervisorSSHAirflowConfiguration) |                                                   |
| [`SupervisorTask`](_build/airflow_supervisor.SupervisorTask.md#airflow_supervisor.SupervisorTask)                                                          |                                                   |
| [`SupervisorTaskArgs`](_build/airflow_supervisor.SupervisorTaskArgs.md#airflow_supervisor.SupervisorTaskArgs)                                              |                                                   |
| [`SupervisorSSHTask`](_build/airflow_supervisor.SupervisorSSHTask.md#airflow_supervisor.SupervisorSSHTask)                                                 |                                                   |
| [`SupervisorSSHTaskArgs`](_build/airflow_supervisor.SupervisorSSHTaskArgs.md#airflow_supervisor.SupervisorSSHTaskArgs)                                     |                                                   |
| [`load_airflow_config`](_build/airflow_supervisor.load_airflow_config.md#airflow_supervisor.load_airflow_config)([config_dir, ...])                        |                                                   |
| [`load_airflow_ssh_config`](_build/airflow_supervisor.load_airflow_ssh_config.md#airflow_supervisor.load_airflow_ssh_config)([config_dir, ...])            |                                                   |

## Re-exported supervisor models

| [`SupervisorConfiguration`](_build/airflow_supervisor.SupervisorConfiguration.md#airflow_supervisor.SupervisorConfiguration)                                  |                                                                                                                    |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| [`SupervisorConvenienceConfiguration`](_build/airflow_supervisor.SupervisorConvenienceConfiguration.md#airflow_supervisor.SupervisorConvenienceConfiguration) | Convenience layer, settings that MUST be set when running via convenience API                                      |
| [`ProgramConfiguration`](_build/airflow_supervisor.ProgramConfiguration.md#airflow_supervisor.ProgramConfiguration)                                           |                                                                                                                    |
| [`SupervisorRemoteXMLRPCClient`](_build/airflow_supervisor.SupervisorRemoteXMLRPCClient.md#airflow_supervisor.SupervisorRemoteXMLRPCClient)(cfg)              | A light wrapper over the supervisor xmlrpc api: [http://supervisord.org/api.html](http://supervisord.org/api.html) |
| [`ProcessInfo`](_build/airflow_supervisor.ProcessInfo.md#airflow_supervisor.ProcessInfo)                                                                      |                                                                                                                    |
