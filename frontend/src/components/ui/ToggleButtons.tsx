import { useState } from 'react'
import { Button } from '@/components/ui/button'

interface ToggleButtonsProps {
	onChange?: (value: 'robot' | 'product') => void
}

export function ToggleButtons({ onChange }: ToggleButtonsProps) {
	const [active, setActive] = useState<'robot' | 'product'>('robot')

	const handleClick = (value: 'robot' | 'product') => {
		setActive(value)
		onChange?.(value)
	}

	return (
		<div className='flex w-full justify-between gap-2'>
			<Button
				type='button'
				onClick={() => handleClick('robot')}
				className={`toggle-button ${
					active === 'robot' ? 'toggle-active' : 'toggle-inactive'
				}`}
			>
				Робот
			</Button>

			<Button
				type='button'
				onClick={() => handleClick('product')}
				className={`toggle-button ${
					active === 'product' ? 'toggle-active' : 'toggle-inactive'
				}`}
			>
				Товар
			</Button>
		</div>
	)
}

export default ToggleButtons
