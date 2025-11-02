import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { AxiosError } from 'axios'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Header } from '@/components/ui/header'
import { Footer } from '@/components/ui/footer'
import { Spinner } from '@/components/ui/spinner'
import { useUserStore } from '@/store/useUserStore'
import api from '@/api/axios'

function AuthPage() {
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [rememberMe, setrememberMe] = useState(false)
	const [loading, setLoading] = useState(false)

	const navigate = useNavigate()
	const { setUser, setToken } = useUserStore()

	// если уже авторизован — редирект на /
	useEffect(() => {
		const token =
			localStorage.getItem('token') || sessionStorage.getItem('token')
		if (token) navigate('/')
	}, [navigate])

	const handleLogin = async () => {
		if (!email.trim() || !password.trim()) {
			toast.error('Введите email и пароль')
			return
		}

		setLoading(true)
		try {
			const { data } = await api.post('/auth/login', {
				email: email.trim(),
				password,
			})

			const { token, user } = data
			if (!token || !user) throw new Error('Некорректный ответ сервера')

			// сохраняем токен через Zustand
			setToken(token, rememberMe)

			// формируем имя пользователя корректно
			const [first_name, last_name = ''] = (user.name ?? '').split(' ')

			setUser({
				id: user.id,
				first_name,
				last_name,
				role: user.role,
				email: user.email,
			})

			toast.success('Вы успешно вошли в систему')
			navigate('/')
		} catch (error) {
			const err = error as AxiosError<{ error?: string }>
			console.error('Ошибка при логине:', err)
			const message =
				err.response?.data?.error || err.message || 'Произошла ошибка при входе'
			toast.error('Ошибка при входе', { description: message })
		} finally {
			setLoading(false)
		}
	}

	return (
		<div className='min-h-screen flex flex-col bg-[#F4F4F5] text-gray-900 font-rostelecom'>
			<Header />

			<main className='flex-1 flex flex-col items-center justify-center p-4 relative'>
				<div className='flex flex-col gap-[20px]'>
					<div className='w-[430px] h-[550px] bg-white rounded-[15px] overflow-hidden max-w-md p-8 flex flex-col items-center'>
						<form
							className='w-full flex flex-col gap-[20px]'
							autoComplete='on'
							onSubmit={e => {
								e.preventDefault()
								handleLogin()
							}}
						>
							<h1 className='text-2xl font-bold text-center mb-2'>
								Войти на склад
							</h1>

							<Input
								name='email'
								autoComplete='email'
								placeholder='Электронная почта'
								value={email}
								onChange={e => setEmail(e.target.value)}
								className='w-[365px] h-[68px] rounded-[10px] border-none bg-[#F2F3F4]
											placeholder-[#A1A1AA] placeholder:font-medium
											placeholder:text-[18px] shadow-none !text-[18px]
											!text-[#000000] !font-medium'
							/>

							<Input
								name='password'
								type='password'
								autoComplete='current-password'
								placeholder='Пароль'
								value={password}
								onChange={e => setPassword(e.target.value)}
								className='w-[365px] h-[68px] rounded-[10px] border-none bg-[#F2F3F4]
											placeholder-[#A1A1AA] placeholder:font-medium
											placeholder:text-[18px] shadow-none !text-[18px]
											!text-[#000000] !font-medium'
							/>

							<div className='flex items-center space-x-2'>
								<Checkbox
									checked={rememberMe}
									onCheckedChange={val => setrememberMe(Boolean(val))}
									className='cursor-pointer'
								/>
								<span className='text-[#000000] text-[16px] leading-[24px]'>
									Запомнить меня
								</span>
							</div>

							<Button
								disabled={!email || !password || loading}
								type='submit'
								className={`w-[365px] h-[68px] rounded-[10px] text-[18px]
											leading-[24px] ${
												!email || !password
													? 'bg-[#CECECE] text-[#FFFFFF] cursor-not-allowed'
													: 'bg-[#7700FF] text-[#FFFFFF]'
											}`}
							>
								{loading ? (
									<div className='flex items-center justify-center gap-2'>
										<Spinner className='size-5' /> загрузка...
									</div>
								) : (
									'Войти'
								)}
							</Button>

							<Button
								variant='outline'
								className='regis-button'
								type='button'
								disabled={true}
							>
								Зарегистрироваться
							</Button>

							<p className='text-[18px] leading-[24px] text-[#9699A3] text-center'>
								<span className='hover:underline cursor-pointer'>
									Забыли пароль?
								</span>
							</p>
						</form>
					</div>

					<div className='w-full h-[123px] bg-white rounded-[15px] overflow-hidden max-w-md relative'>
						<p className='absolute top-[10px] text-center w-full text-[18px] text-[#9699A3]'>
							Войти через
						</p>
						<div className='absolute top-[50px] flex items-center justify-center gap-[17px] w-full'>
							<Button className='login-add' disabled>
								Ростелеком ID
							</Button>

							<Button className='login-add' disabled>
								Код доступа
							</Button>
						</div>
					</div>
				</div>

				<Footer />
			</main>
		</div>
	)
}

export default AuthPage
