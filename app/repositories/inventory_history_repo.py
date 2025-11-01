from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, Date, or_, distinct, func
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from io import BytesIO
import pandas as pd
import xlsxwriter
import csv
from io import StringIO

import uuid

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io

import os

from app.models.inventory_history import InventoryHistory
from app.models.delivery import ScheduledDelivery
from app.models.product import Product
from app.models.warehouse import Warehouse


class InventoryHistoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def get(self, id: str) -> Optional[InventoryHistory]:
        return await self.session.scalar(
            select(InventoryHistory).where(InventoryHistory.id == id)
        )
    
    async def get_all_by_warehouse_id(self, warehosue_id: str):
        result = await self.session.execute(
            select(InventoryHistory).where(InventoryHistory.warehouse_id == warehosue_id)
        )
        return list(result.scalars().all())
    

    async def get_filtered_inventory_history(
        self, 
        warehouse_id: str,
        filters: Dict[str, Any], 
        sort_by: str, 
        sort_order: str,
        page: int,
        page_size: int
    ) -> Tuple[List[Tuple[InventoryHistory, Any, int]], int]:
        
        discrepancy = InventoryHistory.stock - func.coalesce(ScheduledDelivery.quantity, 0)

        query = select(InventoryHistory, ScheduledDelivery.quantity, discrepancy.label('discrepancy')
        ).outerjoin(
            ScheduledDelivery,
            InventoryHistory.product_id == ScheduledDelivery.product_id
        ).filter(
            InventoryHistory.warehouse_id == warehouse_id
        )
        
        if zone_filter := filters.get('zone_filter'):
            query = query.filter(InventoryHistory.current_zone.in_(zone_filter))
        
        # Фильтр по категории
        if category_filter := filters.get('category_filter'):
            query = query.filter(InventoryHistory.category.in_(category_filter))
        
        # Фильтр по статусу
        if status_filter := filters.get('status_filter'):
            query = query.filter(InventoryHistory.status.in_(status_filter))

        date_from = filters.get('date_from')
        date_to = filters.get('date_to')
        if date_from:
            query = query.filter(cast(InventoryHistory.created_at, Date) >= date_from)
        if date_to:
            query = query.filter(cast(InventoryHistory.created_at, Date) <= date_to)

                # Фильтр по поисковой строке (name и article)
        if search_string := filters.get('search_string'):
            search_pattern = f"%{search_string}%"
            query = query.filter(
                or_(
                    InventoryHistory.name.ilike(search_pattern),
                    InventoryHistory.article.ilike(search_pattern)
                )
            )

                # Обработка периодов (кнопки)
        period_filters = []
        period_buttons = filters.get('period_buttons', [])
        
        if 'today' in period_buttons:
            today = datetime.now().date()
            period_filters.append(cast(InventoryHistory.created_at, Date) == today)
        
        if 'yesterday' in period_buttons:
            yesterday = datetime.now().date() - timedelta(days=1)
            period_filters.append(cast(InventoryHistory.created_at, Date) == yesterday)
        
        if 'week' in period_buttons:
            week_ago = datetime.now().date() - timedelta(days=7)
            period_filters.append(cast(InventoryHistory.created_at, Date) >= week_ago)
        
        if 'month' in period_buttons:
            month_ago = datetime.now().date() - timedelta(days=30)
            period_filters.append(cast(InventoryHistory.created_at, Date) >= month_ago)

        # Применяем фильтры периода (OR логика между разными периодами)
        if period_filters:
            query = query.filter(or_(*period_filters))

        if sort_by:
            sort_column = getattr(InventoryHistory, sort_by, None)
            if sort_column is not None:
                if sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
    
        # Пагинация
        offset = (page - 1) * page_size
        count_query = query.with_only_columns(func.count()).order_by(None)
        total_count = await self.session.scalar(count_query)



        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        item = list(result.all())
        print(item, total_count)
        return (item, total_count)
    
    async def inventory_history_export_to_xl(
        self,
        warehouse_id: str,
        record_ids: List[str]  
        ) -> BytesIO:

        query = select(
            InventoryHistory, 
            ScheduledDelivery.quantity  # ожидаемое количество
        ).outerjoin(
            ScheduledDelivery,
            InventoryHistory.product_id == ScheduledDelivery.product_id
        ).filter(
            InventoryHistory.warehouse_id == warehouse_id,
            InventoryHistory.id.in_(record_ids)
        )
    
        result = await self.session.execute(query)
        data = list(result.all())

        # Преобразуем данные в список словарей
        data_list = []
        for item, expected_quantity in data:

            stock_info = f"{expected_quantity or 0}/{item.stock or 0}"

            data_list.append({
                'Дата и время проверки': item.created_at,
                'ID робота': item.robot_id,
                'Зона': item.current_zone,
                'Артикул': item.article,
                'Название': item.name,
                'Категория': item.category,
                'Статус': item.status,
                'Ожидаемое/фактическое количество': stock_info,
                'Склад': item.warehouse_id
            })

        # Создаем DataFrame и Excel файл
        df = pd.DataFrame(data_list)
        df['Дата и время проверки'] = df['Дата и время проверки'].dt.tz_localize(None)
        output = BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='История инвентаря', index=False)
            
            # Форматирование
            workbook = writer.book
            worksheet = writer.sheets['История инвентаря']
            
            header_format = workbook.add_format({
                'bold': True,
                'fg_color': '#FFA789',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Авто-ширина колонок
            for i, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                worksheet.set_column(i, i, min(max_len, 50))

        output.seek(0)
        return output
    
    async def inventory_history_export_to_pdf(
        self,
        warehouse_id: str,
        record_ids: List[str]  
        ) -> BytesIO:

        query = select(
            InventoryHistory, 
            ScheduledDelivery.quantity  # ожидаемое количество
        ).outerjoin(
            ScheduledDelivery,
            InventoryHistory.product_id == ScheduledDelivery.product_id
        ).filter(
            InventoryHistory.warehouse_id == warehouse_id,
            InventoryHistory.id.in_(record_ids)
        )

        query_wh_name = select(Warehouse.name).filter(
           Warehouse.id == warehouse_id,
        )
        
        result = await self.session.execute(query)
        data = list(result.all())
        result_2 = await self.session.execute(query_wh_name)
        wh_name = result_2.scalars().first()

        if not data:
            raise ValueError(
                f"История инвентаризации на складе id '{warehouse_id}' не найдена."
            )

        buffer = io.BytesIO()

        current_dir = os.path.dirname(os.path.abspath(__file__))  # .../app/repositories/
        app_dir = os.path.dirname(current_dir)  # .../app/
        fonts_dir = os.path.join(app_dir, 'font')  # .../app/font/

        # Используем стандартные шрифты без регистрации
        pdfmetrics.registerFont(TTFont('DejaVuSans', os.path.join(fonts_dir, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', os.path.join(fonts_dir, 'DejaVuSans-Bold.ttf')))

        font_normal = 'DejaVuSans'
        font_bold = 'DejaVuSans-Bold'
        
        # Создаем документ в альбомной ориентации
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch, encoding='utf-8')
        
        # Стили
        styles = getSampleStyleSheet()

        # Создаем кастомные стили с правильным шрифтом
        title_style = styles['Heading1'].clone('CustomTitle')
        title_style.alignment = 1
        title_style.fontName = 'DejaVuSans-Bold'
        
        normal_style = styles['Normal'].clone('CustomNormal')
        normal_style.fontName = 'DejaVuSans'

        elements = []
        
        title = Paragraph(f"Отчет по инвентаризации - Склад {wh_name}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Подготовка данных таблицы
        table_data = []
        
        # Заголовки столбцов
        headers = [
            'Дата проверки', 'ID робота', 'Зона', 'Артикул', 
            'Название', 'Категория', 'Статус', 'Ожид/Факт Кол-во', 'Склад'
        ]
        table_data.append(headers)
        
        # Данные строк
        for item, expected_quantity in data:
            # Форматируем дату
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
                wh_name
            ]
            table_data.append(row)
        
        # Создаем таблицу
        table = Table(table_data, repeatRows=1)
        
        # Расчет ширины столбцов
        def calculate_column_widths(data):
            if not data:
                return [1.2 * inch] * len(headers)
            
            num_cols = len(data[0])
            max_widths = [0] * num_cols
            
            for row_idx, row in enumerate(data):
                for col_idx, cell in enumerate(row):
                    cell_text = str(cell) if cell is not None else ""
                    # Для заголовков используем больший коэффициент
                    if row_idx == 0:
                        width = len(cell_text) * 0.2 * inch
                    else:
                        width = len(cell_text) * 0.12 * inch
                    max_widths[col_idx] = max(max_widths[col_idx], width)
            
            # Нормализация ширины
            total_width = sum(max_widths)
            page_width = landscape(A4)[0] - 1 * inch
            
            if total_width > page_width:
                scale_factor = page_width / total_width
                max_widths = [w * scale_factor for w in max_widths]
            
            # Минимальная и максимальная ширина
            min_col_width = 0.6 * inch
            max_col_width = 2 * inch
            
            return [max(min_col_width, min(w, max_col_width)) for w in max_widths]
        
        # Устанавливаем ширину столбцов
        table._argW = calculate_column_widths(table_data)
        
        # Стили таблицы
        table_style = TableStyle([
            # Заголовки
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FFA789')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_bold),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            
            # Данные
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), font_normal),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            
            # Границы
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.black),
            
            # Чередование цветов строк
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
            
            # Выравнивание для числовых колонок
            ('ALIGN', (7, 1), (7, -1), 'CENTER'),  # Количество
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # ID робота
        ])
        
        table.setStyle(table_style)
        elements.append(table)
        
        # Добавляем информацию о количестве записей
        elements.append(Spacer(1, 0.2*inch))
        info_style = styles['Normal'].clone('InfoStyle')
        info_style.fontName = 'DejaVuSans'
        info_style.alignment = 1  # по центру
        info_text = Paragraph(f"Всего записей: {len(data)}", info_style)
        elements.append(info_text)
        
        # Генерируем PDF
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
    

    async def inventory_history_create_graph(
        self,
        warehouse_id: str,
        record_ids: List[str]  
        ) -> Dict[str, List[Tuple[datetime, int]]]:

        query = select(InventoryHistory.name, InventoryHistory.stock, InventoryHistory.created_at).filter(
            InventoryHistory.warehouse_id == warehouse_id,
            InventoryHistory.id.in_(record_ids)
        )
        
        result = await self.session.execute(query)
        rows = result.fetchall()

        chart_data = {}

        for name, stock, created_at in rows:
            if name not in chart_data:
                chart_data[name] = []
        
            chart_data[name].append((
                created_at, 
                stock               
            ))
    
        return chart_data
    

    async def inventory_history_unique_zones(
        self,
        warehouse_id: str
    ) -> List[str]:
        # DISTINCT автоматически убирает повторы
        query = select(distinct(InventoryHistory.current_zone)).filter(
            InventoryHistory.warehouse_id == warehouse_id,
        )
        
        result = await self.session.execute(query)
        zones = result.scalars().all()
        return list(zones)  # Все повторы уже убраны DISTINCT


    async def inventory_history_unique_categories(
        self,
        warehouse_id: str
    ) -> List[str]:
        # DISTINCT автоматически убирает повторы
        query = select(distinct(InventoryHistory.category)).filter(
            InventoryHistory.warehouse_id == warehouse_id,
        )
        
        result = await self.session.execute(query)
        categories = result.scalars().all()
        return list(categories)  # Все повторы уже убраны DISTINCT
    

    async def import_inventory_from_csv(
        self,
        warehouse_id: str,
        csv_data: str,
    ) -> None:
        """
        Импорт данных инвентаризации из CSV с обновлением существующих записей
        """
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

            query = select(Product.category).filter(
            Product.warehouse_id == warehouse_id,
            Product.id == product_id,
            )

            result = await self.session.execute(query)
            category = result.scalar_one_or_none()  
            
            new_record = InventoryHistory(
                id=uuid.uuid4(),
                warehouse_id=warehouse_id,
                product_id=product_id,
                article=product_id,
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