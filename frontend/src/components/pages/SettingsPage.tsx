import api from '@/api/axios.ts';
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { useUserStore } from '@/store/useUserStore'
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import ChevronDown from '@atomaro/icons/24/navigation/ChevronDown';
import { Switch } from "@/components/ui/switch";
import SignOut from '@atomaro/icons/24/navigation/SignOut';
import CheckLarge from '@atomaro/icons/24/navigation/CheckLarge';
import CloseLarge from '@atomaro/icons/24/navigation/CloseLarge';
import { Label } from '@/components/ui/label'
import { Notification } from "@/components/widgets/Notifications";
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select'

function SettingsPage(){
	const token = localStorage.getItem('token')
  
	/* const [showNotifications, setShowNotifications] = useState(false); */
	/* const [email, setEmail] = useState('') */
	const [loading, setLoading] = useState(false)
	/* const [error, setError] = useState<string | null>(null) */
	
	const { user, updateUser } = useUserStore()

	type EditableUser = {
		first_name: string
		last_name: string
		role: string
	}

	const [form, setForm] = useState({
		first_name: '',
		last_name: '',
		role: '',
	})

	useEffect(() => {
		if (user) {
			setForm({
				first_name: user.first_name || '',
				last_name: user.last_name || '',
				role: user.role || '',
			})
		}
	}, [user])

	const handleChange = (key: keyof EditableUser, value: string) => {
		setForm(prev => ({ ...prev, [key]: value }))
	}

  const handleSave = async () => {
		if (!user) return
		setLoading(true)

		try {
			const full_name = `${form.first_name} ${form.last_name}`.trim()

			const payload = {
				name: full_name,
				role: form.role,
			}

			const response = await api.put(`/user/${user.id}`,payload)

			const updated = response.data
			const [updatedFirstName, updatedLastName = ''] = updated.name.split(' ')

			updateUser({
				first_name: updatedFirstName,
				last_name: updatedLastName,
				role: updated.role,
			})

			toast.success('Изменения сохранены!')
		} catch (error) {
			console.error('Ошибка при сохранении:', error)
			toast.error('Не удалось сохранить изменения')
		} finally {
			setLoading(false)
		}
	}
	
	const handleReset = async () =>{
		setForm({
			first_name: user?.first_name || '',
			last_name: user?.last_name || '',
			role: user?.role || '',
		})
	}


  return (
		<div className='flex bg-[#F4F4F5] min-h-screen'>
			<div className='flex flex-col flex-1 ml-[60px]'>
				<header className='header-style'>
					<span className='page-name'>Параметры и уведомления</span>
				</header>
				<main className='flex-1 p-[9px]'>
					<div className='grid grid-cols-12 gap-3 justify-between'>
						<section className='flex flex-col col-span-6 gap-[10px]'>
							<div className='bg-white rounded-[15px] p-[10px] h-[70px] flex justify-between'>
								<div className='flex items-center gap-[10px]'>
									<Avatar className='h-12 w-12 bg-[#F7F0FF] border-1 border-[#7700FF]'>
										<AvatarImage src='' />
										<AvatarFallback>
											{user?.first_name?.charAt(0)}
											{user?.last_name?.charAt(0)}
										</AvatarFallback>
									</Avatar>
									<div className='flex flex-col text-black'>
										<span className='text-[18px] font-medium'>
											{user?.first_name} {user?.last_name}
										</span>
										<span className='text-[12px] font-light'>
											логин: {user?.email}
										</span>
									</div>
								</div>
								<span className='flex items-center'>
									{user?.role === 'operator'
										? 'оператор склада'
										: 'пользователь'}
								</span>
							</div>
							<div className='bg-white rounded-[15px] p-[10px] flex flex-col'>
								<h2 className='font-medium text-[24px] mb-[15px]'>
									Профиль и настройки
								</h2>
								<div className='flex flex-col gap-[15px]'>
									<div className='flex flex-col'>
										<Label className='section-title'>Имя</Label>
										<Input
											className='main-input !text-[16px]'
											id='first_name'
											name='first_name'
											value={form.first_name || ''}
											onChange={e => handleChange('first_name', e.target.value)}
										></Input>
									</div>
									<div className='flex flex-col'>
										<Label className='section-title'>Фамилия</Label>
										<Input
											className='main-input !text-[16px]'
											id='last_name'
											name='last_name'
											value={form.last_name}
											onChange={e => handleChange('last_name', e.target.value)}
										></Input>
									</div>
									<div className='flex flex-col'>
										<Label className='section-title'>Логин</Label>
										<Label className='input-description'>
											Укажите свою почту, чтобы мы могли Вас идентифицировать
										</Label>
										<Input
											className='main-input !text-[16px]'
											id='login'
											name='login'
											placeholder='voenmeh@gmail.com'
											value={user?.email}
										/>
									</div>
									<div className='flex flex-col'>
										<Label className='section-title'>Роль</Label>
										<Label className='input-description'>
											Роль определяет уровень ваших прав на сайте
										</Label>
										<Select
											value={form.role}
											onValueChange={value => handleChange('role', value)}
										>
											<SelectTrigger className='w-full !h-[52px]'>
												<SelectValue defaultValue={form.role} />
											</SelectTrigger>
											<SelectContent>
												<SelectItem value='operator'>Оператор</SelectItem>
												<SelectItem value='user'>
													Пользователь склада
												</SelectItem>
											</SelectContent>
										</Select>
									</div>
									<div className='flex gap-[10px]'>
										<Button className='flex-1 h-[40px] bg-white border-[2px] border-[#FF4F12] text-[#FF4F12] text-[18px] rounded-[10px]'>
											<SignOut
												fill='#FF4F12'
												className='h-[14px] w-auto'
											></SignOut>
											Выйти
										</Button>
										<Button
											className='flex-1 h-[40px] bg-white border-[2px] border-[#5A606D] text-[#5A606D] text-[18px] rounded-[10px]'
											onClick={handleReset}
										>
											<CloseLarge
												fill='#5A606D'
												className='h-[14px] w-auto'
											></CloseLarge>
											Отменить
										</Button>
										<Button
											onClick={handleSave}
											className='flex-1 h-[40px] bg-white border-[2px] border-[#7700FF] text-[#7700FF] text-[18px] rounded-[10px]'
										>
											<CheckLarge
												fill='#7700FF'
												className='h-[14px] w-auto'
											></CheckLarge>
											Сохранить
										</Button>
									</div>
								</div>
							</div>
							<div className='flex items-center justify-center pt-[8px]'>
								<img
									src='/src/assets/images/warehouse-img 1.svg'
									alt='Warehouse'
									className='w-[480px] h-[320px]'
								/>
							</div>
						</section>
						<section className='flex flex-col col-span-6'>
							<div className='bg-white rounded-[15px] p-[6px] pl-[12px] justify-between h-[920px]'>
								<div className='flex flex-col p-[10px]'>
									<h2 className='text-[24px] font-medium text-black mb-[10px]'>
										Уведомления
									</h2>
									<Notification />
								</div>
							</div>
						</section>
					</div>
				</main>
			</div>
		</div>
	)
}

export default SettingsPage;