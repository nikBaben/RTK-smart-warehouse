import { motion } from 'framer-motion'
import { Header } from '@/components/ui/header'
import { Footer } from '@/components/ui/footer'
import { useNavigate } from 'react-router-dom'

function ServerErrorPage() {
	const navigate = useNavigate()
	return (
		<div className='min-h-screen flex flex-col bg-[#F4F4F5] text-gray-900 font-rostelecom'>
			<Header />
			<motion.div
				initial={{ opacity: 0, y: 20 }}
				animate={{ opacity: 1, y: 0 }}
				className='flex flex-col items-center justify-center h-[80vh] text-center'
			>
				<div className='relative space-y-[-80px]'>
					<h1 className='select-none font-bold text-[#7700FF] text-[300px] relative z-10'>
						500
					</h1>
					<h1 className='select-none font-bold text-[#FF4F12] text-[300px] absolute top-3 left-3 z-0'>
						500
					</h1>
				</div>
				<div className='flex flex-col gap-[-20px]'>
					<h2 className='text-[#9699A3] text-[30px] mb-0'>
						внутренняя ошибка сервера
					</h2>
					<p className='text-[#9699A3] text-[25px]'>
						что-то пошло не так. мы уже работаем над исправлением
					</p>
					<a onClick={() => navigate('/')} className='mainpage-ref-error mb-8'>
						на главную
					</a>
				</div>
			</motion.div>
			<Footer />
		</div>
	)
}
export default ServerErrorPage
