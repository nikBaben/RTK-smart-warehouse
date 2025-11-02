import api from '@/api/axios'
import { create } from 'zustand'

type DepletionItem = {
	product_id: string
	product_name: string
	warehouse_id: string
	depletion_at: string
	reliability: number
	stock: number
	required_delivery: number
}

type DepletionState = {
  items: DepletionItem[]
  loading: boolean
  error: string | null

  fetchSoonDepleted: (warehouse_id: string) => Promise<void>
  recalcDepletion: (product_id: string, warehouse_id: string) => Promise<void>
}

export const useDepletionStore = create<DepletionState>((set, get) => ({
	items: [],
	loading: false,
	error: null,


	//получаем товары с ближайшим истощением
	fetchSoonDepleted: async(warehouse_id: string) => {
    set({loading: true, error: null})
    try{
      const {data} = await api.get('ml/soon_depleted',{params: { warehouse_id },})
      set({ items: data, loading: false })
    } catch (err: any){
      set({
				error: err?.response?.data?.message || err.message || 'Ошибка загрузки',
				loading: false,
			})
    } 
  },

  recalcDepletion: async (product_id: string, warehouse_id: string) => {
    try {
			await api.post('ml/depletion', null, {
				params: {
					product_id,
					warehouse_id,
					horizon_days: 30,
				},
			})
			await get().fetchSoonDepleted(warehouse_id)
		} catch (err: any) {
			set({
				error:
					err?.response?.data?.message || err.message || 'Ошибка пересчета',
				loading: false,
			})
		} finally {
			set({ loading: false })
		}
  }
}))