# airflow_supervisor.SupervisorRemoteXMLRPCClient

### *class* airflow_supervisor.SupervisorRemoteXMLRPCClient(cfg: [SupervisorConvenienceConfiguration](airflow_supervisor.SupervisorConvenienceConfiguration.md#airflow_supervisor.SupervisorConvenienceConfiguration))

Bases: `object`

A light wrapper over the supervisor xmlrpc api: [http://supervisord.org/api.html](http://supervisord.org/api.html)

#### \_\_init_\_(cfg: [SupervisorConvenienceConfiguration](airflow_supervisor.SupervisorConvenienceConfiguration.md#airflow_supervisor.SupervisorConvenienceConfiguration))

### Methods

| [`__init__`](#airflow_supervisor.SupervisorRemoteXMLRPCClient.__init__)(cfg)   |    |
|--------------------------------------------------------------------------------|----|
| `getAllProcessInfo`()                                                          |    |
| `getProcessInfo`(name)                                                         |    |
| `getState`()                                                                   |    |
| `readProcessLog`(name)                                                         |    |
| `readProcessStderrLog`(name)                                                   |    |
| `readProcessStdoutLog`(name)                                                   |    |
| `reloadConfig`([start_new])                                                    |    |
| `restart`()                                                                    |    |
| `shutdown`()                                                                   |    |
| `signalProcess`(name, signal)                                                  |    |
| `startAllProcesses`()                                                          |    |
| `startProcess`(name)                                                           |    |
| `stopAllProcesses`()                                                           |    |
| `stopProcess`(name)                                                            |    |
