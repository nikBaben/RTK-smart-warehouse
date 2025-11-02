import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogClose,
} from '@/components/ui/dialog'
import {
	ResponsiveContainer,
	LineChart,
	Line,
	XAxis,
	YAxis,
	CartesianGrid,
	Tooltip,
	Legend,
} from 'recharts'
import { motion } from 'framer-motion'

export function TrendGraph({
	data,
	onClose,
}: {
	data: any[]
	onClose: () => void
}) {
	// если данных нет — сообщение-заглушка
	if (!data || data.length === 0) {
		return (
			<Dialog open onOpenChange={onClose}>
				<DialogContent className='w-[400px] p-[20px] text-center'>
					<DialogHeader>
						<DialogTitle>Нет данных для построения графика</DialogTitle>
					</DialogHeader>
					<DialogClose />
				</DialogContent>
			</Dialog>
		)
	}

	// --- 1. фильтруем ключи, чтобы не включать 'date'
	const productKeys = Object.keys(data[0] || {}).filter(key => key !== 'date')

	// --- 2. вычисляем уникальные дни (по UTC, чтобы не смещало)
	const uniqueDays = new Set(
		data
			.map(item => {
				if (!item.date) return ''
				const d = new Date(item.date)
				return isNaN(d.getTime()) ? '' : d.toISOString().split('T')[0] // YYYY-MM-DD (UTC)
			})
			.filter(Boolean)
	)
	const isSingleDay = uniqueDays.size === 1

	// --- 3. форматируем дату/время для оси X
	const formattedData = data.map(item => {
		const dateObj = new Date(item.date)
		if (isNaN(dateObj.getTime())) return { ...item, displayX: '?' }

		return {
			...item,
			displayX: isSingleDay
				? dateObj.toLocaleTimeString('ru-RU', {
						hour: '2-digit',
						minute: '2-digit',
						timeZone: 'Europe/Moscow', // 👈 фикс смещения
				  })
				: dateObj.toLocaleDateString('ru-RU', {
						day: '2-digit',
						month: '2-digit',
						year: '2-digit',
				  }),
		}
	})

	const colors = ['#7700FF', '#FF5733', '#3F7BFF', '#0ACB5B', '#FDA610']

	return (
		<Dialog open onOpenChange={onClose}>
			<DialogContent className='!w-[700px] h-[270px] max-w-none py-0 top-[35%] bg-white z-[500] rounded-[15px] p-0 gap-0 flex flex-col items-center justify-center'>
				<DialogHeader className='w-full px-[20px]'>
					<DialogTitle className='text-[20px] font-medium text-black text-left'>
						График тренда остатков
					</DialogTitle>
				</DialogHeader>

				<div className='flex w-[657px] h-[210px] items-center'>
					<ResponsiveContainer width='100%' height='100%'>
						<LineChart
							data={formattedData}
							margin={{ top: 0, right: 25, left: -30, bottom: 0 }}
						>
							<CartesianGrid stroke='#CCCCCC' />

							<XAxis
								dataKey='displayX'
								tick={{ fontSize: 10, fill: '#000' }}
								label={{
									value: isSingleDay ? 'время' : 'дата',
									position: 'insideRight',
									dy: 6,
									dx: 16.5,
									style: { fontSize: 10, fill: '#000' },
								}}
								axisLine={false}
								tickLine={false}
							/>

							<YAxis
								tick={{ fontSize: 10, fill: '#000' }}
								label={{
									value: 'единиц, товар, шт',
									angle: 0,
									position: 'top',
									dx: 70,
									style: { textAnchor: 'middle', fontSize: 10, fill: '#000' },
								}}
								axisLine={false}
								tickLine={false}
							/>

							<Tooltip
								formatter={value => [`${value} шт`]}
								labelFormatter={label =>
									isSingleDay ? `Время: ${label}` : `Дата: ${label}`
								}
							/>

							<Legend
								verticalAlign='top'
								align='right'
								height={13}
								wrapperStyle={{ fontSize: 10 }}
								formatter={(value: string) => (
									<span style={{ color: '#000' }}>{value}</span>
								)}
							/>

							<motion.g initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
								{productKeys.map((key, index) => (
									<Line
										key={key}
										type='linear'
										dataKey={key}
										name={key}
										stroke={colors[index % colors.length]}
										strokeWidth={2}
										dot={{ r: 0 }}
									/>
								))}
							</motion.g>
						</LineChart>
					</ResponsiveContainer>
				</div>

				<DialogClose />
			</DialogContent>
		</Dialog>
	)
}
