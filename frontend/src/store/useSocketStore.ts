import { create } from 'zustand'
import { ReadyState } from 'react-use-websocket'
import { subscribeWithSelector } from 'zustand/middleware'
import { toast } from 'sonner'

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
	avgBatteryLoading: boolean
	avgBatteryError?: string | null

	robotsData?: RobotActiveRobots
	robotsLoading: boolean
	robotsError?: string | null

	scanned24h?: InventoryScanned24h
	scanned24hLoading: boolean

	criticalUnique?: InventoryCriticalUnique
	criticalUniqueLoading: boolean

	statusAvg?: InventoryStatusAvg
	statusAvgLoading: boolean

	activitySeries?: RobotActivitySeries
	activitySeriesLoading: boolean

	productScan?: ProductScan
	productScanLoading: boolean

	robotPositions?: RobotPositions
	robotPositionsLoading: boolean

	productSnapshot?: ProductSnapshot
	productSnapshotLoading: boolean

	connectionState: ReadyState

	setConnectionState: (state: ReadyState) => void
	updateData: (msg: SocketMessage) => void
	resetData: () => void
}

export const useSocketStore = create(
	subscribeWithSelector<SocketState>(set => ({
		connectionState: ReadyState.CLOSED,

		avgBatteryLoading: true,
		robotsLoading: true,
		scanned24hLoading: true,
		criticalUniqueLoading: true,
		statusAvgLoading: true,
		activitySeriesLoading: true,
		productScanLoading: true,
		robotPositionsLoading: true,
		productSnapshotLoading: true,
		setConnectionState: state => set({ connectionState: state }),

		updateData: msg => {
			try {
				switch (msg.type) {
					case 'robot.avg_battery':
						set({ avgBattery: msg, avgBatteryLoading: false })
						break
					case 'robot.active_robots':
						set({ robotsData: msg, robotsLoading: false })
						break
					case 'inventory.scanned_24h':
						set({ scanned24h: msg, scanned24hLoading: false })
						break
					case 'inventory.critical_unique':
						set({ criticalUnique: msg, criticalUniqueLoading: false })
						break
					case 'inventory.status_avg':
						set({ statusAvg: msg, statusAvgLoading: false })
						break
					case 'robot.activity_series':
						set(state => {
							if (
								JSON.stringify(state.activitySeries?.series) ===
								JSON.stringify(msg.series)
							)
								return {}
							return { activitySeries: msg, activitySeriesLoading: false }
						})
						break
					case 'product.scan':
						set({ productScan: msg, productScanLoading: false })
						break
					case 'robot.positions':
						set({ robotPositions: msg, robotPositionsLoading: false })
						break
					case 'product.snapshot':
						set({ productSnapshot: msg, productSnapshotLoading: false })
						break
					default:
						console.warn('⚠️ Неизвестный тип сообщения:', msg)
				}
			} catch (err) {
				toast.error('Ошибка при обновлении сокета')
				console.error('Ошибка при обновлении сокета:', err)
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
				
				avgBatteryLoading: true,
				robotsLoading: true,
				scanned24hLoading: true,
				criticalUniqueLoading: true,
				statusAvgLoading: true,
				activitySeriesLoading: true,
				productScanLoading: true,
				robotPositionsLoading: true,
				productSnapshotLoading: true,
			})
		},
	}))
)