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

export function SelectWarehouse(){
	const { warehouses, selectedWarehouse, setSelectedWarehouse, loading, error } = useWarehouseStore()
  const { resetData } = useSocketStore()
	const pathname = useLocation()
  return (
		<div className='relative'>
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
				<SelectTrigger className='select-warehouse'>
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
export default SelectWarehouse