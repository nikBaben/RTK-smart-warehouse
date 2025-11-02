import { UserAvatar } from '../ui/UserAvatar'
import SelectWarehouse from '../ui/SelectWarehouse'
import { useWarehouseSocket } from '@/hooks/useWarehouseSocket'
import { useWarehouseStore } from '@/store/useWarehouseStore'
import { useSupplyStore } from '@/store/useSupplyStore'
import { useEffect } from 'react'

import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuTrigger,
} from '@/components/ui/context-menu'

function SuppliesPage() {
	const { selectedWarehouse } = useWarehouseStore()
	const { shipments, deliveries, fetchSupplies, loading } = useSupplyStore()
	const { readyState } = useWarehouseSocket(selectedWarehouse?.id ?? '')
	useEffect(() => {
		if (selectedWarehouse?.id) {
			fetchSupplies(selectedWarehouse.id)
		}
	}, [selectedWarehouse?.id, fetchSupplies])

	return (
		<div className='flex bg-[#F4F4F5] min-h-screen'>
			<div className='flex flex-col flex-1 overflow-hidden ml-[60px]'>
				<header className='header-style'>
					<span className='pagename-font'>Поставки</span>
					<div className='flex items-center space-x-5'>
						<SelectWarehouse />
						{/* <AddWarehouseDialog /> */}
						<UserAvatar />
					</div>
				</header>

				<main className='flex-1 p-3 h-full'>
					<div className='grid grid-cols-12 gap-3 justify-between h-full'>
						<section className='bg-white rounded-[15px] col-span-6 h-full p-[10px]'>
							<h2 className='big-section-font mb-3'>Поступления</h2>
							{selectedWarehouse?.id ? (
								<div className='space-y-2 overflow-y-hidden max-h-[675px]'>
									{deliveries.map(d => (
										<ContextMenu key={d.id}>
											<ContextMenuTrigger asChild>
												<div
													/* onClick={() => onSelect(wh)}*/
													/* onContextMenu={() => onContextMenu?.(d)} */
													className='flex justify-between items-center bg-[#F2F3F4] rounded-[10px] max-h-[60px] px-[10px] py-[10px] cursor-pointer transition-all border-[2px]'
												>
													<div className='text-left space-y-0'>
														<span className='text-[20px] font-medium text-black'>
															{d.name}
														</span>
														<span className='text-[14px] font-normal text-black'>
															от: {d.supplier}
														</span>
													</div>
													<div className='text-right space-y-0'>
														<div className='text-[14px] font-normal text-[#5A606D]'>
															ожидаемая дата: {d.scheduled_at}
														</div>
														<div className='text-[14px] font-normal text-[#5A606D]'>
															количество товаров: {d.quantity}
														</div>
													</div>
												</div>
											</ContextMenuTrigger>

											<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
												<ContextMenuItem
													className='context-menu-delete'
													/* onClick={() => onDelete?.(wh)} */
												>
													Удалить
												</ContextMenuItem>
											</ContextMenuContent>
										</ContextMenu>
									))}
								</div>
							) : (
								<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
									выберите склад для отображения поступлений
								</div>
							)}
						</section>
						<section className='bg-white rounded-[15px] col-span-6 h-full p-[10px] space-y-5'>
							<h2 className='big-section-font'>Отгрузки</h2>
							{selectedWarehouse?.id ? (
								<div className='space-y-2 overflow-y-hidden max-h-[675px]'>
									{shipments.map(s => (
										<ContextMenu key={s.id}>
											<ContextMenuTrigger asChild>
												<div
													/* onClick={() => onSelect(wh)}*/
													/* onContextMenu={() => onContextMenu?.(d)} */
													className='flex justify-between items-center bg-[#F2F3F4] rounded-[10px] max-h-[60px] px-[10px] py-[10px] cursor-pointer transition-all border-[2px]'
												>
													<div className='text-left space-y-0'>
														<span className='text-[20px] font-medium text-black'>
															{s.name}
														</span>
														<span className='text-[14px] font-normal text-black'>
															кому: {s.customer}
														</span>
													</div>
													<div className='text-right space-y-0'>
														<div className='text-[14px] font-normal text-[#5A606D]'>
															ожидаемая дата: {s.scheduled_at}
														</div>
														<div className='text-[14px] font-normal text-[#5A606D]'>
															количество товаров: {s.quantity}
														</div>
													</div>
												</div>
											</ContextMenuTrigger>

											<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
												<ContextMenuItem
													className='context-menu-delete'
													/* onClick={() => onDelete?.(wh)} */
												>
													Удалить
												</ContextMenuItem>
											</ContextMenuContent>
										</ContextMenu>
									))}
								</div>
							) : (
								<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
									выберите склад для отображения отгрузок
								</div>
							)}
						</section>
					</div>
				</main>
			</div>
		</div>
	)
}

export default SuppliesPage
