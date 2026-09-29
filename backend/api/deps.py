"""Composition root: wire SQL adapters to services, sharing one session per request."""

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_session
from backend.db.transaction import SqlAlchemyTransaction
from backend.integrations.keycloak import KeycloakService

from backend.repositories.robot_repo import RobotRepository
from backend.repositories.robot_history_repo import RobotHistoryRepository
from backend.repositories.product_repo import ProductRepository
from backend.repositories.warehouse_repo import WarehouseRepository
from backend.repositories.user_repo import UserRepository
from backend.repositories.kkid_user_repo import KkidUserRepository
from backend.repositories.inventory_history_repo import InventoryHistoryRepository
from backend.repositories.alarm_repo import AlarmRepository
from backend.repositories.operations_repo import OperationsRepository
from backend.repositories.reports_repo import ReportsRepository
from backend.repositories.delivery_repo import DeliveryRepository
from backend.repositories.delivery_items_repo import DeliveryItemsRepository
from backend.repositories.shipment_repo import ShipmentRepository
from backend.repositories.shipment_items_repo import ShipmentItemsRepository
from backend.repositories.predict_repo import PredictRepository
from backend.repositories.scheduled_delivery_repo import ScheduledDeliveryRepository
from backend.service.robot_service import RobotService
from backend.service.product_service import ProductService
from backend.service.warehouse_service import WarehouseService
from backend.service.user_service import UserService
from backend.service.inventory_history_service import InventoryHistoryService
from backend.service.alarm_service import AlarmService
from backend.service.operations_service import OperationsService
from backend.service.reports_service import ReportsService
from backend.service.delivery_service import DeliveryService
from backend.service.shipment_service import ShipmentService
from backend.service.predict_service import PredictService
from backend.service.scheduled_delivery_service import ScheduledDeliveryService
from backend.service.auth_service import AuthService

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_transaction(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyTransaction:
    return SqlAlchemyTransaction(session)


def get_keycloak_service() -> KeycloakService:
    return KeycloakService()


def get_robot_repo(session: AsyncSession = Depends(get_session)) -> RobotRepository:
    return RobotRepository(session)


def get_robot_history_repo(
    session: AsyncSession = Depends(get_session),
) -> RobotHistoryRepository:
    return RobotHistoryRepository(session)


def get_product_repo(session: AsyncSession = Depends(get_session)) -> ProductRepository:
    return ProductRepository(session)


def get_warehouse_repo(
    session: AsyncSession = Depends(get_session),
) -> WarehouseRepository:
    return WarehouseRepository(session)


def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_kkid_user_repo(
    session: AsyncSession = Depends(get_session),
) -> KkidUserRepository:
    return KkidUserRepository(session)


def get_inventory_history_repo(
    session: AsyncSession = Depends(get_session),
) -> InventoryHistoryRepository:
    return InventoryHistoryRepository(session)


def get_alarm_repo(session: AsyncSession = Depends(get_session)) -> AlarmRepository:
    return AlarmRepository(session)


def get_operations_repo(
    session: AsyncSession = Depends(get_session),
) -> OperationsRepository:
    return OperationsRepository(session)


def get_reports_repo(session: AsyncSession = Depends(get_session)) -> ReportsRepository:
    return ReportsRepository(session)


def get_delivery_repo(
    session: AsyncSession = Depends(get_session),
) -> DeliveryRepository:
    return DeliveryRepository(session)


def get_delivery_items_repo(
    session: AsyncSession = Depends(get_session),
) -> DeliveryItemsRepository:
    return DeliveryItemsRepository(session)


def get_shipment_repo(
    session: AsyncSession = Depends(get_session),
) -> ShipmentRepository:
    return ShipmentRepository(session)


def get_shipment_items_repo(
    session: AsyncSession = Depends(get_session),
) -> ShipmentItemsRepository:
    return ShipmentItemsRepository(session)


def get_predict_repo(session: AsyncSession = Depends(get_session)) -> PredictRepository:
    return PredictRepository(session)


def get_scheduled_delivery_repo(
    session: AsyncSession = Depends(get_session),
) -> ScheduledDeliveryRepository:
    return ScheduledDeliveryRepository(session)


def get_product_service(
    repo: ProductRepository = Depends(get_product_repo),
    warehouse_repo: WarehouseRepository = Depends(get_warehouse_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return ProductService(repo, warehouse_repo, transaction)


def get_warehouse_service(
    repo: WarehouseRepository = Depends(get_warehouse_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return WarehouseService(repo, transaction)


def get_robot_service(
    repo: RobotRepository = Depends(get_robot_repo),
    warehouse_repo: WarehouseRepository = Depends(get_warehouse_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return RobotService(repo, warehouse_repo, transaction)


def get_user_service(
    repo: UserRepository = Depends(get_user_repo),
    kkid_user_repo: KkidUserRepository = Depends(get_kkid_user_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return UserService(repo, kkid_user_repo, transaction)


def get_alarm_service(
    repo: AlarmRepository = Depends(get_alarm_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return AlarmService(repo, transaction)


def get_inventory_history_service(
    repo: InventoryHistoryRepository = Depends(get_inventory_history_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return InventoryHistoryService(repo, transaction)


def get_delivery_service(
    repo: DeliveryRepository = Depends(get_delivery_repo),
    delivery_items_repo: DeliveryItemsRepository = Depends(get_delivery_items_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return DeliveryService(repo, delivery_items_repo, transaction)


def get_shipment_service(
    repo: ShipmentRepository = Depends(get_shipment_repo),
    shipment_items_repo: ShipmentItemsRepository = Depends(get_shipment_items_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return ShipmentService(repo, shipment_items_repo, transaction)


def get_scheduled_delivery_service(
    repo: ScheduledDeliveryRepository = Depends(get_scheduled_delivery_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
    warehouse_repo: WarehouseRepository = Depends(get_warehouse_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    return ScheduledDeliveryService(repo, product_repo, warehouse_repo, transaction)


def get_predict_service(
    repo: PredictRepository = Depends(get_predict_repo),
    product_repo: ProductRepository = Depends(get_product_repo),
    warehouse_repo: WarehouseRepository = Depends(get_warehouse_repo),
    transaction: SqlAlchemyTransaction = Depends(get_transaction),
):
    from backend.ml.predictor import Predictor

    return PredictService(repo, product_repo, warehouse_repo, transaction, Predictor)


def get_operations_service(repo: OperationsRepository = Depends(get_operations_repo)):
    return OperationsService(repo)


def get_reports_service(repo: ReportsRepository = Depends(get_reports_repo)):
    return ReportsService(repo)


def get_auth_service(
    identity: KeycloakService = Depends(get_keycloak_service),
    users: UserService = Depends(get_user_service),
) -> AuthService:
    return AuthService(identity, users)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_svc: KeycloakService = Depends(get_keycloak_service),
):
    token = credentials.credentials
    logger.info("Getting current user from token")

    if not await auth_svc.validate_token(token):
        logger.error("Token validation failed in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    try:
        user_info = await auth_svc.get_user_info(token)
        logger.info(f"User authenticated: {user_info.get('email')}")
        return user_info
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to get user information",
        )


async def keycloak_auth_middleware(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_svc: KeycloakService = Depends(get_keycloak_service),
):
    token = credentials.credentials
    logger.info("Middleware token validation")

    if not await auth_svc.validate_token(token):
        logger.error("Middleware token validation failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    logger.info("Middleware token validation successful")
    return token


async def get_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return credentials.credentials
