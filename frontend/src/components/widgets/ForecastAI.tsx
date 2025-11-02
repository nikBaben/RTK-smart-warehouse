import React from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "../ui/button";
import Refresh from '@atomaro/icons/24/action/Refresh';
import type { useWarehouseSocket } from "@/hooks/useWarehouseSocket";
import { useSocketStore } from '@/store/useSocketStore'

interface ForecastItem {
  name: string;
  remaining: number;
  depletionDate: string;
  recommendation: string;
  confidence: number;
}

const forecastData: ForecastItem[] = [
  {
    name: "Apple IPhone 17 Pro Max",
    remaining: 10,
    depletionDate: "18.10.2025",
    recommendation: "150 шт",
    confidence: 88,
  },
  {
    name: "Фигурка коллекционная",
    remaining: 24,
    depletionDate: "20.10.2025",
    recommendation: "80 шт",
    confidence: 94,
  },
  {
    name: "Монитор XXXXXXXXX",
    remaining: 16,
    depletionDate: "21.10.2025",
    recommendation: "50 шт",
    confidence: 81,
  },
  {
    name: "Ящик деревянный",
    remaining: 60,
    depletionDate: "20.10.2025",
    recommendation: "400 шт",
    confidence: 97,
  },
  {
    name: "Телевизор Samsung",
    remaining: 31,
    depletionDate: "19.10.2025",
    recommendation: "100 шт",
    confidence: 86,
  },
];

export function ForecastAI() {

  const { connectionState } = useSocketStore()
  const getConnectionColor = (connectionState:number) => {
    switch (connectionState){
      case 0: return '#FDA610'
      case 1: return '#0ACB5B'
      case 2: return '#FF2626'
      case 3: return '#FF2626'
      default: '#9699A3'
    }
  }

  return (
		<div className='bg-white rounded-[15px]'>
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

			<div className='flex flex-col gap-2'>
				{forecastData.map((item, index) => (
					<div
						key={index}
						className='flex items-center justify-between bg-[#F6F7F7] rounded-[10px] px-3 py-3 h-[54px]'
					>
						<div className='flex flex-col min-w-[230px]'>
							<span className='font-medium text-[14px] text-black truncate'>
								{item.name}
							</span>
							<span className='text-[12px] text-black'>
								осталось {item.remaining} шт
							</span>
						</div>
						<div className='flex flex-col text-[12px] text-[#000000] min-w-[230px]'>
							<span>
								запас будет исчерпан{' '}
								<span className='font-medium'>{item.depletionDate}</span>
							</span>
							<span>
								рекомендуется заказать{' '}
								<span className='font-light'>{item.recommendation}</span>
							</span>
						</div>
						<div className='flex items-center gap-2 min-w-[180px] justify-end text-[12px] text-[#000000]'>
							<span>
								достоверность прогноза –{' '}
								<span className='font-medium'>{item.confidence}%</span>
							</span>
							<Button className='p-1 rounded-[5px] bg-[#DEDFE1] hover:bg-gray-200 transition h-[25px] w-[25px]'>
								<Refresh className='w-auto h-[12.5px] text-[#000000]' />
							</Button>
						</div>
					</div>
				))}
			</div>
		</div>
	)
};
export default ForecastAI