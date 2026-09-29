import { Check } from "lucide-react";
import { Button } from "../ui/button";
import React from "react";

interface SingleSelectableButtonsProps {
  params: string[];
  multiple?: false;
  selected?: string | null;
  onSelect?: (value: string | null) => void;
}

interface MultiSelectableButtonsProps {
  params: string[];
  multiple: true;
  selected?: string[];
  onSelect?: (value: string[]) => void;
}

type SelectableButtonsProps = SingleSelectableButtonsProps | MultiSelectableButtonsProps;

const SelectableButtons: React.FC<SelectableButtonsProps> = ({
  params,
  selected,
  onSelect,
  multiple = false,
}) => {
  const isSelected = (param: string) => {
    if (multiple && Array.isArray(selected)) {
      return selected.includes(param);
    }
    return selected === param;
  };

  const handleToggle = (param: string) => {
    if (!onSelect) return;

    if (multiple) {
      const multiOnSelect = onSelect as (value: string[]) => void;
      const arr = Array.isArray(selected) ? selected : [];
      if (arr.includes(param)) {
        multiOnSelect(arr.filter((p) => p !== param));
      } else {
        multiOnSelect([...arr, param]);
      }
    } else {
      const singleOnSelect = onSelect as (value: string | null) => void;
      singleOnSelect(selected === param ? null : param);
    }
  };


  return (
    <div className="rounded-[5px] bg-[#F2F3F4] flex flex-col gap-[2px]">
      {params.map((param, index) => {
        const active = isSelected(param);
        return (
          <Button
            key={index}
            onClick={() => handleToggle(param)}
            className={`flex items-center justify-between w-[198px] h-[24px] text-[12px] font-medium cursor-pointer text-black rounded-[5px] shadow-none p-[2px] transition-all
              ${
                active
                  ? "border border-purple-600 bg-white"
                  : "border border-transparent bg-[#F2F3F4]"
              }`}
          >
            {param}
            {active && <Check className="w-3 h-3 mr-1 text-[#7700FF]" />}
          </Button>
        );
      })}
    </div>
  );
};

export default SelectableButtons;
