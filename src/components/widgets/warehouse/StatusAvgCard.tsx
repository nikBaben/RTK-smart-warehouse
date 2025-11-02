import { motion } from 'framer-motion'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'

export function StatusAvgCard(){
  const { statusAvg, loading, error } = useSocketStore()
  const getStatusName = (status: string) => {
		switch (status) {
			case 'ok':
				return 'ОК'
			case 'low':
				return 'низкий остаток'
			case 'critical':
				return 'критично'
			default:
				return 'неизвестен'
		}
	}
  return (
		<div className='dashboard-card !col-span-3'>
			{loading ? (
				<div className='spinner-load-container dashboard-card-load-font'>
					<Spinner className='size-4 m-1' /> определяем ср. статус склада...
				</div>
			) : error ? (
				<div className='spinner-load-container dashboard-card-load-font'>
					{error}
				</div>
			) : statusAvg?.status !== undefined ? (
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
				>
					<h3 className='dashboard-section-font'>Ср. статус по складу</h3>
					<div className='flex flex-col items-center justify-between space-y-[-8px] pb-4'>
						<span className='dashboard-avg-status-data'>
							{getStatusName(statusAvg?.status)}
						</span>
						<p className='text-[10px] text-[#CCCCCC] font-light'>статистика</p>
					</div>
				</motion.div>
			) : (
				<div className='spinner-load-container dashboard-card-load-font'>
					не удалось получить ср. статус
				</div>
			)}
		</div>
	)
}
export default StatusAvgCard