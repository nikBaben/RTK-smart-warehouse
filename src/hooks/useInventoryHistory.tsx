import { useState, useEffect } from "react";
import axios from "axios";

const BASE_URL = "https://dev.rtk-smart-warehouse.ru/api/v1";

// ========================
// 🔹 Типы
// ========================

// Одна запись из истории инвентаризации
export interface InventoryHistoryItem {
  id: number | string;
  product_name?: string;
  name?: string;
  category: string;
  zone?: string;
  current_zone?: string;
  status: string;
  count?: number; // старое поле, оставляем для совместимости
  expected_count?: number; // ожидаемое количество (если null → 0)
  difference?: number; // расхождение
  stock?: number;
  user?: string;
  created_at: string;
  updated_at?: string | null;
  [key: string]: string | number | null | undefined;
}

// Параметры фильтрации
export interface HistoryFilters {
  search?: string;
  zones?: string[];
  categories?: string[];
  statuses?: string[];
  date_from?: string;
  date_to?: string;
  periods?: string[];
}

export type SortOrder = "asc" | "desc";

// Новый формат ответа сервера
export interface HistoryResponse {
  data: any; // структура стала динамической, типизируем вручную ниже
}

// ========================
// 🔹 Сервис работы с API
// ========================
const historyService = {
  async getFilteredHistory(
    warehouseId: string,
    token: string,
    params: {
      page?: number;
      pageSize?: number;
      search?: string;
      zones?: string[];
      categories?: string[];
      statuses?: string[];
      date_from?: string;
      date_to?: string;
      periods?: string[];
      sort_by?: string;
      sort_order?: SortOrder;
    }
  ): Promise<{ data: InventoryHistoryItem[]; total: number }> {
    const {
      page = 1,
      pageSize = 20,
      search = "",
      zones = [],
      categories = [],
      statuses = [],
      date_from,
      date_to,
      periods = [],
      sort_by = "created_at",
      sort_order = "desc",
    } = params;

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
    };

    const response = await axios.post<HistoryResponse>(
      `${BASE_URL}/inventory_history/get_filtered_history/${warehouseId}`,
      payload,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );

    // Новый формат: [[[item, expected_count, difference]], total]
    const rawData = response.data.data || [[], 0];
    const nestedItems = rawData[0] || [];
    const total = rawData[1] || 0;

    const items = nestedItems.map((entry: any) => {
      const [item, expected, difference] = entry;
      return {
        ...item,
        expected_count: expected ?? 0, // если null → 0
        difference,
      };
    });

    return { data: items, total };
  },
};

// ========================
// 🔹 Форматирование даты
// ========================
function formatDate(dateString: string): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const year = String(date.getFullYear()).slice(-2);
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${day}.${month}.${year} - ${hours}:${minutes}`;
}

// ========================
// 🔹 Основной хук
// ========================
export function useInventoryHistory(
  warehouseId?: string,
  token?: string,
  productsCount?: number,
  filters?: HistoryFilters,
  sortBy?: string | null,
  sortOrder?: SortOrder
) {
  const [data, setData] = useState<InventoryHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState<number>(productsCount ?? 0);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  useEffect(() => {
    if (!warehouseId || !token) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const { data: historyData, total } =
          await historyService.getFilteredHistory(warehouseId, token, {
            page,
            pageSize,
            search: filters?.search ?? "",
            zones: filters?.zones ?? [],
            categories: filters?.categories ?? [],
            statuses: filters?.statuses ?? [],
            date_from: filters?.date_from,
            date_to: filters?.date_to,
            periods: filters?.periods ?? [],
            sort_by: sortBy ?? "created_at",
            sort_order: sortOrder ?? "desc",
          });

        const formatted = historyData.map((item) => ({
          ...item,
          created_at: formatDate(item.created_at),
        }));

        setData(formatted);
        setTotal(total);
        setError(null);
      } catch (err) {
        console.error("Ошибка при загрузке истории:", err);
        if (axios.isAxiosError(err) && err.response?.status === 442) {
          setData([]);
          setError("Нет подходящих записей");
        } else {
          setData([]);
          setError("Не удалось загрузить данные");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
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
  ]);

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
  };
}
