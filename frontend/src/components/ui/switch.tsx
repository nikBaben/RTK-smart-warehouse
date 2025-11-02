import * as React from "react"
import * as SwitchPrimitive from "@radix-ui/react-switch"

import { cn } from "@/lib/utils"

function Switch({
  className,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root>) {
  return (
    <SwitchPrimitive.Root
    data-slot="switch"
    className={cn(
        "peer inline-flex h-[1.5rem] w-[2.75rem] shrink-0 items-center rounded-full border border-transparent transition-all outline-none cursor-pointer data-[state=checked]:bg-[#7700FF] data-[state=unchecked]:bg-gray-300",
        className
    )}
    {...props}
    >
    <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className={cn(
        "block size-[16px] bg-white rounded-full transition-transform data-[state=checked]:translate-x-[calc(100%)] data-[state=unchecked]:translate-x-[2px]"
        
        )}
    />
    </SwitchPrimitive.Root>

  )
}

export { Switch }
