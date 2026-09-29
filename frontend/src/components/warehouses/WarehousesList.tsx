import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuTrigger,
} from '@/components/ui/context-menu'
import { Skeleton } from '@/components/ui/skeleton'
import type { Warehouse } from '../types/warehouse'
import type { FC } from 'react'

type Props = {
	warehouses: Warehouse[]
	selectedWarehouse: Warehouse | null
	loading: boolean
	error: string | null
	onSelect: (warehouse: Warehouse) => void
	onContextMenu?: (warehouse: Warehouse) => void
	onDelete?: (warehouse: Warehouse) => void
}

export const WarehouseList: FC<Props> = ({
	warehouses,
	selectedWarehouse,
	loading,
	error,
	onSelect,
	onContextMenu,
	onDelete,
}) => {
	if (loading) {
		return (
			<div className='space-y-2'>
				{[...Array(14)].map((_, i) => (
					<div
						key={i}
						className='flex justify-between items-center bg-[#F2F3F4] rounded-[10px] px-[10px] py-[10px]'
					>
						<div className='flex items-center gap-3'>
							<Skeleton className='bg-[#CDCED2] h-[20px] w-[120px] rounded-md' />
						</div>
						<div className='text-right space-y-1'>
							<Skeleton className='bg-[#CDCED2] h-[14px] w-[180px] rounded-md' />
							<Skeleton className='bg-[#CDCED2] h-[14px] w-[200px] rounded-md' />
						</div>
					</div>
				))}
			</div>
		)
	}

	if (error) {
		return (
			<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
				не удалось получить данные о складах
			</div>
		)
	}

	return (
		<div className='space-y-2 overflow-y-hidden max-h-[675px]'>
			{warehouses.map(wh => (
				<ContextMenu key={wh.id}>
					<ContextMenuTrigger asChild>
						<div
							onClick={() => onSelect(wh)}
							onContextMenu={() => onContextMenu?.(wh)}
							className={`flex justify-between items-center bg-[#F2F3F4] rounded-[10px] max-h-[60px] px-[10px] py-[10px] cursor-pointer transition-all border-[2px]
                ${
									selectedWarehouse?.id === wh.id
										? 'border-[#7700FF]'
										: 'border border-transparent hover:border-[#7700FF33]'
								}`}
						>
							<div className='flex items-center'>
								<span className='text-[20px] font-medium text-black'>
									{wh.name}
								</span>
							</div>
							<div className='text-right space-y-0'>
								<div className='text-[14px] font-normal text-[#5A606D]'>
									адрес: {wh.address}
								</div>
								<div className='text-[14px] font-normal text-[#5A606D]'>
									текущее количество товаров: {wh.products_count}
								</div>
							</div>
						</div>
					</ContextMenuTrigger>

					<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
						<ContextMenuItem
							className='context-menu-delete'
							onClick={() => onDelete?.(wh)}
						>
							Удалить
						</ContextMenuItem>
					</ContextMenuContent>
				</ContextMenu>
			))}
		</div>
	)
}
