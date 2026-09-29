import React, { useEffect, useState } from 'react'
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'
import { useWarehouseStore } from '@/store/useWarehouseStore'

type TableRowData = {
	scanned_at: string
	name_article: string
	stock: string
	status: string
	current_zone: string
	robot_id: string
}

type Column<T> = {
	header: string
	accessor: keyof T | ((row: T) => React.ReactNode)
	className?: string
	align?: 'left' | 'center' | 'right'
}

export function ScanStoryTable() {
	const { productScan } = useSocketStore()
	const { selectedWarehouse } = useWarehouseStore()
	const [scanHistory, setScanHistory] = useState<(typeof productScan)[]>([])

	//очищаем таблицу при переключении между складами
	useEffect(() => {
		setScanHistory([])
	}, [selectedWarehouse?.id])

	//сохраняем последние 20 сканирований
	useEffect(() => {
		if (productScan) {
			console.log('productScan:', productScan)
			setScanHistory([productScan])
		}
	}, [productScan])

	// преобразуем данные для таблицы
	const tableData: TableRowData[] = scanHistory
		.flatMap(
			scan =>
				scan?.scans.map(s => ({
					scanned_at: new Date(s.scanned_at).toLocaleString('ru-RU', {
						day: '2-digit',
						month: '2-digit',
						year: '2-digit',
						hour: '2-digit',
						minute: '2-digit',
						second: '2-digit',
					}).replace(',', ' -'), //заменяем запятую на тире
					robot_id: s.robot_id,
					current_zone: s.current_zone,
					name_article: `${s.name} - ${s.article}`,
					stock: String(s.stock),
					status: s.status,
				})) || []
		)
		.filter(Boolean)

	// цвет статуса
	const getStatusColor = (status: string) => {
		switch (status) {
			case 'ok':
				return 'bg-[#0ACB5B]'
			case 'low':
				return 'bg-[#FDA610]'
			case 'critical':
				return 'bg-[#FF4F12]'
			default:
				return 'bg-gray-400'
		}
	}

	const getStatusName = (status: string) => {
		switch (status) {
			case 'ok':
				return 'ОК'
			case 'low':
				return 'Низкий остаток'
			case 'critical':
				return 'Критично'
			default:
				return 'Неизвестен'
		}
	}

	// колонки таблицы
	const columns: Column<TableRowData>[] = [
		{ header: 'время проверки', accessor: 'scanned_at' },
		{ header: 'id робота', accessor: 'robot_id' },
		{ header: 'отдел склада', accessor: 'current_zone' },
		{ header: 'название товара и артикул', accessor: 'name_article' },
		{
			header: 'количество',
			accessor: 'stock',
			className: 'font-semibold',
			align: 'center',
		},
		{
			header: 'статус',
			accessor: (row: TableRowData) => (
				<span
					className={`${getStatusColor(
						row.status
					)} text-black text-[12px] font-medium px-3 py-[3px] rounded-[8px]`}
				>
					{getStatusName(row.status)}
				</span>
			),
			align: 'left',
		},
	]

	return (
		<div className='overflow-hidden rounded-[10px] bg-[#FFFFFF]'>
			<div
				className={cn(
					'max-h-[196px] scroll-padding',
					tableData.length > 0 ? 'overflow-y-auto' : 'overflow-hidden'
				)}
			>
				<Table className='border-separate border-spacing-y-[5px] border-0 [&_*]:border-0 w-full !text-center'>
					<TableHeader className='text-[10px]'>
						<TableRow className='bg-[#FFFFFF] text-black'>
							{columns.map((col, index) => (
								<TableHead key={index} className='p-[0px]'>
									{col.header}
								</TableHead>
							))}
						</TableRow>
					</TableHeader>
					<TableBody className='[&_tr]:h-[30px]'>
						{tableData.length == 0 ? (
							<TableRow>
								<TableCell
									colSpan={columns.length}
									className='text-center py-20'
								>
									<div className='spinner-load-container'>
										<Spinner className='size-5 m-1' /> ожидаем сканирования...
									</div>
								</TableCell>
							</TableRow>
						) : (
							tableData.map((item, i) => (
								<TableRow
									key={i}
									className='bg-[#F6F7F7] row-height rounded-lg mb-2 text-[14px]'
								>
									{columns.map((col, index) => {
										const value =
											typeof col.accessor === 'function'
												? col.accessor(item)
												: (item[col.accessor] as React.ReactNode)

										const isFirst = index === 0
										const isLast = index === columns.length - 1

										return (
											<TableCell
												key={index}
												className={cn(
													'text-center py-[5px]',
													isFirst && 'rounded-l-lg',
													isLast && 'rounded-r-lg text-right'
												)}
											>
												{value}
											</TableCell>
										)
									})}
								</TableRow>
							))
						)}
					</TableBody>
				</Table>
			</div>
		</div>
	)
}
