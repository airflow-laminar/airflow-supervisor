# airflow_supervisor.SupervisorRemoteXMLRPCClient

### *class* airflow_supervisor.SupervisorRemoteXMLRPCClient(cfg: [SupervisorConvenienceConfiguration](airflow_supervisor.SupervisorConvenienceConfiguration.html.md#airflow_supervisor.SupervisorConvenienceConfiguration))[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#SupervisorRemoteXMLRPCClient)

Bases: `object`

A light wrapper over the supervisor xmlrpc api: [http://supervisord.org/api.html](http://supervisord.org/api.html)

#### \_\_init_\_(cfg: [SupervisorConvenienceConfiguration](airflow_supervisor.SupervisorConvenienceConfiguration.html.md#airflow_supervisor.SupervisorConvenienceConfiguration))[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#SupervisorRemoteXMLRPCClient.__init__)

### Methods

| [`__init__`](#airflow_supervisor.SupervisorRemoteXMLRPCClient.__init__)(cfg)   |                                                                               |
|--------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| `getAllProcessInfo`()                                                          |                                                                               |
| `getProcessInfo`(name)                                                         |                                                                               |
| `getProcessLogSize`(name, channel)                                             |                                                                               |
| `getProgramProcessInfo`()                                                      | Return configured workloads, excluding event listeners.                       |
| `getState`()                                                                   |                                                                               |
| `readProcessLog`(name)                                                         |                                                                               |
| `readProcessLogChunk`(name, channel[, offset, ...])                            | Read new UTF-8 text, advancing a byte cursor without replaying a tail window. |
| `readProcessStderrLog`(name[, offset, length])                                 |                                                                               |
| `readProcessStdoutLog`(name[, offset, length])                                 |                                                                               |
| `reloadConfig`([start_new])                                                    |                                                                               |
| `restart`()                                                                    |                                                                               |
| `shutdown`()                                                                   |                                                                               |
| `signalProcess`(name, signal)                                                  |                                                                               |
| `startAllProcesses`()                                                          |                                                                               |
| `startProcess`(name)                                                           |                                                                               |
| `stopAllProcesses`()                                                           |                                                                               |
| `stopProcess`(name)                                                            |                                                                               |
