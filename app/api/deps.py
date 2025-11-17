from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from typing import AsyncIterator
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
import logging
from app.service.predict_service import PredictService

from app.repositories.robot_repo import RobotRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.warehouse_repo import WarehouseRepository
from app.repositories.user_repo import UserRepository
from app.repositories.kkid_user_repo import KkidUserRepository
from app.repositories.inventory_history_repo import InventoryHistoryRepository
from app.repositories.alarm_repo import AlarmRepository
from app.repositories.operations_repo import OperationsRepository
from app.repositories.reports_repo import ReportsRepository
from app.repositories.robot_history_repo import RobotHistoryRepository
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.delivery_items_repo import DeliveryItemsRepository
from app.repositories.shipment_repo import ShipmentRepository
from app.repositories.shipment_items_repo import ShipmentItemsRepository
from app.repositories.predict_repo import PredictRepository

from app.service.robot_service import RobotService
from app.service.product_service import ProductService
from app.service.warehouse_service import WarehouseService 
from app.service.auth_service import AuthService
from app.service.keycloak_service import KeycloakService
from app.service.user_service import UserService
from app.service.inventory_history_service import InventoryHistoryService
from app.service.alarm_service import AlarmService
from app.service.operations_service import OperationsService
from app.service.reports_service import ReportsService
from app.service.delivery_service import DeliveryService
from app.service.shipment_service import ShipmentService

from app.db.session import get_session

logger = logging.getLogger(__name__)
security = HTTPBearer()


#Repositories
def get_robot_repo(db: AsyncSession = Depends(get_session)) -> RobotRepository:
    return RobotRepository(db)

def get_robot_history_repo(db: AsyncSession = Depends(get_session)) -> RobotHistoryRepository: 
    return RobotHistoryRepository(db)

def get_product_repo(db: AsyncSession = Depends(get_session)) -> ProductRepository:
    return ProductRepository(db)

def get_warehouse_repo(db: AsyncSession = Depends(get_session)) -> WarehouseRepository:
    return WarehouseRepository(db)

def get_user_repo(db: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(db)

def get_kkid_user_repo(db: AsyncSession = Depends(get_session)) -> KkidUserRepository:
    return KkidUserRepository(db)

def get_alarm_repo(db: AsyncSession = Depends(get_session)) -> AlarmRepository:
    return AlarmRepository(db)

async def get_delivery_repo(session: AsyncSession = Depends(get_session)) -> DeliveryRepository:
    return DeliveryRepository(session)

async def get_delivery_items_repo(session: AsyncSession = Depends(get_session)) -> DeliveryItemsRepository:
    return DeliveryItemsRepository(session)

async def get_delivery_service(
    delivery_repo: DeliveryRepository = Depends(get_delivery_repo),
    items_repo: DeliveryItemsRepository = Depends(get_delivery_items_repo)
) -> DeliveryService:
    return DeliveryService(delivery_repo, items_repo)

async def get_shipment_repo(session: AsyncSession = Depends(get_session)) -> ShipmentRepository:
    return ShipmentRepository(session)

async def get_shipment_items_repo(session: AsyncSession = Depends(get_session)) -> ShipmentItemsRepository:
    return ShipmentItemsRepository(session)

async def get_shipment_service(
    shipment_repo: ShipmentRepository = Depends(get_shipment_repo),
    items_repo: ShipmentItemsRepository = Depends(get_shipment_items_repo)
) -> ShipmentService:
    return ShipmentService(shipment_repo, items_repo)

#Services
def  get_alarm_service(repo: AlarmRepository = Depends(get_alarm_repo)) -> AlarmService:
    return AlarmService(repo)
    
def get_robot_service(repo: RobotRepository = Depends(get_robot_repo), alarm_service: AlarmService = Depends(get_alarm_service)) -> RobotService:
    return RobotService(repo,alarm_service)

def get_product_service(repo: ProductRepository = Depends(get_product_repo)) -> ProductService:
    return ProductService(repo)

def get_warehouse_service(repo: WarehouseRepository = Depends(get_warehouse_repo)) -> WarehouseService:
    return WarehouseService(repo)

async def get_auth_service(session: AsyncSession = Depends(get_session), userRepo:UserRepository = Depends(get_user_repo), kkidUserRepo: KkidUserRepository = Depends(get_kkid_user_repo)) -> AuthService:
    keycloak_service = KeycloakService()
    user_service = UserService(userRepo, kkidUserRepo)
    return AuthService(keycloak_service, user_service)

async def get_operations_repo(session: AsyncSession = Depends(get_session)) -> OperationsRepository:
    return OperationsRepository(session)

async def get_operations_service(
    operations_repo: OperationsRepository = Depends(get_operations_repo)
) -> OperationsService:
    return OperationsService(operations_repo)

async def get_reports_repo(session: AsyncSession = Depends(get_session)) -> ReportsRepository:
    return ReportsRepository(session)

async def get_reports_service(
    reports_repo: ReportsRepository = Depends(get_reports_repo)
) -> ReportsService:
    return ReportsService(reports_repo)

def get_user_service(userRepo:UserRepository = Depends(get_user_repo), kkidUserRepo: KkidUserRepository = Depends(get_kkid_user_repo)) -> UserService:
    return UserService(userRepo, kkidUserRepo)

def get_keycloak_service() -> KeycloakService:
    return KeycloakService()

def get_inventory_history_repo(db: AsyncSession = Depends(get_session)) -> InventoryHistoryRepository:
    return InventoryHistoryRepository(db)

def get_inventory_history_service(repo: InventoryHistoryRepository = Depends(get_inventory_history_repo)) -> InventoryHistoryService:
    return InventoryHistoryService(repo)

def  get_alarm_service(repo: AlarmRepository = Depends(get_alarm_repo)) -> AlarmService:
    return AlarmService(repo)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_svc: KeycloakService = Depends(get_keycloak_service)
):
    token = credentials.credentials
    logger.info("Getting current user from token")

    if not await auth_svc.validate_token(token):
        logger.error("Token validation failed in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    try:
        user_info = await auth_svc.get_user_info(token)
        logger.info(f"User authenticated: {user_info.get('email')}")
        return user_info
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user information"
        )

async def keycloak_auth_middleware(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_svc: KeycloakService = Depends(get_keycloak_service)
):
    token = credentials.credentials
    logger.info("Middleware token validation")

    if not await auth_svc.validate_token(token):
        logger.error("Middleware token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    logger.info("Middleware token validation successful")
    return token


async def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials

def get_predict_repo(db: AsyncSession = Depends(get_session)) -> PredictRepository:
    return PredictRepository(db)

def get_predict_service(
    repo: PredictRepository = Depends(get_predict_repo),
    product_repo: ProductRepository = Depends(get_product_repo),       # уже есть фабрика get_product_repo
    warehouse_repo: WarehouseRepository = Depends(get_warehouse_repo), # уже есть фабрика get_warehouse_repo
) -> PredictService:
    return PredictService(
        predict_repo=repo,
        product_repo=product_repo,
        warehouse_repo=warehouse_repo,
    )

@asynccontextmanager
async def product_repo_provider() -> AsyncIterator[ProductRepository]:
    async with async_session() as session:
        yield ProductRepository(session)

@asynccontextmanager
async def robot_history_repo_provider() -> AsyncIterator[RobotHistoryRepository]:
    async with async_session() as session:
        yield RobotHistoryRepository(session)

@asynccontextmanager
async def inventory_history_repo_provider() -> AsyncIterator[InventoryHistoryRepository]:
    async with async_session() as session:
        yield InventoryHistoryRepository(session)

@asynccontextmanager
async def robot_repo_provider() -> AsyncIterator[RobotRepository]:
    async with async_session() as session:
        yield RobotRepository(session)
