# airflow_supervisor.SupervisorConfiguration

### *pydantic model* airflow_supervisor.SupervisorConfiguration

Bases: `BaseModel`

#### to_cfg() → str

#### *field* unix_http_server *: UnixHttpServerConfiguration | None* *= None*

#### *field* inet_http_server *: InetHttpServerConfiguration | None* *= None*

#### *field* supervisord *: SupervisordConfiguration* *= SupervisordConfiguration(logfile=None, logfile_maxbytes=None, logfile_backups=None, loglevel=None, pidfile=None, umask=None, nodaemon=None, silent=None, minfds=None, minprocs=None, nocleanup=None, childlogdir=None, user=None, directory=None, strip_ansi=None, environment=None, identifier=None)*

#### *field* supervisorctl *: SupervisorctlConfiguration* *= SupervisorctlConfiguration(serverurl=None, username=None, password=None, prompt=None, history_file=None)*

#### *field* include *: IncludeConfiguration | None* *= None*

#### *field* program *: Dict[str, [ProgramConfiguration](airflow_supervisor.ProgramConfiguration.md#airflow_supervisor.ProgramConfiguration)]* *[Required]*

#### *field* group *: Dict[str, GroupConfiguration] | None* *= None*

#### *field* fcgiprogram *: Dict[str, FcgiProgramConfiguration] | None* *= None*

#### *field* eventlistener *: Dict[str, EventListenerConfiguration] | None* *= None*

#### *field* rpcinterface *: Dict[str, RpcInterfaceConfiguration] | None* *= None*

#### *field* config_path *: Path | None* *= 'supervisord.conf'*

Path to supervisor configuration file, relative to working_dir

#### *field* working_dir *: Path | None* *= ''*

Path to supervisor working directory

#### *classmethod* load(config_dir: str = 'config', config_name: str = '', overrides: list[str] | None = None, , basepath: str = '', \_offset: int = 3) → [SupervisorConfiguration](#airflow_supervisor.SupervisorConfiguration)

#### write()

#### rmdir()

#### start(daemon: bool = False)

#### running()

#### stop()

#### kill()
