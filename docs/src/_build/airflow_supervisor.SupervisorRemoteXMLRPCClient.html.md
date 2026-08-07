# airflow_supervisor.SupervisorRemoteXMLRPCClient

### *class* airflow_supervisor.SupervisorRemoteXMLRPCClient(cfg: [SupervisorConvenienceConfiguration](airflow_supervisor.SupervisorConvenienceConfiguration.html.md#airflow_supervisor.SupervisorConvenienceConfiguration))[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#SupervisorRemoteXMLRPCClient)

Bases: `object`

A light wrapper over the supervisor xmlrpc api: [http://supervisord.org/api.html](http://supervisord.org/api.html)

#### \_\_init_\_(cfg: [SupervisorConvenienceConfiguration](airflow_supervisor.SupervisorConvenienceConfiguration.html.md#airflow_supervisor.SupervisorConvenienceConfiguration))[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#SupervisorRemoteXMLRPCClient.__init__)

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
