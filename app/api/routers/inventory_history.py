from fastapi import APIRouter, Depends, status, Body, Response, File, UploadFile, HTTPException
from app.schemas.inventory_history import InventoryHistoryRead, InventoryHistoryFilters, FilteredInventoryHistoryResponse, InventoryHistoryExport, ChartResponse
from app.service.inventory_history_service import InventoryHistoryService
from app.api.deps import get_inventory_history_service  
from typing import List

from io import BytesIO
import datetime

router = APIRouter(prefix="/inventory_history", tags=["inventory_history"])


@router.get(
    "/get_inventory_history_by_warehouse_id/{warehouse_id}",
    response_model=list[InventoryHistoryRead],
    status_code=status.HTTP_200_OK,
    summary="История инвентаризации, привзяанная к складу",
)
async def get_inventory_history_by_warehouse_id(
    warehouse_id: str,
    service: InventoryHistoryService = Depends(get_inventory_history_service),
):
    inventory_history = await service.get_inventory_history_by_warehouse_id(warehouse_id)
    return inventory_history

@router.post(
    "/get_filtered_history/{warehouse_id}",
    response_model=FilteredInventoryHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Получить отфильтрованную историю инвентаризации",
    description="""
    Универсальный endpoint для фильтрации истории инвентаризации.
    """
)
async def get_filtered_inventory_history(
    warehouse_id: str,
    filters: InventoryHistoryFilters = Body(...),
    service: InventoryHistoryService = Depends(get_inventory_history_service),
):
    """
    Единственный endpoint для получения отфильтрованных данных
    """
    # Конвертируем фильтры в dict и убираем None значения
    filters_dict = {
        k: v for k, v in filters.dict().items() 
        if v is not None and v != ""
    }

    sort_by = filters_dict.pop('sort_by', None)
    sort_order = filters_dict.pop('sort_order', 'asc')
    page = filters_dict.pop('page', 1)
    page_size = filters_dict.pop('page_size', 50)
    
    inventory_history = await service.get_filtered_inventory_history(
        warehouse_id=warehouse_id,
        filters=filters_dict,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )

    return FilteredInventoryHistoryResponse(
        data=inventory_history,
    )


@router.post(
    "/inventory_history_export_to_xl/{warehouse_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить exl файл",
    description="""
    Универсальный endpoint для получения exl файла.
    """
)
async def inventory_history_export_to_xl(
    warehouse_id: str,
    record_ids: InventoryHistoryExport = Body(...),
    service: InventoryHistoryService = Depends(get_inventory_history_service),
):
    record_ids_list = record_ids.record_ids
    
    xl: BytesIO = await service.inventory_history_export_to_xl(
        warehouse_id=warehouse_id,
        record_ids=record_ids_list
    )

    file_size = len(xl.getvalue())
    
    # Создаем имя файла с timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"inventory_{warehouse_id}_{timestamp}.xlsx"

    return Response(
        content=xl.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Content-Length": str(file_size),
            "Cache-Control": "no-cache",
            "X-File-Size": str(file_size),
            "X-File-Name": filename
        }
    )


@router.post(
    "/inventory_history_export_to_pdf/{warehouse_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить pdf файл",
    description="""
    Универсальный endpoint для получения pdf файла.
    """
)
async def inventory_history_export_to_pdf(
    warehouse_id: str,
    record_ids: InventoryHistoryExport = Body(...),
    service: InventoryHistoryService = Depends(get_inventory_history_service),
):
    record_ids_list = record_ids.record_ids
    
    pdf: BytesIO = await service.inventory_history_export_to_pdf(
        warehouse_id=warehouse_id,
        record_ids=record_ids_list
    )

    file_size = len(pdf.getvalue())
    
    # Создаем имя файла с timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"inventory_{warehouse_id}_{timestamp}.pdf"

    return Response(
        content=pdf.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{filename}\"",
            "Content-Length": str(file_size),
            "Cache-Control": "no-cache",
            "X-File-Size": str(file_size),
            "X-File-Name": filename
        }
    )

@router.post(
    "/inventory_history_create_graph/{warehouse_id}",
    status_code=status.HTTP_200_OK,
    summary="История инвентаризации, привзяанная к складу",
)
async def inventory_history_create_graph(
    warehouse_id: str,
    record_ids: InventoryHistoryExport = Body(...),
    service: InventoryHistoryService = Depends(get_inventory_history_service),
):
    
    record_ids_list = record_ids.record_ids

    inventory_history = await service.inventory_history_create_graph(        
        warehouse_id=warehouse_id,
        record_ids=record_ids_list
    )

    return ChartResponse(
        data=inventory_history,
    )

@router.get(
    "/inventory_history_unique_zones/{warehouse_id}",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="Получить уникальные зоны склада",
)
async def inventory_history_unique_zones(
    warehouse_id: str,
    service: InventoryHistoryService = Depends(get_inventory_history_service),
) -> List[str]:
    return await service.inventory_history_unique_zones(warehouse_id=warehouse_id)


@router.get(
    "/inventory_history_unique_categories/{warehouse_id}",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="Получить уникальные категории товаров на складе",
)
async def inventory_history_unique_categories(
    warehouse_id: str,
    service: InventoryHistoryService = Depends(get_inventory_history_service),
) -> List[str]:
    return await service.inventory_history_unique_categories(warehouse_id=warehouse_id)


@router.post(
    "/import_inventory_from_csv/{warehouse_id}",
    status_code=status.HTTP_200_OK,
    summary="Получить уникальные категории товаров на складе",
)
async def import_inventory_from_csv(
    warehouse_id: str,
    csv_file: UploadFile = File(..., description="CSV файл с данными инвентаризации"),
    service: InventoryHistoryService = Depends(get_inventory_history_service),
) -> None:
    
    if not csv_file.filename.lower().endswith('.csv'):
        raise HTTPException(400, "Файл должен быть в формате CSV")
    
    # Читаем файл
    try:
        content = await csv_file.read()
        csv_data = content.decode('utf-8-sig')  # utf-8-sig для обработки BOM
    except Exception as e:
        raise HTTPException(400, f"Ошибка чтения файла: {str(e)}")

    await service.import_inventory_from_csv(warehouse_id=warehouse_id, csv_data=csv_data)
