import { motion } from 'framer-motion'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'
export function Scanned24hCard() {
	const { scanned24h, scanned24hLoading } = useSocketStore()
	return (
		<div className='dashboard-card'>
			{scanned24hLoading ? (
				<div className='spinner-load-container dashboard-card-load-font'>
					<Spinner className='size-4 m-1' /> собираем статистику...
				</div>
			) : (
				<motion.div
					initial={{ opacity: 0 }}
					animate={{ opacity: 1, y: 0 }}
				>
					<h3 className='dashboard-section-font'>Проверено за 24ч</h3>
					<div className='flex flex-col items-center justify-between space-y-[-8px] pb-4'>
						<p className='dashboard-card-data'>{scanned24h?.count}</p>
						<p className='text-[10px] text-[#CCCCCC] font-light'> позиций </p>
					</div>
				</motion.div>
			)}
		</div>
	)
}
export default Scanned24hCard
