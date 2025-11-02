from fastapi import APIRouter, Depends, status,Query
from app.schemas.product import ProductCreate, ProductRead,ProductEdit
from app.service.product_service import ProductService
from app.api.deps import get_product_service  
from app.api.deps import keycloak_auth_middleware

router = APIRouter(prefix="/products", tags=["products"])#dependencies=[Depends(keycloak_auth_middleware)]

@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать товар",
)
async def create_product(
    payload: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    product = await service.create_product(payload)
    return product

@router.patch(
        "/{product_id}", 
        response_model=ProductRead,
        summary="Редактировать товар",
)
async def patch_product(
    product_id: str,
    payload: ProductEdit,
    service: ProductService = Depends(get_product_service),
):
    return await service.edit_product(product_id, payload)


@router.delete(
        "/{product_id}", 
        summary="Удалить товар",
)
async def delete_product(
    product_id: str,
    service: ProductService = Depends(get_product_service),
    
):
    return await service.delete_product(product_id)

@router.get(
    "/get_products_by_warehouse_id/{warehouse_id}",
    response_model=list[ProductRead],
    status_code=status.HTTP_200_OK,
    summary="Список товаров, привязанных к складу",
)
async def get_products_by_warehouse_id(
    warehouse_id: str,
    service: ProductService = Depends(get_product_service),
):
    robots = await service.get_products_by_warehouse_id(warehouse_id)
    return robots

