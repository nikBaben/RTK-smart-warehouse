import api from '@/api/axios'
import { toast } from 'sonner'
import { UserAvatar } from '../ui/UserAvatar'
import SelectWarehouse from '../ui/SelectWarehouse'
import { useWarehouseSocket } from '@/hooks/useWarehouseSocket'
import { useWarehouseStore } from '@/store/useWarehouseStore'
import { useSupplyStore } from '@/store/useSupplyStore'
import { useEffect } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import Upload from '@atomaro/icons/24/action/Upload'

import {
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuTrigger,
} from '@/components/ui/context-menu'
import type { Delivery } from '../types/delivery'
import type { Shipment } from '../types/shipment'

function SuppliesPage() {
	const { selectedWarehouse } = useWarehouseStore()
	const {
		shipments,
		deliveries,
		fetchSupplies,
		exportMonthlyReport,
		loading,
		error,
	} = useSupplyStore()
	useEffect(() => {
		if (selectedWarehouse?.id) {
			fetchSupplies(selectedWarehouse.id)
		}
	}, [selectedWarehouse?.id, fetchSupplies])

	const { fetchWarehouses } = useWarehouseStore()
	/* 	useEffect(()=>{
	if (token) fetchWarehouses(token)
	}[token]) */
	useEffect(() => {
		fetchWarehouses()
	}, [])

	const handleDeleteDelivery = async (delivery: Delivery) => {
		if (
			!confirm(
				`Вы действительно хотите удалить поступление "${delivery.name}"? Данное действие невозможно отменить`
			)
		)
			return
		try{
			await api.delete(`deliveries/${delivery.id}`)
			toast.success(`Поставка "${delivery.name}" успешно удалена`)
			if (selectedWarehouse?.id) {
				await fetchSupplies(selectedWarehouse.id)
			}
			else console.error('Ошибка: склад не выбран')
		} catch (err){
			console.error(err)
			toast.error(`Не удалось удалить поставку "${delivery.name}"`)
		}	
	}

	const handleDeleteShipment = async (shipment: Shipment) => {
		if (
			!confirm(
				`Вы действительно хотите удалить отгрузку "${shipment.name}"? Данное действие невозможно отменить`
			)
		)
			return
		try {
			await api.delete(`shipments/${shipment.id}`)
			toast.success(`Отгрузка "${shipment.name}" успешно удалена`)
			if (selectedWarehouse?.id) {
				await fetchSupplies(selectedWarehouse.id)
			} else console.error('Ошибка: склад не выбран')
		} catch (err) {
			console.error(err)
			toast.error(`Не удалось удалить отгрузку "${shipment.name}"`)
		}
	}

	return (
		<div className='flex bg-[#F4F4F5] h-screen'>
			<div className='flex flex-col flex-1 ml-[60px]'>
				<header className='header-style'>
					<span className='pagename-font'>Поставки</span>
					<div className='flex items-center space-x-5'>
						<SelectWarehouse />
						<UserAvatar />
					</div>
				</header>

				<main className='flex-1 p-3 h-full'>
					<div className='h-full space-y-3'>
						<div className='grid grid-cols-12 gap-3 justify-between h-[94%]'>
							<section className='bg-white rounded-[15px] col-span-6 h-full p-[10px]'>
								<h2 className='big-section-font mb-3'>Поступления</h2>
								{loading ? (
									<div className='space-y-2'>
										{[...Array(12)].map((_, i) => (
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
								) : error ? (
									<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
										ошибка при загрузке поступлений: {error}
									</div>
								) : selectedWarehouse?.id ? (
									<div className='space-y-2 overflow-y-hidden max-h-[675px]'>
										{deliveries.map(d => (
											<ContextMenu key={d.id}>
												<ContextMenuTrigger asChild>
													<div
														/* onClick={() => onSelect(wh)}*/
														/* onContextMenu={() => onContextMenu?.(d)} */
														className='big-list-item-container hover:border-[#7700FF33]'
													>
														<div className='text-left space-y-0'>
															<div className='text-[18px] font-medium text-black'>
																{d.name}
															</div>
															<div className='text-[14px] font-light text-black'>
																от:{' '}
																{d.supplier === null
																	? 'нет данных'
																	: d.supplier}
															</div>
														</div>
														<div className='text-right space-y-0'>
															<div className='text-[14px] font-light text-[#5A606D]'>
																ожидаемая дата: {d.scheduled_at}
															</div>
															<div className='text-[14px] font-light text-[#5A606D]'>
																количество товаров: {d.quantity}
															</div>
														</div>
													</div>
												</ContextMenuTrigger>

												<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
													<ContextMenuItem
														className='context-menu-delete'
														onClick={() => handleDeleteDelivery(d)}
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
								{loading ? (
									<div className='space-y-2'>
										{[...Array(12)].map((_, i) => (
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
								) : error ? (
									<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
										ошибка при загрузке поступлений: {error}
									</div>
								) : selectedWarehouse?.id ? (
									<div className='space-y-2 overflow-y-hidden max-h-[675px]'>
										{shipments.map(s => (
											<ContextMenu key={s.id}>
												<ContextMenuTrigger asChild>
													<div
														/* onClick={() => onSelect(wh)}*/
														/* onContextMenu={() => onContextMenu?.(d)} */
														className='big-list-item-container hover:border-[#7700FF33]'
													>
														<div className='text-left space-y-0'>
															<div className='text-[18px] font-medium text-black'>
																{s.name}
															</div>
															<div className='text-[14px] font-light text-black'>
																кому:{' '}
																{s.customer === null
																	? 'нет данных'
																	: s.customer}
															</div>
														</div>
														<div className='text-right space-y-0'>
															<div className='text-[14px] font-light text-[#5A606D]'>
																ожидаемая дата: {s.scheduled_at}
															</div>
															<div className='text-[14px] font-light text-[#5A606D]'>
																количество товаров: {s.quantity}
															</div>
														</div>
													</div>
												</ContextMenuTrigger>

												<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
													<ContextMenuItem
														className='context-menu-delete'
														onClick={() => handleDeleteShipment(s)}
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
						</div>
						<div className='flex justify-end'>
							<Button
								onClick={() => exportMonthlyReport()}
								className='supplies-export-excel ml-auto'
							>
								<Upload fill='#7700FF' className='h-[8px] w-[8px]' />
								Экспорт в Excel
							</Button>
						</div>
					</div>
				</main>
			</div>
		</div>
	)
}

export default SuppliesPage
