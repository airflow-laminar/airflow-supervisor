from airflow_supervisor import load_config


def test_hydra_config():
    cfg = load_config("config", overrides=["+program=[sleep,echo]", "+rpcinterface=standard", "+inet_http_server=local"])
    assert (
        cfg.to_cfg().strip()
        == "[inet_http_server]\nport=localhost:8000\n\n[supervisord]\n\n[program:sleep]\ncommand=sleep 1000\n\n[program:echo]\ncommand=echo\n\n[rpcinterface:supervisor]\nsupervisor.rpcinterface_factory=supervisor.rpcinterface:make_main_rpcinterface"
    )
