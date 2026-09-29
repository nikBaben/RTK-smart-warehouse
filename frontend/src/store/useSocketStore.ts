import { create } from 'zustand'
import { ReadyState } from 'react-use-websocket'
import { subscribeWithSelector } from 'zustand/middleware'

type RobotAvgBattery = {
  type: 'robot.avg_battery'
	warehouse_id: string
  avg_battery: number
}

type RobotActiveRobots = {
	type: 'robot.active_robots'
	warehouse_id: string
	active_robots: number
	robots: number
}

type InventoryCriticalUnique = {
  type: 'inventory.critical_unique'
	warehouse_id: string
  unique_articles: number
}

type InventoryScanned24h = {
	type: 'inventory.scanned_24h'
	warehouse_id: string
	count: number
}

type InventoryStatusAvg = {
  type: 'inventory.status_avg'
  warehouse_id: string
	status: string
	max_avg: number
}

type RobotActivitySeries = {
	type: 'robot.activity_series'
	warehouse_id: string
	window_min: number
	bucket_sec: number
	series: [string,number][]
	ts: string
	total_robots: number
}

type Product = {
	robot_id: string
	name: string
	category: string
	article: string
	current_row: number
	current_shelf: number
	shelf_num: string
	current_zone: string
	stock: number
	status: string
	scanned_at: string
}


type ProductScan = {
	type: 'product.scan'
	warehouse_id: string
	scans: Product[]
}

type RobotPositions = {
	type: 'robot.positions'
	warehouse_id: string
	robots: MapRobot[]
}

type MapRobot = {
	robot_id: string
	x: number
	y: number
	shelf: string
	battery_level: number
	status: string
	updated_at: string
}

type ProductSnapshot = {
	type: 'product.snapshot'
	warehouse_id: string
	items: MapProduct[]
}

type MapProduct = {
	id: string
	name: string
	category: string
	warehouse_id: string
	current_zone: string
	current_row: number
	current_shelf: number
	status: string
	stock: number
	min_stock: number
	optimal_stock: number
	created_at: string
}

type SocketMessage =
	| RobotAvgBattery
	| RobotActiveRobots
	| InventoryScanned24h
	| InventoryCriticalUnique
	| InventoryStatusAvg
	| RobotActivitySeries
	| ProductScan
	| RobotPositions
	| ProductSnapshot

interface SocketState {
	avgBattery?: RobotAvgBattery
	robotsData?: RobotActiveRobots
	scanned24h?: InventoryScanned24h
	criticalUnique?: InventoryCriticalUnique
	statusAvg?: InventoryStatusAvg
	activitySeries?: RobotActivitySeries
	productScan?: ProductScan
	robotPositions?: RobotPositions
	productSnapshot?: ProductSnapshot
	connectionState: ReadyState
	updateData: (msg: SocketMessage) => void
	resetData: () => void
	setConnectionState: (state: ReadyState) => void
}

export const useSocketStore = create(
	subscribeWithSelector<SocketState>(set => ({
		avgBattery: undefined,
		robotsData: undefined,
		scanned24h: undefined,
		criticalUnique: undefined,
		statusAvg: undefined,
		activitySeries: undefined,
		productScan: undefined,
		connectionState: ReadyState.CLOSED,
		setConnectionState: state => set({ connectionState: state }),

		updateData: msg => {
			switch (msg.type) {
				case 'robot.avg_battery':
					set({ avgBattery: msg });
					break
				case 'robot.active_robots':
					set({ robotsData: msg });
					break
				case 'inventory.scanned_24h':
					set({ scanned24h: msg });
					break
				case 'inventory.critical_unique':
					set({ criticalUnique: msg });
					break
				case 'inventory.status_avg':
					set({ statusAvg: msg });
					break
				case 'robot.activity_series':
					set(state => {
						if (
							JSON.stringify(state.activitySeries?.series) ===
							JSON.stringify(msg.series)
						) {
							return {} // ничего не меняем, чтобы не вызавать ререндер
						}
						return { activitySeries: msg } // заменяем полностью
					})
					break
				case 'product.scan':
					set({ productScan: msg });
					break
				case 'robot.positions':
					set({ robotPositions: msg });
					break
				case 'product.snapshot':
					set({ productSnapshot: msg });
					break
				default:
					console.warn('⚠️ Неизвестный тип сообщения:', msg)
			}
		},
		resetData: () => {
			set({
				avgBattery: undefined,
				robotsData: undefined,
				scanned24h: undefined,
				criticalUnique: undefined,
				statusAvg: undefined,
				activitySeries: undefined,
				productScan: undefined,
			})
		},
	}))
)