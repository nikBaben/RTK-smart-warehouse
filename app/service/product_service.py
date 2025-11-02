from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.schemas.product import ProductCreate,ProductEdit
from app.repositories.product_repo import ProductRepository
from app.models.product import Product


class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo


    async def create_product(self, data: ProductCreate) -> Product:
        product_id = str(uuid4())

        if data.warehouse_id is None or data.warehouse_id == "":
            raise HTTPException(status_code=400, detail="warehouse_id is required")

        try:
            product = await self.repo.create(
                id=product_id,
                name=data.name,
                category=data.category,
                article = data.article,
                stock = data.stock,
                current_zone = "A",
                current_row = data.current_row,
                current_shelf = data.current_shelf, 
                warehouse_id=data.warehouse_id,   
                check_warehouse_exists=True,    
            )
            return product

        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or getattr(e, "orig", e))

            if code == "23505": 
                raise HTTPException(status_code=409, detail="Product with this id already exists")
            if code == "23502":  
                raise HTTPException(status_code=400, detail="Missing required field (NOT NULL violation)")
            if code == "23503":  
                raise HTTPException(status_code=422, detail="Related entity not found (FK violation)")
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")
        
    async def delete_product(self, product_id: str) -> dict:
        try:
            await self.repo.delete(product_id)
            return {"detail": f"Товар с id '{product_id}' успешно удалён."}

        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or e.orig or e)

            if code == "23503":  # FK violation
                raise HTTPException(
                    status_code=422,
                    detail="Невозможно удалить товар: на него ссылаются другие сущности (FK violation)."
                )
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")
        
    async def edit_product(self, product_id: str,data: ProductEdit) -> Product:
        try:
            new_product = await self.repo.edit(
                id = product_id,
                warehouse_id=data.warehouse_id,
                name=data.name,
                article=data.article,
                stock = data.stock,
                category = data.category,
                current_row = data.current_row,
                current_shelf = data.current_shelf
            )
            return new_product

        # Наш репозиторий бросает ValueError для бизнес-ошибок (не найден / дубль имени)
        except ValueError as e:
            msg = str(e)
            # Поддержим русские и англ. формулировки на всякий
            if "не найден" in msg or "not found" in msg:
                raise HTTPException(status_code=404, detail=msg)
            if "уже существует" in msg or "already exists" in msg:
                raise HTTPException(status_code=409, detail=msg)
            raise HTTPException(status_code=400, detail=msg)

        # Транслируем ошибки целостности БД в HTTP-статусы, аналогично create_warehouse
        except IntegrityError as e:
            code = getattr(getattr(e, "orig", None), "pgcode", None) or getattr(getattr(e, "orig", None), "sqlstate", None)
            detail = str(getattr(getattr(e, "orig", None), "diag", None) or e.orig or e)

            if code == "23505":  # unique_violation
                raise HTTPException(status_code=409, detail="Warehouse with this unique field already exists")
            if code == "23502":  # not_null_violation
                raise HTTPException(status_code=400, detail="Missing required field (NOT NULL violation)")
            if code == "23503":  # foreign_key_violation
                raise HTTPException(status_code=422, detail="Related entity not found (FK violation)")
            raise HTTPException(status_code=500, detail=f"Integrity error: {detail}")

    
    async def get_products_by_warehouse_id(self, warehouse_id: str):
        prodcts = await self.repo.get_all_by_warehouse_id(warehouse_id)
        return prodcts