from airflow.plugins_manager import AirflowPlugin
from airflow_pydantic.migration import _airflow_3

from .viewer import load_snapshot, render_viewer

if _airflow_3():
    from airflow.api_fastapi.auth.managers.models.resource_details import AccessView
    from airflow.api_fastapi.core_api.security import requires_access_view
    from fastapi import Depends, FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(
        dependencies=[Depends(requires_access_view(AccessView.WEBSITE))],
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse(render_viewer(load_snapshot()), headers={"Cache-Control": "no-store"})

    class SupervisorViewerPlugin(AirflowPlugin):
        name = "Supervisor Viewer"
        fastapi_apps = [{"app": app, "url_prefix": "/airflow-supervisor", "name": "Supervisor Viewer"}]  # noqa: RUF012
        external_views = [  # noqa: RUF012
            {
                "name": "Supervisor Viewer",
                "href": "/airflow-supervisor/",
                "destination": "nav",
                "category": "admin",
                "url_route": "airflow-supervisor",
            }
        ]

else:
    from airflow.www.auth import has_access_view
    from flask import Blueprint, make_response

    bp = Blueprint("supervisor_viewer", __name__, url_prefix="/airflow-supervisor")

    @bp.route("/")
    @has_access_view()
    def home():
        response = make_response(render_viewer(load_snapshot()))
        response.headers["Cache-Control"] = "no-store"
        return response

    class SupervisorViewerPlugin(AirflowPlugin):
        name = "Supervisor Viewer"
        flask_blueprints = [bp]  # noqa: RUF012
        appbuilder_menu_items = [  # noqa: RUF012
            {"name": "Supervisor Viewer", "href": "/airflow-supervisor/", "category": "Laminar"}
        ]
