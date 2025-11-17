"use client"

import * as React from "react"
import { format } from "date-fns"
import ChevronDown from '@atomaro/icons/24/navigation/ChevronDown';
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface DatePickerProps {
  startDate?: Date
  endDate?: Date
  onChange?: (start: Date | undefined, end: Date | undefined) => void
}

export function DatePicker({ startDate, endDate, onChange }: DatePickerProps) {
  return (
    <div className="flex gap-2">
      {/* START DATE */}
      <Popover>
        <PopoverTrigger asChild>
          <Button
            data-empty={!startDate}
            variant="ghost"
            className="cursor-pointer data-[empty=true]:text-[12px] w-[96px] h-[24px] justify-between text-left font-light bg-[#F2F3F4] shadow-none text-[#9699A3] px-[5px]"
          >
            {startDate ? format(startDate, "dd.MM.yyyy") : "от"}
            <ChevronDown fill="#9699A3" className="w-3 h-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-auto p-2 shadow-md rounded-md border bg-white">
          <Calendar
            mode="single"
            selected={startDate}
            onSelect={(date) => onChange?.(date, endDate)}
            disabled={(date) => endDate ? date > endDate : false}
            className="
              rounded-md text-[11px]
              [&_.rdp-day]:w-7 [&_.rdp-day]:h-7 [&_.rdp-day]:text-[11px]
              [&_.rdp-head_cell]:text-[10px]
            "
          />
        </PopoverContent>
      </Popover>

      {/* END DATE */}
      <Popover>
        <PopoverTrigger asChild>
          <Button
            data-empty={!endDate}
            variant="ghost"
            className="cursor-pointer data-[empty=true]:text-[12px] w-[96px] h-[24px] justify-between text-left font-light bg-[#F2F3F4] shadow-none text-[#9699A3] px-[5px]"
          >
            {endDate ? format(endDate, "dd.MM.yyyy") : "до"}
            <ChevronDown fill="#9699A3" className="w-3 h-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-auto p-2 shadow-md rounded-md border bg-white">
          <Calendar
            mode="single"
            selected={endDate}
            onSelect={(date) => onChange?.(startDate, date)}
            disabled={(date) => startDate ? date < startDate : false}
            className="
              rounded-md text-[11px]
              [&_.rdp-day]:w-7 [&_.rdp-day]:h-7 [&_.rdp-day]:text-[11px]
              [&_.rdp-head_cell]:text-[10px]
            "
          />
        </PopoverContent>
      </Popover>
    </div>
  )
}
