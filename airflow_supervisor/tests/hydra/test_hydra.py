from airflow_supervisor import load_config


def test_hydra_config():
    cfg = load_config("config", overrides=["+program=config"])
    assert cfg.to_cfg().strip() == "[supervisord]\n\n[program:test]\ncommand=echo"
