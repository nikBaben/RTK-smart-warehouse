from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserCreateWithKeycloak
from app.service.user_service import UserService
from app.service.keycloak_service import KeycloakService
from app.api.deps import get_user_service, get_keycloak_service

router = APIRouter(prefix="/user", tags=["users"])

def parse_name(full_name: str) -> tuple[str, str]:
    if not full_name or not full_name.strip():
        return "User", "User"
    
    name_parts = full_name.strip().split()
    
    if len(name_parts) == 0:
        return "User", "User"
    elif len(name_parts) == 1:
        # Только одно имя - используем его как first_name, last_name = "User"
        return name_parts[0], "User"
    elif len(name_parts) == 2:
        # Имя и фамилия
        return name_parts[0], name_parts[1]
    else:
        # Более двух слов: первое слово - имя, остальные - фамилия
        return name_parts[0], " ".join(name_parts[1:])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_handler(
    user_in: UserCreateWithKeycloak,
    user_service: UserService = Depends(get_user_service),
    keycloak_service: KeycloakService = Depends(get_keycloak_service)
):
    try:
        # Парсим имя на first_name и last_name
        first_name, last_name = parse_name(user_in.name)
        
        # 1. Создаем пользователя в Keycloak
        keycloak_user_id = await keycloak_service.create_verified_user(
            email=user_in.email,
            password=user_in.password,
            first_name=first_name,
            last_name=last_name,
            username=user_in.email  # используем email как username
        )
        
        # 2. Создаем пользователя в БД приложения и связываем с Keycloak ID
        user = await user_service.create_user_with_keycloak(
            user_create=user_in,
            kkid=keycloak_user_id
        )
        
        return user
        
    except ValueError as e:
        # Удаляем пользователя из Keycloak если создание в БД не удалось
        if 'keycloak_user_id' in locals():
            await keycloak_service.delete_user(keycloak_user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Откатываем изменения в Keycloak при любой ошибке
        if 'keycloak_user_id' in locals():
            await keycloak_service.delete_user(keycloak_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )



@router.get("/{user_id}", response_model=UserResponse)
async def get_user_handler(
    user_id: int,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user_handler(
    user_id: int,
    user_update: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    user = await user_service.update_user(user_id, user_update)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user