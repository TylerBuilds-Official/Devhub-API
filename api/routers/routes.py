from api.routers.health_router    import router as health_router
from api.routers.projects_router  import router as projects_router
from api.routers.deploys_router   import router as deploys_router
from api.routers.jobs_router      import router as jobs_router
from api.routers.logs_router      import router as logs_router
from api.routers.system_router    import router as system_router
from api.routers.upstream_router  import router as upstream_router


ROUTES = [
    health_router,
    projects_router,
    deploys_router,
    jobs_router,
    logs_router,
    system_router,
    upstream_router,
]
