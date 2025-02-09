from airflow.exceptions import AirflowSkipException


def skip_():
    raise AirflowSkipException


__all__ = ("skip_",)
