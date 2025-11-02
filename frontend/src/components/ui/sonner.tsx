import { useTheme } from 'next-themes'
import { Toaster as Sonner } from 'sonner'

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
	const { theme = 'system' } = useTheme()

	return (
		<Sonner
			theme={theme as ToasterProps['theme']}
			position='top-right'
			toastOptions={{
				classNames: {
					toast: `
            group toast
            !rounded-[10px] !font-rostelecom !text-[14px]
            shadow-lg border border-transparent transition-all duration-200
            data-[type=success]:!bg-[#0ACB5B] data-[type=success]:!text-white
            data-[type=error]:!bg-[#D92020] data-[type=error]:!text-white
            data-[type=info]:bg-[#F4F4F5] data-[type=info]:text-[#5A606D]
            data-[type=warning]:bg-[#FFF4E5] data-[type=warning]:text-[#7A4100]
          `,
					description: 'opacity-80',
					actionButton:
						'bg-[#7700FF] text-white rounded-md px-3 py-1 hover:brightness-90 transition-all',
				},
			}}
			{...props}
		/>
	)
}

export { Toaster }
