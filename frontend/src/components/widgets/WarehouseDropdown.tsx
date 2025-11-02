import { useEffect, useState } from 'react';
import axios from 'axios';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';

type Warehouse = {
  id: string;
  name: string;
  products_count: number;
};

type Props = {
  selectedWarehouseId: string | null;
  setSelectedWarehouseId: (id: string | null) => void;
};

export function WarehouseDropdown({ selectedWarehouseId, setSelectedWarehouseId }: Props) {
  const token = localStorage.getItem('token');
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Загрузка складов
  useEffect(() => {
    const fetchWarehouses = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get(
          'https://rtk-smart-warehouse.ru/api/v1/warehouses?limit=100&offset=0',
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setWarehouses(response.data);
      } catch (err) {
        console.error('Ошибка загрузки складов:', err);
        setError('Не удалось загрузить склады');
      } finally {
        setLoading(false);
      }
    };

    fetchWarehouses();
  }, [token]);

  useEffect(() => {
    if (selectedWarehouseId) {
      localStorage.setItem('selectedWarehouseId', selectedWarehouseId);
    } else {
      localStorage.removeItem('selectedWarehouseId');
    }
  }, [selectedWarehouseId]);

  return (
    <div className="w-[250px]">
      <Select
        value={selectedWarehouseId || ''}
        onValueChange={(value) => setSelectedWarehouseId(value)}
      >
        <SelectTrigger className="w-full h-[38px] border-[#CCCCCC] border-[1px] rounded-[10px] text-[20px] text-[#7700FF] flex items-center justify-between px-4">
          <SelectValue placeholder="Выберите склад" />
        </SelectTrigger>
        <SelectContent className="bg-white border border-gray-300 rounded-[10px] shadow-lg text-[#7700FF] text-[18px]">
          {loading ? (
            <SelectItem value="loading" disabled>
              Загрузка...
            </SelectItem>
          ) : error ? (
            <SelectItem value="error" disabled>
              {error}
            </SelectItem>
          ) : (
            warehouses.map((wh) => (
              <SelectItem key={wh.id} value={wh.id}>
                {wh.name}
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
    </div>
  );
}
