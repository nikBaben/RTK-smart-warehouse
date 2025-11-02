import { useState, useEffect } from "react";
import axios from "axios";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import CheckLarge from "@atomaro/icons/24/navigation/CheckLarge";
import CloseLarge from "@atomaro/icons/24/navigation/CloseLarge";
import { Checkbox } from "@/components/ui/checkbox";
import SelectableButtons from "@/components/widgets/SelectableButtons";
import { UserAvatar } from '../ui/UserAvatar.tsx';

import { useInventoryHistory } from "@/hooks/useInventoryHistory.tsx";
import { useWarehouseStore } from '@/store/useWarehouseStore';

import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select';

import { DatePicker } from "../widgets/DatePicker";
import { ButtonGrid } from "../widgets/ButtonGrid";
import { DataTableHistory } from "../widgets/DataTableHistory";
import { TrendGraph } from "../widgets/TrendGraph.tsx";

import StatisticsLine from '@atomaro/icons/24/business/StatisticsLine';
import Upload from '@atomaro/icons/24/action/Upload';


function HistoryPage(){
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "ok":
        return "bg-[#0ACB5B]";
      case "низкий остаток":
        return "bg-[#FDA610]";
      case "критично":
        return "bg-[#FF2626]";
      default:
        return "bg-gray-400";
    }
  };

  const [search, setSearch] = useState("");
  const [selectedZone, setSelectedZone] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string[]>([]);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [startDate, setStartDate] = useState<Date | undefined>();
  const [endDate, setEndDate] = useState<Date | undefined>();
  const [selectedPeriods, setSelectedPeriods] = useState<string[]>([]);
  const [appliedFilters, setAppliedFilters] = useState<any>({});
  const [showGraph, setShowGraph] = useState(false);


  const [selectedRows, setSelectedRows] = useState<string[]>([]);
  const [graphData, setGraphData] = useState<any[]>([]);

  const [sortBy, setSortBy] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const handleSort = (key: string, direction: "asc" | "desc") => {
    setSortBy(key);
    setSortOrder(direction);
    setPage(1);
  };

  const token = localStorage.getItem("token");
  const { warehouses, selectedWarehouse, setSelectedWarehouse, fetchWarehouses } =
    useWarehouseStore();

    const [zones, setZones] = useState<string[]>([]);
    const [categories, setCategories] = useState<string[]>([]);

    useEffect(() => {
    const fetchZonesAndCategories = async () => {
        if (!selectedWarehouse?.id || !token) return;

        try {
        const [zonesRes, categoriesRes] = await Promise.all([
            axios.get(
            `https://dev.rtk-smart-warehouse.ru/api/v1/inventory_history/inventory_history_unique_zones/${selectedWarehouse.id}`,
            { headers: { Authorization: `Bearer ${token}` } }
            ),
            axios.get(
            `https://dev.rtk-smart-warehouse.ru/api/v1/inventory_history/inventory_history_unique_categories/${selectedWarehouse.id}`,
            { headers: { Authorization: `Bearer ${token}` } }
            ),
        ]);

        setZones(zonesRes.data || []);
        setCategories(categoriesRes.data || []);
        } catch (err) {
        console.error("Ошибка загрузки зон или категорий:", err);
        setZones([]);
        setCategories([]);
        }
    };


    fetchZonesAndCategories();
    }, [selectedWarehouse?.id, token]);


  useEffect(() => {
    fetchWarehouses();
  }, []);

    const {
    data: filteredData,
    loading,
    error,
    page,
    pageSize,
    totalPages,
    setPage,
    setPageSize,
        } = useInventoryHistory(
    selectedWarehouse?.id,
    token ?? undefined,
    selectedWarehouse?.products_count,
    appliedFilters,
    sortBy,
    sortOrder
    );

    console.log(selectedWarehouse?.id);
    console.log(selectedRows);
    console.log(graphData);

  type Column<T> = {
    header: string;
    accessor: keyof T | ((row: T) => React.ReactNode);
    className?: string;
    align?: "left" | "center" | "right";
    sortable?: boolean;
    sortKey?: keyof T;
  };

  const formatDateLocal = (date?: Date) => {
    if (!date) return undefined;
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
};

  const columns: Column<any>[] = [
    { header: "дата и время проверки", accessor: "created_at", sortable: true },
    { header: "id робота", accessor: "robot_id", sortable: true },
    { header: "артикул", accessor: "article", sortable: true },
    { header: "категория", accessor: "category", sortable: true },
    { header: "зона склада", accessor: "current_zone", sortable: true },
    { header: "название", accessor: "name", sortable: true },
    {
      header: "количество ожидаемое/фактическое",
      accessor: "stock",
      sortable: true,
    },
    { header: "расхождение (+/-)", accessor: "deviation", sortable: true },
    {
      header: "статус",
      accessor: (row) => (
        <span
          className={`${getStatusColor(
            row.status
          )} text-black text-[10px] font-light rounded-[5px] px-[4px] py-[2px]`}
        >
          {row.status}
        </span>
      ),
      align: "left",
      sortable: true,
      sortKey: "status",
    },
  ];

  const applyFilters = () => {
    setAppliedFilters({
      search,
      zones: selectedZone,
      categories: selectedCategory,
      statuses: selectedStatuses,
      date_from: formatDateLocal(startDate),
      date_to: formatDateLocal(endDate),
      periods: selectedPeriods,
    });
  };

  const resetFilters = () => {
    setSearch("");
    setSelectedZone([]);
    setSelectedCategory([]);
    setSelectedStatuses([]);
    setStartDate(undefined);
    setEndDate(undefined);
    setSelectedPeriods([]);
    setAppliedFilters({});
    setSelectedRows([]);
    setSortBy("created_at");
    setSortOrder("desc");
  };

  const toggleStatus = (status: string) => {
    setSelectedStatuses((prev) =>
      prev.includes(status)
        ? prev.filter((s) => s !== status)
        : [...prev, status]
    );
  };

    return (
        <div className="flex bg-[#F4F4F5] min-h-screen">
            <div className="flex flex-col flex-1 overflow-hidden ml-[60px]">
                <header className='header-style'>
                    <span className='pagename-font'>Исторические данные</span>
                    <div className='flex items-center space-x-5'>
                        <div className='relative'>
							<Select
								value={selectedWarehouse?.id || ''}
								onValueChange={id => {
									const wh = warehouses.find(w => w.id === id) || null
									setSelectedWarehouse(wh)
								}}
							>
								<SelectTrigger className='select-warehouse'>
									<SelectValue placeholder='Выберите склад' />
								</SelectTrigger>
								<SelectContent>
									{warehouses.map(w => (
										<SelectItem key={w.id} value={w.id}>
											{w.name}
										</SelectItem>
									))}
								</SelectContent>
							</Select>
						</div>
                        <UserAvatar />
                    </div>
                </header>
                <main className="flex-1 overflow-auto p-[10px]">
                    {selectedWarehouse?.id == null ? (
						<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[40px]'>
							<h1>выберите склад для отображения истории</h1>
						</div>
					) : (
                        <div className="flex">
                            <div className="h-[662px] w-[218px]">
                                <h2 className="font-medium text-[20px] "> Фильтры</h2>
                                <div className="h-[662px] w-[218px] bg-white rounded-[15px]">
                                    <div className="p-[10px] flex flex-col w-[199px] gap-[15px]">
                                        <div className="h-[42px]">
                                            <span className="text-[14px] font-medium"> Поиск </span>
                                            <Input value = {search} onChange={(e) => setSearch(e.target.value)} placeholder = "артикул или название товара" className="h-[24px] w-[198px] border-none shadow-none bg-[#F2F3F4] placeholder:font-medium placeholder:text-[12px] !text-[12px] !text-[#000000] px-[5px]"></Input>
                                        </div>
                                        <div className="h-[103px] w-[198px]">
                                            <span className="text-[14px] font-medium"> Выбор периода </span>
                                            <div className="h-[82px] w-[198px]">
                                                <div className="flex flex-col gap-[7px]">
                                                    <div>
                                                        <DatePicker 
                                                        startDate={startDate}
                                                        endDate={endDate}
                                                        onChange={(start, end) => {
                                                            setStartDate(start);
                                                            setEndDate(end);
                                                            setSelectedPeriods([]);
                                                        }}
                                                        />

                                                    </div> 
                                                    <div>
                                                        <ButtonGrid
                                                        selected={selectedPeriods}
                                                        onChange={(periods) => {
                                                            setSelectedPeriods(periods);
                                                            if (periods.length > 0) {
                                                            setStartDate(undefined);
                                                            setEndDate(undefined);
                                                            }
                                                        }}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="h-[120px] w-[198px]">
                                            <span className="text-[14px] font-medium"> Зоны склада </span>
                                            <SelectableButtons params={zones} onSelect={setSelectedZone} selected={selectedZone} multiple/>
                                        </div>
                                        <div className="h-[231px] w-[198px]">
                                            <span className="text-[14px] font-medium"> Категории товаров </span>
                                            <SelectableButtons params={categories} onSelect={setSelectedCategory} selected={selectedCategory} multiple/>
                                        </div>
                                        <div className="h-[53px] w-[198px]">
                                            <span className="text-[14px] font-medium"> Статус </span>
                                            <div className="h-[35px] pl-[5px] bg-[#F2F3F4] gap-[5px] rounded-[5px] flex-col items-center">
                                                <div className="flex gap-[5px] items-center">
                                                    <div className="flex gap-[2px] items-center">
                                                        <Checkbox 
                                                            checked={selectedStatuses.length === 0}  
                                                            onCheckedChange={() => setSelectedStatuses([])}
                                                            className="history-checkbox cursor-pointer"/> 
                                                        <span className="text-[#000000] text-[12px]">
                                                            все
                                                        </span>
                                                    </div>
                                                    <div className="flex gap-[2px] items-center">
                                                        <Checkbox 
                                                        checked={selectedStatuses.includes("OK")}
                                                        onCheckedChange={() => toggleStatus("OK")}
                                                        className="history-checkbox cursor-pointer"/> 
                                                        <span className="text-[#000000] text-[12px]">
                                                            ок
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-[5px]">
                                                    <div className="flex gap-[2px] items-center">
                                                        <Checkbox 
                                                        checked={selectedStatuses.includes("низкий остаток")} 
                                                        onCheckedChange={() => toggleStatus("низкий остаток")}
                                                        className="history-checkbox cursor-pointer"/> 
                                                        <span className="text-[#000000] text-[12px]">
                                                            низкий остаток
                                                        </span>                                         
                                                    </div>
                                                    <div className="flex gap-[2px]  items-center">
                                                        <Checkbox 
                                                        checked={selectedStatuses.includes("критично")} 
                                                        onCheckedChange={() => toggleStatus("критично")}
                                                        className="history-checkbox cursor-pointer"/> 
                                                        <span className="text-[#000000] text-[12px]">
                                                            критично
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex h-[18px] w-[198px] gap-[4px]">
                                            <Button onClick={resetFilters} className="bg-[#FF4F12] text-[10px] text-white h-[18px] w-[97px]">
                                                <CloseLarge fill="#FFFFFF"className="w-[7px] h-[7px]"/>
                                                Cбросить
                                            </Button>
                                            <Button onClick = {applyFilters} className="bg-[#7700FF] text-[10px] text-white h-[18px] w-[97px]">
                                                <CheckLarge fill="#FFFFFF"className="w-[7px] h-[7px]"/>
                                                Применить
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="flex flex-col pl-[10px] w-full  gap-[5px]">
                                {/*Ультра заглушка, потом что-то нормальное напишу*/}
                                <div className="h-[77px]">
                                    <h2 className="font-medium text-[20px]">Сводная статистика</h2>
                                    <div className="h-[46px] bg-white rounded-[15px] flex items-center justify-between p-[10px]">
                                        <span className="text-[14px] font-light">всего проверок за период: 12375</span>
                                        <span className="text-[14px] font-light">уникальных товаров: 56</span>
                                        <span className="text-[14px] font-light">выявлено расхождений: 21</span>
                                        <span className="text-[14px] font-light">среднее время инвентаризации: 10 мин</span>
                                    </div>
                                </div>
                                <div>
                                    <h2 className="font-medium text-[20px]">Историческая таблица</h2>
                                    <div className="h-[751px] bg-white rounded-[15px] pl-[10px] pr-[10px]">
                                        <DataTableHistory
                                            data={filteredData}
                                            columns={columns}
                                            totalPages={totalPages}
                                            page={page}
                                            rowsPerPage={pageSize}
                                            onPageChange={setPage}
                                            onRowsPerPageChange={setPageSize}
                                            isLoading={loading}
                                            selectedRows={selectedRows}
                                            setSelectedRows={setSelectedRows}
                                            sortBy={sortBy}               // из useInventoryHistory
                                            sortOrder={sortOrder}         // из useInventoryHistory
                                            onSortChange={handleSort} 
                                        />
                                    </div>
                                </div>
                                <div className="flex items-center justify-end gap-[10px] pt-[10px]">
                                    <div className="flex gap-[5px]">
                                    <Button
                                        className="h-[30px] w-[187px] text-[12px] text-[#7700FF] bg-[#F7F0FF] border-[#7700FF] border-[1px] rounded-[10px] font-medium"
                                        onClick={async () => {
                                            if (!selectedWarehouse?.id) {
                                            alert("Выберите склад");
                                            return;
                                            }
                                            if (selectedRows.length === 0) {
                                            alert("Выберите хотя бы одну строку для экспорта");
                                            return;
                                            }

                                            try {
                                            const res = await fetch(
                                                `https://dev.rtk-smart-warehouse.ru/api/v1/inventory_history/inventory_history_export_to_xl/${selectedWarehouse.id}`,
                                                {
                                                method: "POST",
                                                headers: {
                                                    "Content-Type": "application/json",
                                                    Authorization: `Bearer ${token}`,
                                                },
                                                body: JSON.stringify({ record_ids: selectedRows }),
                                                }
                                            );

                                            if (!res.ok) {
                                                const text = await res.text();
                                                console.error("Ошибка сервера:", text);
                                                throw new Error("Ошибка при получении файла");
                                            }

                                            const blob = await res.blob();

                                            const disposition = res.headers.get("Content-Disposition");
                                            let filename = "Отчёт.xlsx";
                                            if (disposition && disposition.includes("filename=")) {
                                                filename = disposition
                                                .split("filename=")[1]
                                                .replace(/"/g, "")
                                                .trim();
                                            }

                                            const url = window.URL.createObjectURL(blob);
                                            const a = document.createElement("a");
                                            a.href = url;
                                            a.download = filename;
                                            document.body.appendChild(a);
                                            a.click();
                                            a.remove();
                                            window.URL.revokeObjectURL(url);
                                            } catch (err) {
                                            console.error(err);
                                            alert("Не удалось скачать файл");
                                            }
                                        }}
                                        >
                                            <Upload fill="#7700FF" className="h-[8px] w-[8px]"/>
                                            Экспорт в Excel
                                    </Button>

                                    <Button
                                        className="h-[30px] w-[187px] text-[12px] text-[#7700FF] bg-[#F7F0FF] border-[#7700FF] border-[1px] rounded-[10px] font-medium"
                                        onClick={async () => {
                                            if (!selectedWarehouse?.id) {
                                            alert("Выберите склад");
                                            return;
                                            }
                                            if (selectedRows.length === 0) {
                                            alert("Выберите хотя бы одну строку для экспорта");
                                            return;
                                            }

                                            try {
                                            const res = await fetch(
                                                `https://dev.rtk-smart-warehouse.ru/api/v1/inventory_history/inventory_history_export_to_pdf/${selectedWarehouse.id}`,
                                                {
                                                method: "POST",
                                                headers: {
                                                    "Content-Type": "application/json",
                                                    Authorization: `Bearer ${token}`,
                                                },
                                                body: JSON.stringify({ record_ids: selectedRows }),
                                                }
                                            );

                                            if (!res.ok) {
                                                const text = await res.text();
                                                console.error("Ошибка сервера:", text);
                                                throw new Error("Ошибка при получении файла");
                                            }

                                            const blob = await res.blob();

                                            const disposition = res.headers.get("Content-Disposition");
                                            let filename = "Отчёт.pdf";
                                            if (disposition && disposition.includes("filename=")) {
                                                filename = disposition
                                                .split("filename=")[1]
                                                .replace(/"/g, "")
                                                .trim();
                                            }

                                            const url = window.URL.createObjectURL(blob);
                                            const a = document.createElement("a");
                                            a.href = url;
                                            a.download = filename;
                                            document.body.appendChild(a);
                                            a.click();
                                            a.remove();
                                            window.URL.revokeObjectURL(url);
                                            } catch (err) {
                                            console.error(err);
                                            alert("Не удалось скачать файл");
                                            }
                                        }}
                                        >
                                            <Upload fill="#7700FF" className="h-[8px] w-[8px]"/>
                                            Экспорт в PDF
                                        </Button>
                                    </div>
                                    <Button
                                        onClick={async () => {
                                            if (!selectedWarehouse?.id) {
                                            alert("Выберите склад");
                                            return;
                                            }
                                            if (selectedRows.length === 0) {
                                            alert("Выберите хотя бы одну строку для построения графика");
                                            return;
                                            }

                                            try {
                                            const res = await fetch(
                                                `https://dev.rtk-smart-warehouse.ru/api/v1/inventory_history/inventory_history_create_graph/${selectedWarehouse.id}`,
                                                {
                                                method: "POST",
                                                headers: {
                                                    "Content-Type": "application/json",
                                                    Authorization: `Bearer ${token}`,
                                                },
                                                body: JSON.stringify({ record_ids: selectedRows }),
                                                }
                                            );

                                            if (!res.ok) {
                                                const text = await res.text();
                                                console.error("Ошибка сервера:", text);
                                                throw new Error("Ошибка при построении графика");
                                            }

                                            const json = await res.json();
                                            const rawData = json.data || {};

                                            // Функция усечения до секунд
                                            const normalizeDate = (iso: string) => {
                                                const d = new Date(iso);
                                                d.setMilliseconds(0);
                                                return d.toISOString(); // формат YYYY-MM-DDTHH:mm:ssZ
                                            };

                                            // Шаг 1 — собираем все возможные метки времени
                                            const allDates = new Set<string>();
                                            Object.values(rawData).forEach((entries: any) => {
                                                entries.forEach(([dateStr]: [string, number]) =>
                                                allDates.add(normalizeDate(dateStr))
                                                );
                                            });

                                            const sortedDates = Array.from(allDates).sort(
                                                (a, b) => new Date(a).getTime() - new Date(b).getTime()
                                            );

                                            // Шаг 2 — создаем таблицу со всеми датами и товарами
                                            const merged: Record<string, any> = {};
                                            const lastKnown: Record<string, number | null> = {};

                                            sortedDates.forEach((date) => {
                                                merged[date] = { date };
                                                Object.keys(rawData).forEach((product) => {
                                                // Находим запись с этой датой, если есть
                                                const entry = (rawData[product] as [string, number][]).find(
                                                    ([d]) => normalizeDate(d) === date
                                                );

                                                if (entry) {
                                                    const [, value] = entry;
                                                    lastKnown[product] = value;
                                                }

                                                merged[date][product] =
                                                    lastKnown[product] !== undefined ? lastKnown[product] : null;
                                                });
                                            });

                                            // Превращаем в массив для Recharts
                                            const formattedData = Object.values(merged);

                                            setGraphData(formattedData);
                                            setShowGraph(true);
                                            } catch (err) {
                                            console.error(err);
                                            alert("Не удалось построить график");
                                            }
                                        }}
                                        className="h-[30px] w-[187px] text-[12px] text-white bg-[#7700FF] rounded-[10px] font-medium"
                                        >
                                        <StatisticsLine fill="white" className="h-[6px] w-[11px]" />
                                        Построить график
                                    </Button>
                                </div>
                            </div>
                        </div>
                    )}
                    {showGraph && (
                        <TrendGraph data={graphData} onClose={() => setShowGraph(false)} />
                    )}
                </main>
            </div>
        </div>
    )
}
export default HistoryPage;