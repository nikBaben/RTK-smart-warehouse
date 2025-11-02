import { useState, useEffect } from 'react'
import axios from 'axios'
import api from '@/api/axios' // общий axios-инстанс

// ========================
// 🔹 Типы
// ========================

export interface InventoryHistoryItem {
	id: number | string
	product_name?: string
	name?: string
	category: string
	zone?: string
	current_zone?: string
	status: string
	count?: number
	expected_count?: number
	difference?: number
	stock?: number
	user?: string
	created_at: string
	updated_at?: string | null
	[key: string]: string | number | null | undefined
}

export interface HistoryFilters {
	search?: string
	zones?: string[]
	categories?: string[]
	statuses?: string[]
	date_from?: string
	date_to?: string
	periods?: string[]
}

export type SortOrder = 'asc' | 'desc'

export interface HistoryResponse {
	data: any
}

// ========================
// 🔹 Сервис работы с API (с логами)
// ========================

const historyService = {
	async getFilteredHistory(
		warehouseId: string,
		params: {
			page?: number
			pageSize?: number
			search?: string
			zones?: string[]
			categories?: string[]
			statuses?: string[]
			date_from?: string
			date_to?: string
			periods?: string[]
			sort_by?: string
			sort_order?: SortOrder
		}
	): Promise<{ data: InventoryHistoryItem[]; total: number }> {
		const {
			page = 1,
			pageSize = 20,
			search = '',
			zones = [],
			categories = [],
			statuses = [],
			date_from,
			date_to,
			periods = [],
			sort_by = 'created_at',
			sort_order = 'desc',
		} = params

		const payload = {
			zone_filter: zones.length ? zones : undefined,
			category_filter: categories.length ? categories : undefined,
			status_filter: statuses.length ? statuses : undefined,
			date_from: date_from || undefined,
			date_to: date_to || undefined,
			search_string: search || undefined,
			period_buttons: periods.length ? periods : undefined,
			sort_by,
			sort_order,
			page,
			page_size: pageSize,
		}

		const endpoint = `/inventory_history/get_filtered_history/${warehouseId}`

		console.groupCollapsed(
			`%c📤 [InventoryHistory] POST ${endpoint}`,
			'color:#007acc;font-weight:bold;'
		)
		console.log('➡ Payload:', payload)
		console.groupEnd()

		try {
			const response = await api.post<HistoryResponse>(endpoint, payload)

			console.groupCollapsed(
				`%c✅ [InventoryHistory] Response ${endpoint}`,
				'color:green;font-weight:bold;'
			)
			console.log('📦 Raw response:', response.data)
			console.groupEnd()

			const rawData = response.data.data || [[], 0]
			const nestedItems = rawData[0] || []
			const total = rawData[1] || 0

			const items = nestedItems.map(([item, expected, difference]: any) => ({
				...item,
				expected_count: expected ?? 0,
				difference,
			}))

			return { data: items, total }
		} catch (err) {
			console.groupCollapsed(
				`%c❌ [InventoryHistory] Error ${endpoint}`,
				'color:red;font-weight:bold;'
			)
			console.error(err)
			console.groupEnd()
			throw err
		}
	},
}

// ========================
// 🔹 Форматирование даты
// ========================

function formatDate(dateString: string): string {
	if (!dateString) return ''
	const date = new Date(dateString)
	const day = String(date.getDate()).padStart(2, '0')
	const month = String(date.getMonth() + 1).padStart(2, '0')
	const year = String(date.getFullYear()).slice(-2)
	const hours = String(date.getHours()).padStart(2, '0')
	const minutes = String(date.getMinutes()).padStart(2, '0')
	return `${day}.${month}.${year} - ${hours}:${minutes}`
}

// ========================
// 🔹 Основной хук (с логами)
// ========================

export function useInventoryHistory(
	warehouseId?: string,
	token?: string,
	productsCount?: number,
	filters?: HistoryFilters,
	sortBy?: string | null,
	sortOrder?: SortOrder
) {
	const [data, setData] = useState<InventoryHistoryItem[]>([])
	const [loading, setLoading] = useState(false)
	const [error, setError] = useState<string | null>(null)
	const [page, setPage] = useState(1)
	const [pageSize, setPageSize] = useState(20)
	const [total, setTotal] = useState<number>(productsCount ?? 0)

	const totalPages = Math.max(1, Math.ceil(total / pageSize))

	useEffect(() => {
		if (!warehouseId || !token) {
			console.warn('⚠️ [InventoryHistory] warehouseId или token отсутствует')
			return
		}

		const fetchData = async () => {
			setLoading(true)
			setError(null)

			console.groupCollapsed(
				`%c🔄 [InventoryHistory] Fetching data...`,
				'color:#ffaa00;font-weight:bold;'
			)
			console.log('🏷 warehouseId:', warehouseId)
			console.log('🔑 token:', token ? '[есть]' : '[нет]')
			console.log('🔍 filters:', filters)
			console.log('📄 page:', page, 'pageSize:', pageSize)
			console.groupEnd()

			try {
				const { data: historyData, total } =
					await historyService.getFilteredHistory(warehouseId, {
						page,
						pageSize,
						search: filters?.search ?? '',
						zones: filters?.zones ?? [],
						categories: filters?.categories ?? [],
						statuses: filters?.statuses ?? [],
						date_from: filters?.date_from,
						date_to: filters?.date_to,
						periods: filters?.periods ?? [],
						sort_by: sortBy ?? 'created_at',
						sort_order: sortOrder ?? 'desc',
					})

				const formatted = historyData.map(item => ({
					...item,
					created_at: formatDate(item.created_at),
				}))

				setData(formatted)
				setTotal(total)

				console.log(
					`%c✅ [InventoryHistory] Успешно загружено ${formatted.length} записей`,
					'color:green;font-weight:bold;'
				)
			} catch (err) {
				console.error('❌ [InventoryHistory] Ошибка при загрузке:', err)
				if (axios.isAxiosError(err) && err.response?.status === 442) {
					setData([])
					setError('Нет подходящих записей')
				} else {
					setData([])
					setError('Не удалось загрузить данные')
				}
			} finally {
				setLoading(false)
			}
		}

		fetchData()
	}, [
		warehouseId,
		token,
		page,
		pageSize,
		filters?.search,
		filters?.zones,
		filters?.categories,
		filters?.statuses,
		filters?.date_from,
		filters?.date_to,
		filters?.periods,
		sortBy,
		sortOrder,
	])

	return {
		data,
		loading,
		error,
		page,
		pageSize,
		total,
		totalPages,
		setPage,
		setPageSize,
	}
}
