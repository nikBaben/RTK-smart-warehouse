import { useEffect, useState } from 'react'
import api from '@/api/axios'
import { useWarehouseStore } from '@/store/useWarehouseStore'

interface ForecastItem {
  product_id: string
  product_name: string
  depletion_date: string
  reliability: number | null
  stock: number | null
  required_delivery: number | null
}

export function ForecastAI() {
  const warehouseId = useWarehouseStore(state => state.selectedWarehouse?.id)
  const [items, setItems] = useState<ForecastItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setItems([])
    setError(false)
    if (!warehouseId) {
      setLoading(false)
      return () => controller.abort()
    }
    setLoading(true)
    api.get<ForecastItem[]>('/ml/soon_depleted', {
      params: { warehouse_id: warehouseId }, signal: controller.signal,
    }).then(response => {
      if (!controller.signal.aborted) setItems(response.data)
    }).catch(() => {
      if (!controller.signal.aborted) setError(true)
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [warehouseId, revision])

  return (
    <div className='bg-white rounded-[15px]'>
      <div className='flex items-center justify-between'>
        <h3 className='dashboard-widget-font'>Прогноз исчерпания запасов</h3>
        <button type='button' disabled={loading} onClick={() => setRevision(value => value + 1)}
          className='text-sm text-[#7700FF] disabled:opacity-50'>Обновить</button>
      </div>
      {loading && <p className='p-3 text-sm text-gray-500'>Загружаем прогноз…</p>}
      {!loading && error && <p className='p-3 text-sm text-red-600'>Не удалось загрузить прогноз.</p>}
      {!loading && !error && items.length === 0 &&
        <p className='p-3 text-sm text-gray-500'>Прогнозов исчерпания пока нет. Они появятся после расчёта планировщиком при достаточной истории операций.</p>}
      <div className='flex flex-col gap-2'>
        {items.map(item => (
          <div key={item.product_id} className='flex flex-wrap justify-between gap-3 bg-[#F6F7F7] rounded-[10px] px-3 py-3 text-xs'>
            <div>
              <p className='font-medium text-sm'>{item.product_name}</p>
              <p>осталось {item.stock ?? '—'} шт</p>
            </div>
            <div>
              <p>ожидаемое исчерпание {new Date(item.depletion_date).toLocaleDateString('ru-RU')}</p>
              <p>до оптимального запаса: {item.required_delivery ?? '—'} шт</p>
            </div>
            <p>вероятность исчерпания: {item.reliability === null ? '—' : `${Math.round(item.reliability * 100)}%`}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ForecastAI
