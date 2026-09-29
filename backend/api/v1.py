from fastapi import APIRouter
from backend.api.routers import robots
from backend.api.routers import product
from backend.api.routers import warehouse
from backend.api.routers import auth
from backend.api.routers import user
from backend.api.routers import inventory_history
from backend.api.routers import docs
from backend.api.routers import predict
from backend.api.routers import scheduled_deliveries
from backend.api.routers import deliveries
from backend.api.routers import shipments
from backend.api.routers import supplies
from backend.api.routers import reports

api_router = APIRouter()
api_router.include_router(robots.router)
api_router.include_router(product.router)
api_router.include_router(warehouse.router)
api_router.include_router(warehouse.router1)
api_router.include_router(inventory_history.router)
api_router.include_router(auth.router)
api_router.include_router(user.router)
api_router.include_router(docs.router)
api_router.include_router(predict.router)
api_router.include_router(scheduled_deliveries.router)
api_router.include_router(shipments.router)
api_router.include_router(deliveries.router)
api_router.include_router(supplies.router)
api_router.include_router(reports.router)


