from airflow_supervisor.utils import _get_calling_dag


def get_calling_dag(offset=2):
    return _get_calling_dag(offset)