from typing import Any, List, Dict
from datetime import datetime, timezone
from io import BytesIO, StringIO
import csv
import io
import os
from uuid import uuid4
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from backend.domain.errors import InvalidOperation, NotFound
from backend.ports import InventoryHistoryRepository, Transaction


class InventoryHistoryService:
    def __init__(self, repo: InventoryHistoryRepository, transaction: Transaction):
        self.repo = repo
        self.transaction = transaction

    async def get_inventory_history_by_warehouse_id(self, warehouse_id: str):
        return await self.repo.get_all_by_warehouse_id(warehouse_id)

    async def get_filtered_inventory_history(
        self, warehouse_id, filters, sort_by, sort_order, page, page_size
    ):
        return await self.repo.get_filtered_inventory_history(
            warehouse_id=warehouse_id,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )

    async def inventory_history_create_graph(self, warehouse_id, record_ids):
        return await self.repo.inventory_history_create_graph(warehouse_id, record_ids)

    async def inventory_history_unique_categories(self, warehouse_id):
        return await self.repo.inventory_history_unique_categories(warehouse_id)

    async def inventory_history_unique_zones(self, warehouse_id):
        return await self.repo.inventory_history_unique_zones(warehouse_id)

    async def import_inventory_from_csv(self, warehouse_id: str, csv_data: str) -> None:
        reader = csv.DictReader(StringIO(csv_data.lstrip("\ufeff")), delimiter=";")
        required = {"product_id", "product_name", "quantity", "zone", "date"}
        if not required.issubset(reader.fieldnames or []):
            raise InvalidOperation(
                "CSV должен содержать поля: " + ", ".join(sorted(required))
            )
        async with self.transaction:
            records = []
            for line, row in enumerate(reader, start=2):
                if not any(row.values()):
                    continue
                try:
                    if any(not (row.get(key) or "").strip() for key in required):
                        raise ValueError("не заполнены обязательные поля")
                    quantity = int(row["quantity"])
                    if quantity < 0:
                        raise ValueError("количество не может быть отрицательным")
                    created_at = datetime.strptime(
                        row["date"].strip(), "%Y-%m-%d"
                    ).replace(tzinfo=timezone.utc)
                    row_number = (
                        int(row["row"]) if (row.get("row") or "").strip() else None
                    )
                except (ValueError, TypeError) as error:
                    raise InvalidOperation(f"Строка CSV {line}: {error}") from error
                product = await self.repo.find_product(
                    warehouse_id, row["product_id"].strip()
                )
                if product is None:
                    raise InvalidOperation(
                        f"Строка CSV {line}: товар не найден на складе {warehouse_id}."
                    )
                records.append(
                    dict(
                        id=uuid4(),
                        warehouse_id=warehouse_id,
                        product_id=product.id,
                        article=product.article,
                        name=row["product_name"].strip(),
                        stock=quantity,
                        current_zone=row["zone"].strip(),
                        current_row=row_number,
                        current_shelf=(row.get("shelf") or "").strip() or None,
                        robot_id=None,
                        created_at=created_at,
                        category=product.category,
                        status="ok",
                    )
                )
            await self.repo.add_records(records)
            await self.transaction.commit()

    async def inventory_history_export_to_xl(
        self, warehouse_id: str, record_ids: List[str]
    ) -> BytesIO:
        data = await self.repo.get_export_rows(warehouse_id, record_ids)

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
        if not df.empty and pd.api.types.is_datetime64_any_dtype(
            df["Дата и время проверки"]
        ):
            df["Дата и время проверки"] = df["Дата и время проверки"].dt.tz_localize(
                None
            )

        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="История инвентаря", index=False)
            workbook = writer.book
            worksheet = writer.sheets["История инвентаря"]
            header_format = workbook.add_format(
                {"bold": True, "fg_color": "#FFA789", "border": 1}
            )
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
        data = await self.repo.get_export_rows(warehouse_id, record_ids)
        if not data:
            raise NotFound(
                f"История инвентаризации на складе id '{warehouse_id}' не найдена."
            )

        wh_name = await self.repo.get_warehouse_name(warehouse_id)

        buffer = io.BytesIO()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(current_dir)
        fonts_dir = os.path.join(app_dir, "font")
        pdfmetrics.registerFont(
            TTFont("DejaVuSans", os.path.join(fonts_dir, "DejaVuSans.ttf"))
        )
        pdfmetrics.registerFont(
            TTFont("DejaVuSans-Bold", os.path.join(fonts_dir, "DejaVuSans-Bold.ttf"))
        )

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            encoding="utf-8",
        )
        styles = getSampleStyleSheet()
        title_style = styles["Heading1"].clone("CustomTitle")
        title_style.alignment = 1
        title_style.fontName = "DejaVuSans-Bold"
        normal_style = styles["Normal"].clone("CustomNormal")
        normal_style.fontName = "DejaVuSans"

        elements: List[Any] = []
        elements.append(
            Paragraph(f"Отчет по инвентаризации - Склад {wh_name}", title_style)
        )
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
            created_at = (
                item.created_at.strftime("%d.%m.%Y %H:%M") if item.created_at else ""
            )
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
            total_width = sum(max_widths)
            page_width = landscape(A4)[0] - 1 * inch
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
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F9F9F9")],
                    ),
                    ("ALIGN", (7, 1), (7, -1), "CENTER"),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 0.2 * inch))
        info_style = styles["Normal"].clone("InfoStyle")
        info_style.fontName = "DejaVuSans"
        info_style.alignment = 1
        elements.append(Paragraph(f"Всего записей: {len(data)}", info_style))
        doc.build(elements)
        buffer.seek(0)
        return buffer
