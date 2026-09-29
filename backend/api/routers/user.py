from fastapi import APIRouter, Depends, HTTPException, status
from backend.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserCreateWithKeycloak,
)
from backend.service.user_service import UserService
from backend.integrations.keycloak import KeycloakService
from backend.api.deps import get_user_service, get_keycloak_service

router = APIRouter(prefix="/user", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_handler(
    user_in: UserCreateWithKeycloak,
    user_service: UserService = Depends(get_user_service),
    keycloak_service: KeycloakService = Depends(get_keycloak_service),
):
    return await user_service.register(user_in, keycloak_service)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_handler(
    user_id: int, user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_handler(
    user_id: int,
    user_update: UserUpdate,
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.update_user(user_id, user_update)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user
