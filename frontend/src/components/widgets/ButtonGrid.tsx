import type { Dispatch, SetStateAction } from "react";
import { Button } from "../ui/button";

interface ButtonGridProps {
  selected: string[];
  onChange: Dispatch<SetStateAction<string[]>>;
}

export function ButtonGrid({ selected, onChange }: ButtonGridProps) {
  const buttons = [
    { key: "today", label: "Сегодня" },
    { key: "yesterday", label: "Вчера" },
    { key: "week", label: "Неделя" },
    { key: "month", label: "Месяц" },
  ];

  const toggleButton = (key: string) => {
    onChange(prev =>
      prev.includes(key)
        ? prev.filter(k => k !== key)
        : [...prev, key]
    );
  };

  return (
    <div className="grid grid-cols-2 gap-x-[6px] gap-y-[3px]">
      {buttons.map(({ key, label }) => (
        <Button
          key={key}
          onClick={() => toggleButton(key)}
          className={`h-[24px] w-[96px] text-[12px] font-medium cursor-pointer
                      ${selected.includes(key) ? "border-[1px] border-[#7700FF]" : "border-none"} 
                      bg-[#F2F3F4] text-black shadow-none`}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}