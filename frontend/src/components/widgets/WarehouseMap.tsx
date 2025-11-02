'use client'
import { motion } from 'framer-motion'
import { useSocketStore } from '@/store/useSocketStore'
import { useEffect, useRef, useState } from 'react'
import AddLarge from '@atomaro/icons/24/action/AddLarge'
import RemoveLarge from '@atomaro/icons/24/action/RemoveLarge'
import Aim from '@atomaro/icons/24/communication/Aim'
import { ButtonGroup } from '@/components/ui/button-group'
import {
  TooltipProvider,
	Tooltip,
	TooltipContent,
	TooltipTrigger,
} from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'

const GRID_X = 26 // A–Z
const GRID_Y = 50

export function WarehouseMap() {
	const { robotPositions, productSnapshot } = useSocketStore()
	const robots = robotPositions?.robots ?? []
	const products = productSnapshot?.items ?? []

	const containerRef = useRef<HTMLDivElement>(null)
  
	//добавляем состояние для масштабирования и перемещения со значением по умолчанию
	const [transform, setTransform] = useState({
		x: 0,
		y: 0,
		scale: 1,
	})

	//-----ПАНОРАМИРОВАНИЕ МЫШЬЮ-----
	const [ isDragging, setDragging ] = useState(false)
  const lastPos = useRef({ x: 0, y: 0 })

  const handleMouseDown = (e: React.MouseEvent) => {
  	setDragging(true)
  	lastPos.current = { x: e.clientX, y: e.clientY }
  }

  const handleMouseUp = () => (setDragging(false))

  const handleMouseMove = (e: React.MouseEvent) => {
  	if (!isDragging) return
  	const dx = e.clientX - lastPos.current.x
  	const dy = e.clientY - lastPos.current.y
  	lastPos.current = { x: e.clientX, y: e.clientY }

  	setTransform(t => ({
  		...t,
  		x: t.x + dx,
  		y: t.y + dy,
  	}))
  }



	function getMinutesAgo(created_at: string) {
		const createdAt = new Date(created_at)
		const now = new Date()
		if (created_at==null){
			return 0;
		}
		else return Math.floor((now.getTime() - createdAt.getTime()) / 60000)
	}

  //функции зума с учетом реализацией ограничений масштаба
	const zoomIn = () => setTransform(t => ({ ...t, scale: Math.min(t.scale * 1.1,3)}))
  const zoomOut = () => setTransform(t => ({...t, scale: Math.max(t.scale / 1.1,0.9)}))
  
  //функция центрирования карты
  const centerMap = () => setTransform(t=> ({...t, x:0,y:0}))

	const [size, setSize] = useState({ width: 1000, height: 600 })

	const getRobotStatusStyles = (status: string) => {
		switch (status) {
			case 'idle':
				return {
					circle: 'fill-[#3BD57C] stroke-[#078E40]',
					tooltip: 'bg-[#3BD57C] border-[#078E40]',
				}
			case 'scanning':
				return {
					circle: 'fill-[#4C87FF] stroke-[#164AB3]',
					tooltip: 'bg-[#4C87FF] border-[#164AB3]',
				}
			case 'charging':
				return {
					circle: 'fill-[#FDB840] stroke-[#B1740B]',
					tooltip: 'bg-[#FDB840] border-[#B1740B]',
				}
			default:
				return {
					circle: 'fill-[#585D69] stroke-[#585D69]',
					tooltip: 'bg-[#585D69] border-[#585D69]',
				}
		}
	}

	//получаем цвет фона в зависимости от статуса товара
	const getProductStatusFill = (status: string) => {
		switch (status) {
			case 'ok':
				return {
					rect: 'fill-[#3BD57C]',
					tooltip: 'bg-[#3BD57C]',
				}
			case 'low':
				return {
					rect: 'fill-[#4C87FF]',
					tooltip: 'bg-[#4C87FF]',
				}
			case 'critical':
				return {
					rect: 'fill-[#FDB840]',
					tooltip: 'bg-[#FDB840]',
				}
			default:
				return {
					rect: 'fill-[#585D69]',
					tooltip: 'bg-[#585D69]',
				}
		}
	}

	//получаем цвет в зависимости от кол-ва минут, прошедших с последнего сканирования
	const getProductStatusBorder = (time: number) => {
		switch (true) {
			case time >= 8 && time < 10:
				return {
					rect: 'stroke-[#D78D0E]',
					tooltip: 'border-[#D78D0E]',
				}
			case time>=10 || time === null:
				return {
					rect: 'stroke-[#D92020]',
					tooltip: 'border-[#D92020]',
				}
			case time<8:
				return {
					rect: 'stroke-[#078E40]',
					tooltip: 'border-[#078E40]',
				}
			default:
				return {
					rect: 'stroke-[#585D69]',
					tooltip: 'border-[#585D69]',
				}
		}
	}

	const getStatusName = (status: string) => {
		switch (status) {
			case 'ok':
				return 'ОК'
			case 'low':
				return 'Низкий остаток'
			case 'critical':
				return 'Критично'
			default:
				return 'Неизвестен'
		}
	}

	//следим за изменением контейнера
	useEffect(() => {
		const container = containerRef.current
		if (!container) return

		const observer = new ResizeObserver(entries => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect
				setSize({ width, height })
			}
		})
		observer.observe(container)
		return () => observer.disconnect()
	}, [])

	//задаем размеры ячеек
	const cellWidth = size.width / GRID_X
	const cellHeight = size.height / GRID_Y

	//задаем размер сетки
	const gridWidth = cellWidth * GRID_X
	const gridHeight = cellHeight * GRID_Y

	//смещение (отступы)
	const offsetX = 10
	const offsetY = 10

	const letters = Array.from({ length: GRID_X }, (_, i) =>
		String.fromCharCode(65 + i)
	)
	const numbers = Array.from({ length: GRID_Y }, (_, i) => i + 1)

	return (
		<div
			ref={containerRef}
			className='relative w-full h-full bg-[#F6F7F7] overflow-hidden rounded-[10px]'
		>
			<svg
				className={`absolute top-0 left-0 w-full h-full ${
					isDragging ? 'cursor-grabbing' : 'cursor-default'
				}`}
				viewBox={`0 0 ${size.width + 20} ${size.height + 20}`}
				preserveAspectRatio='xMidYMid meet'
				onMouseDown={handleMouseDown}
				onMouseUp={handleMouseUp}
				onMouseMove={handleMouseMove}
			>
				<motion.g
					animate={{
						x: transform.x,
						y: transform.y,
						scale: transform.scale,
					}}
					transition={{ duration: 0.1 }}
				>
					<g transform={`translate(${offsetX}, ${offsetY})`}>
						<rect
							x={0}
							y={0}
							width={gridWidth}
							height={gridHeight / 4}
							fill='#FFD6D6'
							opacity={0.3}
						/>
						<rect
							x={0}
							y={gridHeight/4}
							width={gridWidth}
							height={gridHeight / 2}
							fill='#D6FFD6'
							opacity={0.3}
						/>
						<rect
							x={0}
							y={(gridHeight/4)*3}
							width={gridWidth}
							height={gridHeight / 4}
							fill='#D6E0FF'
							opacity={0.3}
						/>
						{/* СЕТКА */}
						{letters.map((_, i) => (
							<line
								key={`v-${i}`}
								x1={i * cellWidth}
								y1={0}
								x2={i * cellWidth}
								y2={size.height}
								stroke='#aaa'
								strokeDasharray='4'
							/>
						))}
						{numbers.map((_, i) => (
							<line
								key={`h-${i}`}
								x1={0}
								y1={i * cellHeight}
								x2={size.width}
								y2={i * cellHeight}
								stroke='#aaa'
								strokeDasharray='4'
							/>
						))}

						{/* ТОВАРЫ */}
						{products.map((item, index) => (
							<TooltipProvider>
								<Tooltip>
									<TooltipTrigger asChild>
										<rect
											key={index}
											x={item.current_shelf * cellWidth}
											y={(GRID_Y - item.current_row - 1) * cellHeight}
											width={cellWidth}
											height={cellHeight}
											className={`
												${getProductStatusFill(item.status).rect}
												${getProductStatusBorder(getMinutesAgo(item.created_at)).rect}`
											}
											opacity={1}
											stroke='#ffffff'
											rx={2}
										/>
									</TooltipTrigger>
									<TooltipContent
										className={`
											${getProductStatusFill(item.status).tooltip}
											${getProductStatusBorder(getMinutesAgo(item.created_at)).tooltip} p-2 border-[1px] text-[10px]`}
									>
										<p>имя: {item.name}</p>
										<Separator className='bg-black' />
										<p>кол-во: {item.stock}</p>
										<Separator className='bg-black' />
										<p>статус: {getStatusName(item.status)}</p>
										<Separator className='bg-black' />
										<p>скан: {getMinutesAgo(item.created_at)} мин. назад</p>
									</TooltipContent>
								</Tooltip>
							</TooltipProvider>
						))}

						{/* РОБОТЫ */}
						{robots.map((robot, index) => (
							<TooltipProvider>
								<Tooltip>
									<TooltipTrigger asChild>
										<motion.g
											key={index}
											animate={{
												x: robot.x * cellWidth,
												y: (GRID_Y - robot.y) * cellHeight,
											}}
											transition={{ duration: 0.8, ease: 'easeInOut' }}
										>
											<circle
												r={Math.min(cellWidth, cellHeight) * 0.4}
												strokeWidth={0.5}
												className={`${
													getRobotStatusStyles(robot.status).circle
												}`}
											/>
											<text
												className='select-none'
												textAnchor='middle'
												dominantBaseline='middle'
												fontSize={Math.min(cellWidth, cellHeight) * 0.5}
												fill='white'
												fontWeight='bold'
											>
												{index + 1}
											</text>
										</motion.g>
									</TooltipTrigger>
									<TooltipContent
										className={`${
											getRobotStatusStyles(robot.status).tooltip
										} p-2 border-[1px] text-[10px]`}
									>
										<p>id: {robot.robot_id}</p>
										<Separator className='bg-black' />
										<p>заряд: {robot.battery_level}%</p>
										<Separator className='bg-black' />
										<p>
											обновлено: &nbsp;
											{new Date(robot.updated_at).toLocaleTimeString('ru-RU', {
												hour: '2-digit',
												minute: '2-digit',
											})}
										</p>
									</TooltipContent>
								</Tooltip>
							</TooltipProvider>
						))}
					</g>
				</motion.g>
			</svg>
			<div className='absolute bottom-4 right-4 flex flex-col gap-2'>
				<Button
					onClick={centerMap}
					size='icon'
					title='Центрировать'
					aria-label='Центрировать'
					className='map-button group'
				>
					<Aim
						className='map-button-icon group-hover:fill-black'
						fill='#585D69'
					/>
				</Button>
				<ButtonGroup
					orientation='vertical'
					aria-label='Media controls'
					className='h-fit'
				>
					<Button
						onClick={zoomIn}
						size='icon'
						title='Приблизить'
						aria-label='Приблизить'
						className='map-button group'
					>
						<AddLarge
							className='map-button-icon group-hover:fill-black'
							fill='#585D69'
						/>
					</Button>
					<Button
						onClick={zoomOut}
						size='icon'
						title='Отдалить'
						aria-label='Отдалить'
						className='map-button group'
					>
						<RemoveLarge
							className='map-button-icon group-hover:fill-black'
							fill='#585D69'
						/>
					</Button>
				</ButtonGroup>
			</div>
		</div>
	)
}
