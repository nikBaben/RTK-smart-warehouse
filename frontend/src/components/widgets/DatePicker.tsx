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
    <div className="flex gap-[6px]">
      <Popover>
        <PopoverTrigger asChild>
          <Button
            data-empty={!startDate}
            className="cursor-pointer data-[empty=true]:text-[12px] w-[96px] h-[24px] justify-between text-left font-light bg-[#F2F3F4] shadow-none text-[#9699A3] px-[5px]"
          >
            {startDate ? format(startDate, "dd.MM.yyyy") : "от"}
            <ChevronDown fill="#9699A3" className="w-[7px] h-[3px]"/>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0">
          <Calendar 
            mode="single" 
            selected={startDate} 
            onSelect={(date) => onChange?.(date, endDate)} 
            className="w-[150px] h-auto [--cell-size:18px] !bg-white rounded-[5px] !shadow-none !text-[10px] border-[#7700FF]"
          />
        </PopoverContent>
      </Popover>

      <Popover>
        <PopoverTrigger asChild>
          <Button
            data-empty={!endDate}
            className="cursor-pointer data-[empty=true]:text-[12px] w-[96px] h-[24px] justify-between text-left font-light bg-[#F2F3F4] shadow-none text-[#9699A3] px-[5px]"
          >
            {endDate ? format(endDate, "dd.MM.yyyy") : "до"}
            <ChevronDown fill="#9699A3" className="w-[7px] h-[3px]"/>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0">
          <Calendar
            mode="single"
            selected={endDate}
            onSelect={(date) => onChange?.(startDate, date)}
            disabled={(date) => startDate ? date < startDate : false}
            className="w-[150px] h-auto [--cell-size:18px] !bg-white rounded-[5px] !shadow-none border-[#7700FF]"
          />
        </PopoverContent>
      </Popover>
    </div>
  )
}
