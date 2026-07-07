from .auth import router as auth_router
from .dashboard import router as dashboard_router
from .meetings import router as meetings_router
from .templates import router as templates_router

__all__ = ["auth_router", "dashboard_router", "meetings_router", "templates_router"]
