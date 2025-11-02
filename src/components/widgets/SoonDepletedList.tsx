import { useEffect } from "react";
import { Button } from "../ui/button";
import Refresh from '@atomaro/icons/24/action/Refresh';
import { useDepletionStore } from '@/store/useDepletionStore'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'

type Props = {
	warehouse_id: string
}

export function SoonDepletedList(props: Props) {
	const warehouse_id = props.warehouse_id
	const { items, loading, error, fetchSoonDepleted, recalcDepletion } = useDepletionStore()
	const { connectionState } = useSocketStore()


	useEffect(()=>{
		fetchSoonDepleted(warehouse_id)
	},[warehouse_id])

	const getConnectionColor = (connectionState: number) => {
		switch (connectionState) {
			case 0:
				return '#FDA610'
			case 1:
				return '#0ACB5B'
			case 2:
				return '#FF6200'
			case 3:
				return '#FF2626'
			default:
				'#9699A3'
		}
	}

	return (
		<div className='bg-white rounded-[15px] h-[334px]'>
			<div className='flex items-center justify-between'>
				<h3 className='dashboard-widget-font'>
					Прогноз ИИ на следующие 7 дней
				</h3>
				<svg width='20' height='20' viewBox='0 0 40 40'>
					<circle
						cx='20'
						cy='20'
						r='14'
						fill='none'
						stroke={getConnectionColor(connectionState)}
						strokeWidth='4'
					/>
				</svg>
			</div>
			{loading ? (
				<div className='spinner-load-container'>
					<Spinner className='size-5 m-1' /> загружаем прогнозы...
				</div>
			) : error ? (
				<div className='spinner-load-container'>
					<p>{error}</p>
				</div>
			) : items.length === 0 ? (
				<div className='spinner-load-container'>
					<p>в ближайшие 7 дней товаров с критическим остатком не ожидается</p>
				</div>
			) : (
				<div className='flex flex-col gap-2'>
					{items.map(item => (
						<div
							key={item.product_id}
							className='flex items-center grid grid-cols-12 justify-between bg-[#F6F7F7] rounded-[10px] px-3 h-[54px]'
						>
							<div className='flex flex-col col-span-5'>
								<span className='font-medium text-[14px] text-black truncate'>
									{item.product_name}
								</span>
								<span className='text-[12px] text-black'>
									осталось {item.stock} шт
								</span>
							</div>
							<div className='flex flex-col col-span-4 text-[12px] text-[#000000]'>
								<span className='font-medium'>
									запас будет исчерпан{' '}
									<span>
										{new Date(item.depletion_at).toLocaleDateString('ru-RU')}
									</span>
								</span>
								<span className='font-light'>
									рекомендуется заказать{' '}
									<span className='font-light'>
										{item.required_delivery} шт
									</span>
								</span>
							</div>
							<div className='flex items-center col-span-3 gap-2 justify-end text-[12px] text-[#000000]'>
								<span>
									достоверность прогноза –{' '}
									<span className='font-medium'>{item.reliability * 100}%</span>
								</span>
								<Button
									onClick={() => recalcDepletion(item.product_id, warehouse_id)}
									className='refresh-button'
								>
									<Refresh className='w-auto h-[12.5px] text-[#000000]' />
								</Button>
							</div>
						</div>
					))}
				</div>
			)}
		</div>
	)
};
export default SoonDepletedList