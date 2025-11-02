import { motion } from 'framer-motion'
import { useSocketStore } from '@/store/useSocketStore'
import { Spinner } from '@/components/ui/spinner'
export function AvgBatteryCard() {
	const { avgBattery, loading, error } = useSocketStore()
	return (
		<div className='dashboard-card !h-full'>
      {loading?(
        <div className='spinner-load-container dashboard-card-load-font'>
          <Spinner className='size-4 m-1' /> считаем заряд
          батарей...
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
          <h3 className='dashboard-section-font'>
            Ср. заряд батарей
          </h3>
          <div className='flex flex-col items-center justify-center space-y-[-8px] '>
            <span className='dashboard-card-data'>
              {avgBattery?.avg_battery.toFixed(2)}%
            </span>
            <p className='text-[10px] text-[#CCCCCC] font-light'>
              среднее значение
            </p>
          </div>
        </motion.div>
      )}
    </div>
	)
}
export default AvgBatteryCard
