from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from datetime import datetime
from app.service.reports_service import ReportsService
from app.schemas.reports import MonthlyReportRequest
from app.api.deps import get_reports_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post(
    "/supplies/monthly-excel",
    summary="Сгенерировать отчет",
)
async def generate_monthly_excel_report(
    request: MonthlyReportRequest,
    reports_service: ReportsService = Depends(get_reports_service)
):
    try:
        excel_data = await reports_service.generate_monthly_report(
            year=request.year,
            warehouse_id=request.warehouse_id,
            months=request.months
        )
        
        filename = f"supplies_report_{request.warehouse_id}_{request.year}.xlsx"
        
        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации отчета: {str(e)}")

@router.get(
    "/supplies/monthly-excel/{warehouse_id}/{year}",
)
async def generate_monthly_excel_report_simple(
    warehouse_id: str,
    year: int,
    reports_service: ReportsService = Depends(get_reports_service)
):
    try:
        excel_data = await reports_service.generate_monthly_report(
            year=year, 
            warehouse_id=warehouse_id
        )
        
        filename = f"supplies_report_{warehouse_id}_{year}.xlsx"
        
        return Response(
            content=excel_data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка генерации отчета: {str(e)}")