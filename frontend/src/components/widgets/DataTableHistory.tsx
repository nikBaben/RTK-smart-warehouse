"use client";

import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { Button } from "../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Skeleton } from "../ui/skeleton";

import ChevronDown from "@atomaro/icons/24/navigation/ChevronDown";
import ArrowRight from "@atomaro/icons/24/navigation/ArrowRight";

type Column<T> = {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  className?: string;
  align?: "left" | "center" | "right";
  sortable?: boolean;
  sortKey?: keyof T;
};

interface DataTableHistoryProps<T extends { id: string }> {
  data: T[];
  columns: Column<T>[];
  totalPages: number;
  page: number;
  rowsPerPage: number;
  onPageChange: (page: number) => void;
  onRowsPerPageChange: (rows: number) => void;
  isLoading?: boolean;
  selectedRows: string[];
  setSelectedRows: React.Dispatch<React.SetStateAction<string[]>>;
  
  onSortChange?: (key: string, direction: "asc" | "desc") => void;
  sortBy?: string | null;
  sortOrder?: "asc" | "desc" | null;
}

export function DataTableHistory<T extends { id: string }>(props: DataTableHistoryProps<T>) {
  const {
    data,
    columns,
    totalPages,
    page,
    rowsPerPage,
    onPageChange,
    onRowsPerPageChange,
    isLoading = false,
    selectedRows,
    setSelectedRows,
    onSortChange,
    sortBy = null,
    sortOrder = "asc",
  } = props;

  const toggleRow = (rowId: string) => {
    setSelectedRows((prev) =>
      prev.includes(rowId) ? prev.filter((i) => i !== rowId) : [...prev, rowId]
    );
  };

  const handleSort = (col: Column<T>) => {
    const key =
      typeof col.accessor === "string" ? col.accessor : col.sortKey ?? null;
    if (!key || !onSortChange) return;

    const currentKey = sortBy;
    const currentDir = sortOrder ?? "asc";
    const newDirection =
      currentKey === key && currentDir === "asc" ? "desc" : "asc";

    onSortChange(String(key), newDirection);
  };

  return (
    <div className="h-full flex flex-col bg-white rounded-[15px] overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        <Table className="w-full text-center border-separate border-spacing-y-[5px]">
          <TableHeader className="text-[10px] sticky top-0 bg-white z-10">
            <TableRow className="text-black">
              {columns.map((col, index) => {
                const key =
                  typeof col.accessor === "string" ? col.accessor : col.sortKey;
                const isActive = sortBy === key;

                return (
                  <TableHead
                    key={index}
                    onClick={() => col.sortable && handleSort(col)}
                    className={cn(
                      "text-center relative select-none",
                      col.sortable && "cursor-pointer",
                      index === 0 && "text-left"
                    )}
                  >
                    <div className="flex items-center justify-center gap-1">
                      {col.header}
                      {col.sortable && (
                        <ChevronDown
                          className={cn(
                            "w-[10px] h-[10px] transition-transform",
                            isActive &&
                              (sortOrder === "desc" ? "rotate-180" : ""),
                            !isActive && "opacity-30"
                          )}
                          fill="black"
                        />
                      )}
                    </div>
                  </TableHead>
                );
              })}
            </TableRow>
          </TableHeader>

          <TableBody className="[&_tr]:h-[30px]">
            {isLoading ? (
              <>
                {[...Array(rowsPerPage)].map((_, rowIndex) => (
                  <TableRow key={rowIndex} className="h-[30px] bg-[#F2F3F4]">
                    {columns.map((col, colIndex) => {
                      let widthClass = "w-[60px]";
                      let justifyClass = "justify-center";
                      if (colIndex === 0) {
                        justifyClass = "justify-start";
                        widthClass = "w-[97px]";
                      }
                      if (colIndex === columns.length - 1) {
                        justifyClass = "justify-end";
                        widthClass = "w-[79px]";
                      }
                      if (colIndex === Math.floor(columns.length / 2))
                        widthClass = "w-[90px]";

                      let roundedClass = "rounded-none";
                      if (colIndex === 0) roundedClass = "rounded-l-[5px]";
                      if (colIndex === columns.length - 1)
                        roundedClass = "rounded-r-[5px]";

                      return (
                        <TableCell
                          key={colIndex}
                          className={cn("py-[5px]", roundedClass)}
                        >
                          <div className={`flex items-center gap-2 ${justifyClass}`}>
                            {colIndex === 0 && (
                              <Skeleton className="h-[10px] w-[10px] rounded-[2px]" />
                            )}
                            <Skeleton
                              className={cn(
                                "h-[12px] rounded-l-[5px] bg-[#CDCED2]",
                                widthClass
                              )}
                            />
                          </div>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </>
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center py-10 text-gray-500"
                >
                  Не удалось найти информацию
                </TableCell>
              </TableRow>
            ) : (
              data.map((item) => {
                const rowId = item.id;
                const isSelected = selectedRows.includes(rowId);

                return (
                  <TableRow
                    key={rowId}
                    className={cn(
                      "transition-colors duration-150",
                      "hover:bg-[#E8E9EA] bg-[#F2F3F4]",
                      isSelected && "bg-[#F7F0FF] hover:bg-[#efe3fc]"
                    )}
                    onClick={(e) => {
                      if (
                        !(e.target as HTMLElement).closest(
                          "input[type='checkbox']"
                        )
                      ) {
                        toggleRow(rowId);
                      }
                    }}
                  >
                    {columns.map((col, index) => {
                      const value =
                        typeof col.accessor === "function"
                          ? col.accessor(item)
                          : (item[col.accessor as keyof T] as React.ReactNode);

                      const isFirst = index === 0;
                      const isLast = index === columns.length - 1;

                      return (
                        <TableCell
                          key={index}
                          className={cn(
                            "text-center py-[5px]",
                            isLast && "rounded-r-[5px] text-right",
                            isFirst && "rounded-l-[5px] text-left"
                          )}
                        >
                          {isFirst ? (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                checked={isSelected}
                                onCheckedChange={() => toggleRow(rowId)}
                                className="h-[10px] w-[10px] border-[#5A606D] border-[0.5px] rounded-[2px]"
                              />
                              {value}
                            </div>
                          ) : (
                            value
                          )}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* --- Пагинация (правильная) --- */}
      <div className="flex justify-center items-center text-[12px] h-[43px] gap-[15px]">
        <div className="flex items-center gap-[4px]">
          {/* Кнопка Назад */}
          <Button
            onClick={() => onPageChange(Math.max(page - 1, 1))}
            disabled={page === 1}
            className={cn(
              "bg-[#F2F3F4] w-[18px] h-[18px] rounded-[5px] shadow-none",
              page === 1 && "opacity-50 cursor-not-allowed"
            )}
          >
            <ArrowRight className="w-[8px] h-[8px] rotate-180" fill="black" />
          </Button>

          {/* Основная логика пагинации */}
          {(() => {
            const visiblePages = 9;
            const pages: (number | string)[] = [];

            if (totalPages <= visiblePages) {
              // Если страниц немного — показываем все
              for (let i = 1; i <= totalPages; i++) pages.push(i);
            } else {
              const half = Math.floor(visiblePages / 2);
              let start = page - half;
              let end = page + half;

              if (start < 1) {
                start = 1;
                end = visiblePages;
              } else if (end > totalPages) {
                end = totalPages;
                start = totalPages - visiblePages + 1;
              }

              if (start > 1) {
                pages.push(1);
                if (start > 2) pages.push("...");
              }

              for (let i = start; i <= end; i++) {
                pages.push(i);
              }

              if (end < totalPages) {
                if (end < totalPages - 1) pages.push("...");
                pages.push(totalPages);
              }
            }

            return pages.map((p, i) =>
              p === "..." ? (
                <span key={`ellipsis-${i}`} className="px-1 text-gray-500 select-none">
                  ...
                </span>
              ) : (
                <Button
                  key={`page-${p}`}
                  onClick={() => onPageChange(Number(p))}
                  className={cn(
                    "w-[18px] h-[18px] !p-0 min-w-[18px] min-h-[18px] rounded-[5px] text-[12px] font-light shadow-none",
                    page === p
                      ? "bg-[#F2F3F4] border-[#7700FF] border-[1px] text-black"
                      : "bg-[#F2F3F4] hover:bg-[#E8E9EA]"
                  )}
                >
                  {p}
                </Button>
              )
            );
          })()}

          {/* Кнопка Вперёд */}
          <Button
            onClick={() => onPageChange(Math.min(page + 1, totalPages))}
            disabled={page === totalPages}
            className={cn(
              "bg-[#F2F3F4] w-[18px] h-[18px] rounded-[5px] shadow-none",
              page === totalPages && "opacity-50 cursor-not-allowed"
            )}
          >
            <ArrowRight fill="black" className="w-[8px] h-[8px]" />
          </Button>
        </div>

        {/* Селект количества строк */}
        <Select
          value={String(rowsPerPage)}
          onValueChange={(value) => onRowsPerPageChange(Number(value))}
        >
          <SelectTrigger className="relative flex items-center justify-between w-auto !h-[18px] border-none rounded-[5px] bg-[#F2F3F4] text-[12px] pl-1 pr-1 focus:ring-0 shadow-none font-light">
            <SelectValue className="truncate" />
          </SelectTrigger>

          <SelectContent
            align="end"
            sideOffset={4}
            className="min-w-[75px] rounded-[5px] border border-gray-200 bg-white shadow-none text-[12px]"
          >
            {[20, 50, 100].map((num) => (
              <SelectItem
                key={num}
                value={String(num)}
                className="px-2 py-[3px] text-gray-800 cursor-pointer h-[18px]"
              >
                {num}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

    </div>
  );
}
