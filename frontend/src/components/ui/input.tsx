import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
			<input
				type={type}
				className={cn(
					'flex border-2 border-transparent focus:border-[#7700FF] focus:ring-0 transition-all h-9 w-full placeholder:text-[#7700FF] rounded-[10px] bg-[#F2F3F4] px-3 py-1 text-base transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground outline-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm',
					className
				)}
				ref={ref}
				{...props}
			/>
		)
  }
)
Input.displayName = "Input"

export { Input }
