import { motion } from 'framer-motion'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'
export function CriticalUnique() {
	const { criticalUnique, loading, error } = useSocketStore()
	return (
		<div className='dashboard-card'>
			{loading ?(
				<div className='spinner-load-container dashboard-card-load-font'>
					<Spinner className='size-5 m-1' /> ищем критические остатки...
				</div>
			):error?(
				<div className='spinner-load-container dashboard-card-load-font'>
					{error}
				</div>
			):(
				<motion.div
					initial={{ opacity: 0, y: 20 }}
					animate={{ opacity: 1, y: 0 }}
				>
					<h3 className='dashboard-section-font'>Критические остатки</h3>
					<div className='flex flex-col items-center justify-between space-y-[-8px] pb-4'>
						<span className='dashboard-card-data'>
							{criticalUnique?.unique_articles}
						</span>
						<p className='text-[10px] text-[#CCCCCC] font-light'>
							количество SKU
						</p>
					</div>
				</motion.div>
			)}
		</div>
	)
}
export default CriticalUnique
