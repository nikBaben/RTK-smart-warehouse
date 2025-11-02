from __future__ import annotations

from typing import Optional, List, Dict, Any, Tuple, Iterable
from datetime import datetime, timedelta, timezone, time
from io import BytesIO, StringIO
import io
import os
import uuid
import csv

import pandas as pd
import xlsxwriter  # noqa: F401 (engine for pandas)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, Date, or_, distinct, func, insert, update
from sqlalchemy.exc import IntegrityError

from fastapi import HTTPException

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.models.inventory_history import InventoryHistory
from app.models.delivery import ScheduledDelivery
from app.models.warehouse import Warehouse
from app.models.product import Product


class InventoryHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    #Read helpers
    async def get(self, id: str) -> Optional[InventoryHistory]:
        return await self.session.scalar(
            select(InventoryHistory).where(InventoryHistory.id == id)
        )

    async def get_all_by_warehouse_id(self, warehouse_id: str) -> List[InventoryHistory]:
        result = await self.session.execute(
            select(InventoryHistory).where(InventoryHistory.warehouse_id == warehouse_id)
        )
        return list(result.scalars().all())

    async def get_filtered_inventory_history(
        self,
        warehouse_id: str,
        filters: Dict[str, Any],
        sort_by: str,
        sort_order: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[Tuple[InventoryHistory, Optional[int], int]], int]:
        discrepancy = InventoryHistory.stock - func.coalesce(ScheduledDelivery.quantity, 0)

        query = (
            select(InventoryHistory, ScheduledDelivery.quantity, discrepancy.label("discrepancy"))
            .outerjoin(
                ScheduledDelivery,
                InventoryHistory.product_id == ScheduledDelivery.product_id,
            )
            .where(InventoryHistory.warehouse_id == warehouse_id)
        )

        if zone_filter := filters.get("zone_filter"):
            query = query.where(InventoryHistory.current_zone.in_(zone_filter))

        if category_filter := filters.get("category_filter"):
            query = query.where(InventoryHistory.category.in_(category_filter))

        if status_filter := filters.get("status_filter"):
            query = query.where(InventoryHistory.status.in_(status_filter))

        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        if date_from:
            query = query.where(cast(InventoryHistory.created_at, Date) >= date_from)
        if date_to:
            query = query.where(cast(InventoryHistory.created_at, Date) <= date_to)

        if search_string := filters.get("search_string"):
            search_pattern = f"%{search_string}%"
            query = query.where(
                or_(
                    InventoryHistory.name.ilike(search_pattern),
                    InventoryHistory.article.ilike(search_pattern),
                )
            )

        # Быстрые кнопки-периоды (OR между ними)
        period_filters = []
        period_buttons = filters.get("period_buttons", [])
        today = datetime.now(timezone.utc).date()
        if "today" in period_buttons:
            period_filters.append(cast(InventoryHistory.created_at, Date) == today)
        if "yesterday" in period_buttons:
            period_filters.append(cast(InventoryHistory.created_at, Date) == (today - timedelta(days=1)))
        if "week" in period_buttons:
            period_filters.append(cast(InventoryHistory.created_at, Date) >= (today - timedelta(days=7)))
        if "month" in period_buttons:
            period_filters.append(cast(InventoryHistory.created_at, Date) >= (today - timedelta(days=30)))
        if period_filters:
            query = query.where(or_(*period_filters))

        if sort_by and hasattr(InventoryHistory, sort_by):
            sort_column = getattr(InventoryHistory, sort_by)
            query = query.order_by(sort_column.desc() if sort_order.lower() == "desc" else sort_column.asc())

        # Count без order_by
        total_count = await self.session.scalar(query.with_only_columns(func.count()).order_by(None))

        # Пагинация
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        items = list(result.all())
        return items, int(total_count or 0)

    #Export: Excel / PDF
    async def inventory_history_export_to_xl(
        self, warehouse_id: str, record_ids: List[str]
    ) -> BytesIO:
        query = (
            select(InventoryHistory, ScheduledDelivery.quantity)
            .outerjoin(
                ScheduledDelivery,
                InventoryHistory.product_id == ScheduledDelivery.product_id,
            )
            .where(
                InventoryHistory.warehouse_id == warehouse_id,
                InventoryHistory.id.in_(record_ids),
            )
        )
        result = await self.session.execute(query)
        data = list(result.all())

        data_list: List[Dict[str, Any]] = []
        for item, expected_quantity in data:
            stock_info = f"{expected_quantity or 0}/{item.stock or 0}"
            data_list.append(
                {
                    "Дата и время проверки": item.created_at,
                    "ID робота": item.robot_id,
                    "Зона": item.current_zone,
                    "Артикул": item.article,
                    "Название": item.name,
                    "Категория": item.category,
                    "Статус": item.status,
                    "Ожидаемое/фактическое количество": stock_info,
                    "Склад": item.warehouse_id,
                }
            )

        df = pd.DataFrame(data_list)
        if not df.empty and pd.api.types.is_datetime64_any_dtype(df["Дата и время проверки"]):
            df["Дата и время проверки"] = df["Дата и время проверки"].dt.tz_localize(None)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="История инвентаря", index=False)
            workbook = writer.book
            worksheet = writer.sheets["История инвентаря"]
            header_format = workbook.add_format({"bold": True, "fg_color": "#FFA789", "border": 1})
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))
        output.seek(0)
        return output

    async def inventory_history_export_to_pdf(
        self, warehouse_id: str, record_ids: List[str]
    ) -> BytesIO:
        query = (
            select(InventoryHistory, ScheduledDelivery.quantity)
            .outerjoin(
                ScheduledDelivery,
                InventoryHistory.product_id == ScheduledDelivery.product_id,
            )
            .where(
                InventoryHistory.warehouse_id == warehouse_id,
                InventoryHistory.id.in_(record_ids),
            )
        )
        result = await self.session.execute(query)
        data = list(result.all())
        if not data:
            raise ValueError(f"История инвентаризации на складе id '{warehouse_id}' не найдена.")

        wh_name = await self.session.scalar(select(Warehouse.name).where(Warehouse.id == warehouse_id))

        buffer = io.BytesIO()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        fonts_dir = os.path.join(app_dir, "font")
        pdfmetrics.registerFont(TTFont("DejaVuSans", os.path.join(fonts_dir, "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", os.path.join(fonts_dir, "DejaVuSans-Bold.ttf")))

        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5 * inch, bottomMargin=0.5 * inch, encoding="utf-8")
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"].clone("CustomTitle"); title_style.alignment = 1; title_style.fontName = "DejaVuSans-Bold"
        normal_style = styles["Normal"].clone("CustomNormal"); normal_style.fontName = "DejaVuSans"

        elements: List[Any] = []
        elements.append(Paragraph(f"Отчет по инвентаризации - Склад {wh_name}", title_style))
        elements.append(Spacer(1, 0.2 * inch))

        headers = [
            "Дата проверки",
            "ID робота",
            "Зона",
            "Артикул",
            "Название",
            "Категория",
            "Статус",
            "Ожид/Факт Кол-во",
            "Склад",
        ]
        table_data: List[List[str]] = [headers]

        for item, expected_quantity in data:
            created_at = item.created_at.strftime("%d.%m.%Y %H:%M") if item.created_at else ""
            stock_info = f"{expected_quantity or 0}/{item.stock or 0}"
            row = [
                created_at,
                str(item.robot_id) if item.robot_id else "",
                item.current_zone or "",
                item.article or "",
                item.name or "",
                item.category or "",
                item.status or "",
                stock_info,
                wh_name or "",
            ]
            table_data.append(row)

        table = Table(table_data, repeatRows=1)

        def calculate_column_widths(data: List[List[str]]) -> List[float]:
            if not data:
                return [1.2 * inch] * len(headers)
            num_cols = len(data[0])
            max_widths = [0.0] * num_cols
            for r_idx, row in enumerate(data):
                for c_idx, cell in enumerate(row):
                    txt = str(cell) if cell is not None else ""
                    width = len(txt) * (0.2 if r_idx == 0 else 0.12) * inch
                    max_widths[c_idx] = max(max_widths[c_idx], width)
            total_width = sum(max_widths); page_width = landscape(A4)[0] - 1 * inch
            if total_width > page_width:
                sf = page_width / total_width
                max_widths = [w * sf for w in max_widths]
            min_w, max_w = 0.6 * inch, 2 * inch
            return [max(min_w, min(w, max_w)) for w in max_widths]

        table._argW = calculate_column_widths(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFA789")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "DejaVuSans-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("ALIGN", (0, 1), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 1), (-1, -1), "DejaVuSans"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("TOPPADDING", (0, 1), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.black),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9F9F9")]),
                    ("ALIGN", (7, 1), (7, -1), "CENTER"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))
        info_style = styles["Normal"].clone("InfoStyle"); info_style.fontName = "DejaVuSans"; info_style.alignment = 1
        elements.append(Paragraph(f"Всего записей: {len(data)}", info_style))
        doc.build(elements)
        buffer.seek(0)
        return buffer

    async def inventory_history_create_graph(
        self, warehouse_id: str, record_ids: List[str]
    ) -> Dict[str, List[Tuple[datetime, int]]]:
        result = await self.session.execute(
            select(InventoryHistory.name, InventoryHistory.stock, InventoryHistory.created_at).where(
                InventoryHistory.warehouse_id == warehouse_id,
                InventoryHistory.id.in_(record_ids),
            )
        )
        rows = result.all()
        chart_data: Dict[str, List[Tuple[datetime, int]]] = {}
        for name, stock, created_at in rows:
            chart_data.setdefault(name, []).append((created_at, stock))
        return chart_data

    async def inventory_history_unique_zones(self, warehouse_id: str) -> List[str]:
        res = await self.session.execute(
            select(distinct(InventoryHistory.current_zone)).where(InventoryHistory.warehouse_id == warehouse_id)
        )
        return list(res.scalars().all())

    async def inventory_history_unique_categories(self, warehouse_id: str) -> List[str]:
        res = await self.session.execute(
            select(distinct(InventoryHistory.category)).where(InventoryHistory.warehouse_id == warehouse_id)
        )
        return list(res.scalars().all())

    async def count_critical_unique_articles(self, warehouse_id: str) -> int:
        val = await self.session.scalar(
            select(func.count(func.distinct(InventoryHistory.article)))
            .where(InventoryHistory.warehouse_id == warehouse_id)
            .where(func.lower(InventoryHistory.status) == "critical")
        )
        return int(val or 0)

    async def get_distinct_warehouse_ids(self) -> List[str]:
        rows = await self.session.execute(select(distinct(InventoryHistory.warehouse_id)))
        return [wid for (wid,) in rows.all() if wid]

    async def get_warehouse_id_by_history_id(self, history_id: str) -> Optional[str]:
        return await self.session.scalar(
            select(InventoryHistory.warehouse_id).where(InventoryHistory.id == history_id)
        )

    async def count_scans_since(self, warehouse_id: str, since_utc: datetime) -> int:
        val = await self.session.scalar(
            select(func.count(InventoryHistory.id))
            .where(InventoryHistory.warehouse_id == warehouse_id)
            .where(InventoryHistory.created_at >= since_utc)
            .where(InventoryHistory.product_id.is_not(None))
        )
        return int(val or 0)

    async def get_last_scans(self, warehouse_id: str, limit: int) -> List[InventoryHistory]:
        try:
            res = await self.session.execute(
                select(InventoryHistory)
                .where(InventoryHistory.warehouse_id == warehouse_id)
                .order_by(InventoryHistory.created_at.desc())
                .limit(limit)
            )
        except Exception:
            res = await self.session.execute(
                select(InventoryHistory)
                .where(InventoryHistory.warehouse_id == warehouse_id)
                .order_by(InventoryHistory.id.desc())
                .limit(limit)
            )
        return list(res.scalars().all())

    #CSV Import with FK safety
    async def import_inventory_from_csv(
        self,
        warehouse_id: str,
        csv_data: str,
    ) -> None:
        buffer = StringIO(csv_data)
        reader = csv.DictReader(buffer, delimiter=';')
        
        for row in reader:
            # Валидация обязательных полей
            required_fields = ['product_id', 'product_name', 'quantity', 'zone', 'date']
            for field in required_fields:
                if not row.get(field):
                    continue
            
            # Парсинг данных
            product_id = row['product_id'].strip()
            product_name = row['product_name'].strip()
            

            quantity = int(row['quantity'])
            
            zone = row['zone'].strip()
            
            date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            
            row_num_val = int(row['row']) if row.get('row') and row['row'].strip() else None
            shelf = int(row['shelf']) if row.get('shelf') and row['shelf'].strip() else None

            query = select(Product.category, Product.article).filter(
                Product.warehouse_id == warehouse_id,
                Product.id == product_id,
            )

            result = await self.session.execute(query)
            row = result.first()

            category, article = row


            new_record = InventoryHistory(
                id=uuid.uuid4(),
                warehouse_id=warehouse_id,
                product_id=product_id,
                article=article,
                name=product_name,
                stock=quantity,
                current_zone=zone,
                current_row=row_num_val,
                current_shelf=shelf,
                robot_id=None,
                created_at=date,
                category=category,
                status="ok"
            )
            self.session.add(new_record)
        

        await self.session.commit()

    async def get_statistic(
        self, 
        warehouse_id: str,
    ) ->Dict:
        
        query = select(
            func.count(InventoryHistory.id).label('total_records'),
            func.count(func.distinct(InventoryHistory.product_id)).label('unique_products_count'),
            func.sum(
                case(
                    (InventoryHistory.stock != func.coalesce(ScheduledDelivery.quantity, 0), 1),
                    else_=0
                )
            ).label('discrepancy_count')
        ).outerjoin(
            ScheduledDelivery,
            InventoryHistory.product_id == ScheduledDelivery.product_id
        ).filter(
            InventoryHistory.warehouse_id == warehouse_id
        )

        result = await self.session.execute(query)

        row = result.first()

        return {
            'total_records': row.total_records or 0,
            'unique_products_count': row.unique_products_count or 0,
            'discrepancy_count': row.discrepancy_count or 0
        }