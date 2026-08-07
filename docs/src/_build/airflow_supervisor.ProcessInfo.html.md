# airflow_supervisor.ProcessInfo

### *pydantic model* airflow_supervisor.ProcessInfo[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#ProcessInfo)

Bases: `BaseModel`

#### *field* name *: str* *[Required]*

#### *field* group *: str* *[Required]*

#### *field* state *: ProcessState* *[Required]*

#### *field* description *: str* *[Required]*

#### *field* start *: datetime* *[Required]*

#### *field* stop *: datetime* *[Required]*

#### *field* now *: datetime* *[Required]*

#### *field* spawner *: str* *= ''*

#### *field* exitstatus *: int* *[Required]*

#### *field* logfile *: str* *[Required]*

#### *field* stdout_logfile *: str* *[Required]*

#### *field* stderr_logfile *: str* *[Required]*

#### *field* pid *: int* *[Required]*

#### running()[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#ProcessInfo.running)

#### stopped()[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#ProcessInfo.stopped)

#### done(ok_exitstatuses=None)[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#ProcessInfo.done)

#### ok(ok_exitstatuses=None)[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#ProcessInfo.ok)

#### bad(ok_exitstatuses=None)[[source]](../../../_modules/supervisor_pydantic/client/xmlrpc.html.md#ProcessInfo.bad)
