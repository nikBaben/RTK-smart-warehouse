import { useEffect} from "react";
import { ScanStoryTable } from '../widgets/warehouse/ScanStoryTable';
import { RobotActivityChart } from "@/components/widgets/warehouse/RobotActivityChart";
import { SoonDepletedList } from "../widgets/SoonDepletedList";
import { UserAvatar } from '../ui/UserAvatar';
import { AddRobotProductDialog } from '../ui/AddRobotProductDialog';
import { useWarehouseSocket } from '@/hooks/useWarehouseSocket';
import { useWarehouseStore } from '@/store/useWarehouseStore';
import { WarehouseMap } from '../widgets/warehouse/WarehouseMap';
import SelectWarehouse from "../ui/SelectWarehouse";
import { StatusAvgCard } from '../widgets/warehouse/StatusAvgCard';
import { CriticalUnique } from '../widgets/warehouse/CriticalUnique';
import { Scanned24hCard } from '../widgets/warehouse/Scanned24hCard';
import { RobotsDataCard } from '../widgets/warehouse/RobotsDataCard'
import AvgBatteryCard from "../widgets/warehouse/AvgBatteryCard";

function DashboardPage(){
	const token = localStorage.getItem('token') || sessionStorage.getItem('token')
	const { warehouses, selectedWarehouse } = useWarehouseStore()
	const { readyState } = useWarehouseSocket(selectedWarehouse?.id ?? '')

	const { fetchWarehouses } = useWarehouseStore()
/* 	useEffect(()=>{
		if (token) fetchWarehouses(token)
	},[token]) */
	useEffect(() => {
		fetchWarehouses()
	}, [])
  return (
		<div className='flex bg-[#F4F4F5] h-screen'>
			<div className='flex flex-col flex-1 ml-[60px]'>
				<header className='header-style shrink-0'>
					<span className='pagename-font'>Дашборд</span>
					<div className='ml-auto flex items-center gap-4'>
						<SelectWarehouse />
						<div className='flex items-center space-x-5'>
							{selectedWarehouse?.id ? <AddRobotProductDialog /> : <></>}
							<UserAvatar />
						</div>
					</div>
				</header>
				<main className='flex-1 p-[9px]'>
					{selectedWarehouse?.id == null ? (
						<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[40px]'>
							<h1>выберите склад для отображения дашборда</h1>
						</div>
					) : (
						<div className='grid grid-cols-12 gap-3 h-full'>
							<section className='bg-white rounded-[15px] p-[10px] flex flex-col col-span-5'>
								<h2 className='dashboard-widget-font'>Карта склада</h2>
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
									<CriticalUnique />
									<Scanned24hCard />
									<StatusAvgCard />
								</div>
								<div className='bg-transparent grid grid-cols-7 gap-3 col-span-2 w-full h-[200px]'>
									<RobotActivityChart />
									<div className='flex flex-col col-span-2 gap-3'>
										<RobotsDataCard />
										<AvgBatteryCard />
									</div>
								</div>
								<div className='scroll-padding bg-white rounded-[15px] pl-[10px] pt-[6px] pr-[10px] col-span-2 h-[239px]'>
									<h3 className='dashboard-widget-font'>
										Последние сканирования
									</h3>
									<ScanStoryTable />
								</div>
								<div className='bg-white rounded-[15px] pl-[10px] pt-[6px] pr-[10px] pb-[10px] col-span-2'>
									<SoonDepletedList warehouse_id={selectedWarehouse.id} />
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
