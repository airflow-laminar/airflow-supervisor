import os
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from airflow_supervisor.airflow.viewer import SupervisorSnapshot


def load_snapshot():
    # UI servers use the metadata API; the SDK Variable API is for task execution.
    from airflow.models import Variable

    data = Variable.get(
        os.environ.get("AIRFLOW_SUPERVISOR_SNAPSHOT_KEY", "airflow-supervisor:instances"),
        default_var=None,
        deserialize_json=True,
    )
    return SupervisorSnapshot.model_validate(data) if data else None


def render_viewer(snapshot):
    now = datetime.now(UTC)
    rows = []
    for value in snapshot.instances if snapshot else []:
        age = (now - value.observed_at).total_seconds() if value.observed_at else None
        stale = (now - value.attempted_at).total_seconds() > snapshot.max_age
        status = "STALE" if stale else "REACHABLE" if value.reachable else "UNREACHABLE"
        rows.append({"value": value, "age": round(age) if age is not None else None, "status": status})
    templates = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"), autoescape=select_autoescape()
    )
    return templates.get_template("instances.html").render(snapshot=snapshot, rows=rows)
