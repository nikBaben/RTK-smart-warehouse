import { motion } from 'framer-motion'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'
export function RobotsDataCard() {
	const { robotsData, robotsLoading, } = useSocketStore()
	return (
		<div className='dashboard-card !h-full'>
			{robotsLoading || robotsData?.robots === undefined ? (
				<div className='spinner-load-container dashboard-card-load-font'>
					<Spinner className='size-5 m-1' /> загружаем роботов...
				</div>
			) : (
				<motion.div
					initial={{ opacity: 0 }}
					animate={{ opacity: 1, y: 0 }}
				>
					<h3 className='dashboard-section-font mb-0'>Роботы</h3>
					<div className='flex flex-col items-center justify-center space-y-[-8px]'>
						<span className='dashboard-card-data'>
							{robotsData?.active_robots}/{robotsData?.robots}
						</span>
						<p className='text-[10px] text-[#CCCCCC] font-light'>
							активных/всего
						</p>
					</div>
				</motion.div>
			)}
		</div>
	)
}
export default RobotsDataCard
