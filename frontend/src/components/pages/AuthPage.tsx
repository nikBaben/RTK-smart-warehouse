import api from '@/api/axios'
import { AxiosError } from 'axios'
import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { useNavigate } from 'react-router-dom'
import { Header } from '@/components/ui/header'
import { Footer } from '@/components/ui/footer'
import { toast } from 'sonner'
import { useUserStore } from '@/store/useUserStore'
import { Spinner } from '@/components/ui/spinner'

/* type User = {
	id: number,
	name: string,
	role: string,
} */

function AuthPage() {
	const [email, setEmail] = useState('')
	const [password, setPassword] = useState('')
	const [loading, setLoading] = useState(false)

	const navigate = useNavigate()
	const setUser = useUserStore(state => state.setUser)
	useEffect(()=>{
		setEmail('')
		setPassword('')
	},[])
	const handleLogin = async () => {
		if (!email?.trim() || !password) {
			toast.error('Введите email и пароль')
			return
		}

		setLoading(true)
		const payload = { email: email?.trim(), password }
		try {
			const response = await api.post('/auth/login',payload)
			localStorage.setItem('token', response.data.token)
			const userData = response.data.user
			const [first_name, last_name = ''] = userData.name.split(' ')

			setUser({
				id: userData.id,
				first_name,
				last_name,
				role: userData.role,
				email: userData.email,
			})
			console.log(userData)
			navigate('/')
		} catch (error) {
			const err = error as AxiosError<{ error?: string }>
			console.error('Ошибка при логине:', err)
			console.log('➡️ err.response:', err.response)
			console.log('➡️ err.request:', err.request)
			console.log('➡️ err.message:', err.message)
			const message = err.response?.data?.error || 'Неизвестная ошибка'

			if (err.response) {
				toast.error('Ошибка при входе в аккаунт', {
					description: message,
				})
			} else {
				alert('Ошибка входа: Сервер недоступен или нет ответа')
			}
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
							className='w-full m-[20px] h-[68px] flex flex-col gap-[20px]'
							autoComplete='on'
							onSubmit={e => {
								e.preventDefault() // <-- обязательно, чтобы форма не отправлялась как GET
								handleLogin()
							}}
						>
							<h1 className='text-2xl font-bold flex flex-col items-center justify-center'>
								Войти на склад
							</h1>
							<div className='flex flex-col items-center justify-center'>
								<Input
									name='email'
									autoComplete='email'
									placeholder='Электронная почта'
									value={email}
									onChange={e => setEmail(e.target.value)}
									className='w-[365px] h-[68px] rounded-[10px] border-none bg-[#F2F3F4] placeholder-[#A1A1AA] placeholder:font-medium placeholder:text-[18px] placeholder:leading-[24px] shadow-none !text-[18px] !leading-[24px] !text-[#000000] !font-medium'
								/>
							</div>
							<div className='flex flex-col gap-[20px]'>
								<div className='flex flex-col items-center justify-center'>
									<Input
										name='password'
										type='password'
										autoComplete='password'
										placeholder='Пароль'
										value={password}
										onChange={e => setPassword(e.target.value)}
										className='w-[365px] h-[68px] rounded-[10px] border-none bg-[#F2F3F4] placeholder-[#A1A1AA] placeholder:font-medium placeholder:text-[18px] placeholder:leading-[24px] shadow-none !text-[18px] !leading-[24px] !text-[#000000] !font-medium'
									/>
								</div>
								<div className='flex items-center space-x-2'>
									<Checkbox
										className={`
                        cursor-pointer
                        shadow-none
                        peer
                        w-5 h-5 border-1 rounded-[5px]
                        bg-[#F2F3F4] border-[#F2F3F4]
                        data-[state=checked]:bg-[#F2F3F4]
                        data-[state=checked]:text-[#7700FF]
                        data-[state=checked]:border-[#7700FF]
                        transition-colors duration-200
                        flex items-center justify-center`}
									/>
									<span className='text-[#000000] text-[16px] leading-[24px]'>
										Запомнить меня
									</span>
								</div>
							</div>
							<div className='flex flex-col items-center justify-center'>
								<Button
									disabled={!email || !password}
									type='submit'
									className={`${loading && 'button-loading'}
									w-[365px] cursor-pointer h-[68px] rounded-[10px] text-[18px] leading-[24px] shadow-none ${
										!email || !password
											? 'bg-[#CECECE] text-[#FFFFFF] cursor-not-allowed'
											: 'bg-[#7700FF] text-[#FFFFFF]'
									}`}
								>
									{loading ? (
										<div className='spinner-load-container !text-white'>
											<Spinner className='size-5 m-1' /> загрузка...
										</div>
									) : (
										'Войти'
									)}
								</Button>
							</div>
							<div className='flex flex-col items-center justify-center'>
								<Button
									variant='outline'
									className='cursor-pointer w-[365px] h-[68px] rounded-[10px] text-[18px] leading-[24px] text-[#7700FF] border-none bg-[#F7F0FF] shadow-none'
								>
									Зарегистрироваться
								</Button>
							</div>
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
							<Button
								className='w-[174px] h-[50px] px-[56px] py-[5px] rounded-[10px] text-[18px] flex items-center justify-center hover:opacity-90 bg-[#FFF1EC] text-[#FF4F12] shadow-none'
								disabled
							>
								Ростелеком ID
							</Button>

							<Button className='cursor-pointer w-[174px] h-[50px] px-[56px] py-[5px] rounded-[10px] text-[18px] flex items-center justify-center hover:opacity-90 bg-[#FFF1EC] text-[#FF4F12] shadow-none'>
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
