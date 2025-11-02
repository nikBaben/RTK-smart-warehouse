import { useNavigate } from 'react-router-dom'
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar'
import { useUserStore } from '@/store/useUserStore'
export function UserAvatar() {
	const navigate = useNavigate()
	const { user } = useUserStore()

	return (
		<div
			onClick={() => navigate('/settings')}
			className='cursor-pointer'
			title='Настройки профиля'
		>
			<Avatar className='h-10 w-10 border-2 shadow border-[#CCCCCC] transition-all hover:border-[#7700FF]'>
				<AvatarImage src='' />
				<AvatarFallback className='text-[#7700FF]'>
					{user?.first_name?.charAt(0)}
					{user?.last_name?.charAt(0)}
				</AvatarFallback>
			</Avatar>
		</div>
	)
}

export default UserAvatar
