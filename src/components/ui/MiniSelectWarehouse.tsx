import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useWarehouseStore } from '@/store/useWarehouseStore'
import { useSocketStore } from '@/store/useSocketStore'
import { useLocation } from 'react-router-dom'

export function MiniSelectWarehouse(){
	const { warehouses, selectedWarehouse, setSelectedWarehouse, loading, error } = useWarehouseStore()
  const { resetData } = useSocketStore()
	const pathname = useLocation()
  return (
		<div className='relative mb-0'>
			<Select
				value={selectedWarehouse?.id || ''}
				onValueChange={id => {
					const wh = warehouses.find(w => w.id === id) || null
					setSelectedWarehouse(wh)
  				//проверяем, что мы находимся на дашборде
					if (window.location.pathname === '/') {
						resetData()
					}
				}}
			>
				<SelectTrigger className='w-auto !h-[31px] cursor-pointer 
                                        border-[#CCCCCC] border-[2px] rounded-[10px] text-[20px] text-black
                                        flex items-center justify-between 
                                        bg-white min-w-[220px]
                                        transition-all duration-200 ease-in-out
                                        enabled:hover:shadow-[0_0_15px_rgba(119,0,255,0.2)]
                                        enabled:hover:border-[#7700FF]'>
					<SelectValue placeholder='Выберите склад' />
				</SelectTrigger>
				<SelectContent>
					{loading ? (
						<div className='spinner-load-container'>
							<Spinner className='size-5 m-1' /> загрузка складов...
						</div>
					) : error ? (
						<div className='flex items-center justify-center text-[20px] text-[#FF9393]'>
							не удалось загрузить
						</div>
					) : warehouses.length === 0 ? (
						<div className='flex items-center justify-center text-[20px] text-[#FED388]'>
							нет доступных складов
						</div>
					) : (
						warehouses.map(w => (
							<SelectItem key={w.id} value={w.id.toString()}>
								{w.name}
							</SelectItem>
						))
					)}
				</SelectContent>
			</Select>
		</div>
	)
}
export default MiniSelectWarehouse