import api from '@/api/axios'
import { create } from 'zustand'
import type { Shipment } from '@/components/types/shipment'
import type { Delivery } from '@/components/types/delivery'

type SupplyStore = {
	shipments: Shipment[]
	deliveries: Delivery[]
	loading: boolean
	error: string | null

	fetchSupplies: (warehouse_id: string) => Promise<void>
	clearSupplies: () => void
}

export const useSupplyStore = create<SupplyStore>(set => ({
	shipments: [],
	deliveries: [],
  loading: false,
  error: null,

  fetchSupplies: async (warehouse_id) => {
    try{
			set({ loading: true, error: null })

			//помещаем массивы из ответа в data
			const { data } = await api.get(`supplies/warehouse/${warehouse_id}`)
			const formatDate = (iso: string) => new Date(iso).toLocaleDateString('ru-RU')
      
      //преобразуем строку из формата iso в читаемую дату
      set({
				shipments: (data.shipments || []).map((s: any) => ({
					...s,
					scheduled_at: formatDate(s.scheduled_at),
				})),
        deliveries: (data.deliveries || []).map((s: any)=>({
          ...s,
          scheduled_at: formatDate(s.scheduled_at),
        }))
			})
		} catch (err: any){
      set({
				error: err?.message || 'Ошибка при загрузке поставок',
				loading: false,
			})
    }
  },

  clearSupplies: () => set({shipments:[], deliveries:[]})
}))