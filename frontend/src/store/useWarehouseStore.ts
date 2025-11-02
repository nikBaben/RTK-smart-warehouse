import { create } from 'zustand'
import api from '@/api/axios'
import type { Warehouse } from '../components/types/warehouse'
import { toast } from 'sonner'


type WarehouseStore = {
	warehouses: Warehouse[]
	loading: boolean
	error: string | null
	selectedWarehouse: Warehouse | null
	/* fetchWarehouses: (token: string) => Promise<void> */
	fetchWarehouses: () => Promise<void>
	setSelectedWarehouse: (wh: Warehouse | null) => void
	updateWarehouse: (warehouse: Warehouse) => void
	deleteWarehouse: (warehouse: Warehouse) => Promise<void>
}

export const useWarehouseStore = create<WarehouseStore>((set, get) => ({
	warehouses: [],
	loading: false,
	error: null,
	selectedWarehouse: null,

	fetchWarehouses: async () => {
		set({ loading: true, error: null })
		try {
			const res = await api.get('/warehouses')
			set({ warehouses: res.data, loading: false })
		} catch (err) {
			set({ error: 'Не удалось получить список складов', loading: false })
		}
	},
	/* 	fetchWarehouses: async (token: string) => {
		set({ loading: true, error: null })
		try {
			const res = await api.get('/warehouses')
			set({ warehouses: res.data, loading: false })
		} catch (err) {
			set({ error: 'Не удалось получить список складов', loading: false })
		}
	}, */

	setSelectedWarehouse: wh => set({ selectedWarehouse: wh }),

	deleteWarehouse: async (warehouse) => {
		if (
			!confirm(
				`Вы действительно хотите удалить склад "${warehouse.name}"? Данное действие невозможно отменить`
			)
		)
			return
		try {
			await api.delete(`/warehouse/${warehouse.id}`)
			if (get().selectedWarehouse?.id === warehouse.id) {
				set({ selectedWarehouse: null })
			}
			//обновляем локальное состояние без доп запроса к серверу
			set({
				warehouses: get().warehouses.filter(w => String(w.id) !== String(warehouse.id)),
			})
			toast.success(`Склад ${warehouse.name} успешно удалён`)
		} catch (err) {
			console.error(err)
			toast.error(`Не удалось удалить склад ${warehouse.name}`)
		}
	},

	updateWarehouse: updated => {
		set({
			warehouses: get().warehouses.map(w =>
				w.id === updated.id ? updated : w
			),
			selectedWarehouse: updated,
		})
	},
}))
