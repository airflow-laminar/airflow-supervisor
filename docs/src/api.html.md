# API reference

## Airflow lifecycle

| [`Supervisor`](_build/airflow_supervisor.Supervisor.html.md#airflow_supervisor.Supervisor)(dag, cfg, \*\*kwargs)                                                |                                                   |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
| [`SupervisorSSH`](_build/airflow_supervisor.SupervisorSSH.html.md#airflow_supervisor.SupervisorSSH)(dag, cfg[, host, port])                                     |                                                   |
| [`SupervisorAirflowConfiguration`](_build/airflow_supervisor.SupervisorAirflowConfiguration.html.md#airflow_supervisor.SupervisorAirflowConfiguration)          | Settings that MUST be set when running in airflow |
| [`SupervisorSSHAirflowConfiguration`](_build/airflow_supervisor.SupervisorSSHAirflowConfiguration.html.md#airflow_supervisor.SupervisorSSHAirflowConfiguration) |                                                   |
| [`SupervisorTask`](_build/airflow_supervisor.SupervisorTask.html.md#airflow_supervisor.SupervisorTask)                                                          |                                                   |
| [`SupervisorTaskArgs`](_build/airflow_supervisor.SupervisorTaskArgs.html.md#airflow_supervisor.SupervisorTaskArgs)                                              |                                                   |
| [`SupervisorSSHTask`](_build/airflow_supervisor.SupervisorSSHTask.html.md#airflow_supervisor.SupervisorSSHTask)                                                 |                                                   |
| [`SupervisorSSHTaskArgs`](_build/airflow_supervisor.SupervisorSSHTaskArgs.html.md#airflow_supervisor.SupervisorSSHTaskArgs)                                     |                                                   |
| [`load_airflow_config`](_build/airflow_supervisor.load_airflow_config.html.md#airflow_supervisor.load_airflow_config)([config_dir, ...])                        |                                                   |
| [`load_airflow_ssh_config`](_build/airflow_supervisor.load_airflow_ssh_config.html.md#airflow_supervisor.load_airflow_ssh_config)([config_dir, ...])            |                                                   |

## Re-exported supervisor models

| [`SupervisorConfiguration`](_build/airflow_supervisor.SupervisorConfiguration.html.md#airflow_supervisor.SupervisorConfiguration)                                  |                                                                                                                    |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| [`SupervisorConvenienceConfiguration`](_build/airflow_supervisor.SupervisorConvenienceConfiguration.html.md#airflow_supervisor.SupervisorConvenienceConfiguration) | Convenience layer, settings that MUST be set when running via convenience API                                      |
| [`ProgramConfiguration`](_build/airflow_supervisor.ProgramConfiguration.html.md#airflow_supervisor.ProgramConfiguration)                                           |                                                                                                                    |
| [`SupervisorRemoteXMLRPCClient`](_build/airflow_supervisor.SupervisorRemoteXMLRPCClient.html.md#airflow_supervisor.SupervisorRemoteXMLRPCClient)(cfg)              | A light wrapper over the supervisor xmlrpc api: [http://supervisord.org/api.html](http://supervisord.org/api.html) |
| [`ProcessInfo`](_build/airflow_supervisor.ProcessInfo.html.md#airflow_supervisor.ProcessInfo)                                                                      |                                                                                                                    |
