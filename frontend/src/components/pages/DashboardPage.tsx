import { useEffect} from "react";
import { motion } from 'framer-motion';
import { ScanStoryTable } from "../widgets/ScanStoryTable";
import { RobotActivityChart } from "@/components/widgets/RobotActivityChart";
import { ForecastAI } from "../widgets/ForecastAI";
import { UserAvatar } from '../ui/UserAvatar';
import { AddRobotProductDialog } from '../ui/AddRobotProductDialog';
import { Spinner } from '@/components/ui/spinner';
import { useWarehouseSocket } from '@/hooks/useWarehouseSocket';
import { useSocketStore } from '@/store/useSocketStore';
import { useWarehouseStore } from '@/store/useWarehouseStore';
import { WarehouseMap } from '../widgets/WarehouseMap';
import SelectWarehouse from "../ui/SelectWarehouse";

function DashboardPage(){
	const token = localStorage.getItem('token')
	const { warehouses, selectedWarehouse } = useWarehouseStore()
	const {
		avgBattery,
		robotsData,
		scanned24h,
		criticalUnique,
		statusAvg,
	} = useSocketStore()
	const { readyState } = useWarehouseSocket(selectedWarehouse?.id ?? '')
	
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

	const { fetchWarehouses } = useWarehouseStore()
/* 	useEffect(()=>{
		if (token) fetchWarehouses(token)
	},[token]) */
	useEffect(() => {
		fetchWarehouses()
	}, [])
  return (
		<div className='flex bg-[#F4F4F5] min-h-screen'>
			<div className='flex flex-col flex-1 overflow-hidden ml-[60px]'>
				<header className='header-style'>
					<span className='pagename-font'>Дашборд</span>
					<div className='ml-auto flex items-center gap-4'>
						<SelectWarehouse />
						<div className='flex items-center space-x-5'>
							{selectedWarehouse?.id ? <AddRobotProductDialog /> : <></>}
							<UserAvatar />
						</div>
					</div>
				</header>
				<main className='flex-1 overflow-auto p-[9px]'>
					{selectedWarehouse?.id == null ? (
						<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[40px]'>
							<h1>выберите склад для отображения дашборда</h1>
						</div>
					) : (
						<div className='grid grid-cols-12 gap-3 h-full'>
							<section className='bg-white rounded-[15px] p-[10px] flex flex-col col-span-5'>
								<h2 className='dashboard-section-font'>Карта склада</h2>
								<div className='flex-1 bg-transparent rounded-[10px] w-full'>
									<div className='flex w-full text-[14px] justify-left items-center pb-1 gap-6'>
										<div className='flex items-center gap-2'>
											<div className='h-2 w-6 rounded-[100px] bg-[#FFD6D6]' />
											<p>разгрузка</p>
										</div>
										<div className='flex items-center gap-2'>
											<div className='h-2 w-6 rounded-[100px] bg-[#D6FFD6]' />
											<p>хранение</p>
										</div>
										<div className='flex items-center gap-2'>
											<div className='h-2 w-6 rounded-[100px] bg-[#D6E0FF]' />
											<p>погрузка</p>
										</div>
									</div>
									<WarehouseMap />
								</div>
							</section>
							<section className='col-span-7 auto-rows-min space-y-[10px]'>
								<div className='bg-transparent grid grid-cols-7 gap-3 col-span-2 w-full'>
									<div className='dashboard-card'>
										{criticalUnique?.unique_articles !== undefined ? (
											<motion.div
												initial={{ opacity: 0, y: 20 }}
												animate={{ opacity: 1, y: 0 }}
											>
												<h3 className='dashboard-section-font'>
													Критические остатки
												</h3>
												<div className='flex flex-col items-center justify-between space-y-[-8px] pb-4'>
													<p className='text-[28px] font-bold'>
														{criticalUnique?.unique_articles}
													</p>
													<p className='text-[10px] text-[#CCCCCC] font-light'>
														количество SKU
													</p>
												</div>
											</motion.div>
										) : (
											<div className='spinner-load-container dashboard-card-load-font'>
												<Spinner className='size-5 m-1' /> ищем критические
												остатки...
											</div>
										)}
									</div>
									<div className='dashboard-card'>
										{scanned24h?.count !== undefined ? (
											<motion.div
												initial={{ opacity: 0, y: 20 }}
												animate={{ opacity: 1, y: 0 }}
											>
												<h3 className='dashboard-section-font'>
													Проверено за 24ч
												</h3>
												<div className='flex flex-col items-center justify-between space-y-[-8px] pb-4'>
													<p className='text-[28px] font-bold'>
														{scanned24h?.count}
													</p>
													<p className='text-[10px] text-[#CCCCCC] font-light'>
														{' '}
														позиций{' '}
													</p>
												</div>
											</motion.div>
										) : (
											<div className='spinner-load-container dashboard-card-load-font'>
												<Spinner className='size-4 m-1' /> собираем
												статистику...
											</div>
										)}
									</div>
									<div className='dashboard-card !col-span-3'>
										{statusAvg?.status !== undefined ? (
											<motion.div
												initial={{ opacity: 0, y: 20 }}
												animate={{ opacity: 1, y: 0 }}
											>
												<h3 className='dashboard-section-font'>
													Ср. статус по складу
												</h3>
												<div className='flex flex-col items-center justify-between space-y-[-8px] pb-4'>
													<p className='text-[28px] font-bold'>
														{getStatusName(statusAvg?.status || '')}
													</p>
													<p className='text-[10px] text-[#CCCCCC] font-light'>
														статистика
													</p>
												</div>
											</motion.div>
										) : (
											<div className='spinner-load-container dashboard-card-load-font'>
												<Spinner className='size-4 m-1' /> определяем ср. статус
												склада...
											</div>
										)}
									</div>
								</div>
								<div className='bg-transparent grid grid-cols-7 gap-3 col-span-2 w-full h-[200px]'>
									<RobotActivityChart />
									<div className='flex flex-col col-span-2 gap-3'>
										<div className='dashboard-card !h-full'>
											{robotsData?.robots !== undefined ? (
												<motion.div
													initial={{ opacity: 0, y: 20 }}
													animate={{ opacity: 1, y: 0 }}
												>
													<h3 className='dashboard-section-font mb-0'>
														Роботы
													</h3>
													<div className='flex flex-col items-center justify-center space-y-[-8px]'>
														<span className='text-[30px] font-bold'>
															{robotsData?.active_robots}/{robotsData?.robots}
														</span>
														<p className='text-[10px] text-[#CCCCCC] font-light'>
															активных/всего
														</p>
													</div>
												</motion.div>
											) : (
												<div className='spinner-load-container dashboard-card-load-font'>
													<Spinner className='size-4 m-1' /> загружаем
													роботов...
												</div>
											)}
										</div>
										<div className='dashboard-card !h-full'>
											{avgBattery?.avg_battery ? (
												<motion.div
													initial={{ opacity: 0, y: 20 }}
													animate={{ opacity: 1, y: 0 }}
												>
													<h3 className='dashboard-section-font'>
														Ср. заряд батарей
													</h3>
													<div className='flex flex-col items-center justify-center space-y-[-8px] '>
														<span className='text-[30px] font-bold'>
															{avgBattery?.avg_battery.toFixed(2)}%
														</span>
														<p className='text-[10px] text-[#CCCCCC] font-light'>
															среднее значение
														</p>
													</div>
												</motion.div>
											) : (
												<div className='spinner-load-container dashboard-card-load-font'>
													<Spinner className='size-4 m-1' /> считаем заряд
													батарей...
												</div>
											)}
										</div>
									</div>
								</div>
								<div className='scroll-padding bg-white rounded-[15px] pl-[10px] pt-[6px] pr-[10px] col-span-2 h-[239px]'>
									<h3 className='dashboard-widget-font'>
										Последние сканирования
									</h3>
									<ScanStoryTable />
								</div>
								<div className='bg-white rounded-[15px] pl-[10px] pt-[6px] pr-[10px] pb-[10px] col-span-2'>
									<ForecastAI />
								</div>
							</section>
						</div>
					)}
				</main>
			</div>
		</div>
	)
};

export default DashboardPage;
