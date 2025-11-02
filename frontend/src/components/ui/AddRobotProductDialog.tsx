import api from '@/api/axios.ts'
import { useState } from 'react'
import {
	Dialog,
	DialogClose,
	DialogContent,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from '@/components/ui/dialog'
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select'
import { X } from 'lucide-react'
import { Check } from 'lucide-react'
import AddLarge from '@atomaro/icons/24/action/AddLarge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { useUserStore } from '@/store/useUserStore'
import { useWarehouseStore } from '@/store/useWarehouseStore'
import { ToggleButtons } from './ToggleButtons.tsx'

export function AddRobotProductDialog() {
  const token = localStorage.getItem('token')
	const [open, setOpen] = useState(false)
	const [formData, setFormData] = useState({
		name: '',
		article: '',
		category: '',
		stock: '',
		current_row: '',
		current_shelf: '',
		current_position: '',
	})

	const { user } = useUserStore()
	const [ loading, setLoading ] = useState(false)
  const { selectedWarehouse } = useWarehouseStore()
	const [mode, setMode] = useState<'robot' | 'product'>('robot')
	
  let denyAdminAccess = !(user?.role === 'operator')

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const { name, value } = e.target
		setFormData(prev => ({ ...prev, [name]: value }))
	}
	const handleCategoryChange = (value: string) => {
		setFormData(prev => ({ ...prev, category: value }))
	}

	const handleAddRobot = async (e: React.FormEvent) => {
		e.preventDefault()
		setLoading(true)
		if (!selectedWarehouse)
			return alert('Выберите склад для добавления робота.')
		try {
			const payload = {
				warehouse_id: selectedWarehouse.id,
			}
			const response = await api.post('/robot', payload)
			setOpen(false)
			console.log('Робот успешно добавлен:', response.data)
			toast.success(`Робот успешно добавлен на склад ${selectedWarehouse.name}`)
		} catch (error) {
			console.error('Ошибка при добавлении робота:', error)
			alert('Не удалось добавить робота')
		} finally {
			setLoading(false)
		}
	}

	const handleAddProduct = async (e: React.FormEvent) => {
		e.preventDefault()
		setLoading(true)
		if (!selectedWarehouse) {
			alert('Сначала выберите склад')
			return
		}
		try {
			const [rowPos, shelfPos] = formData.current_position.split(',').map(s => s.trim())
			const payload = {
				name: formData.name,
				article: formData.article,
				category: formData.category,
				stock: Number(formData.stock),
				current_row: Number(rowPos),
				current_shelf: shelfPos,
				warehouse_id: selectedWarehouse.id,
			}
      console.log(payload)
			const response = await api.post('/products', payload)
			setOpen(false)
			
			console.log('Товар добавлен:', response.data)
			toast.success('Товар успешно добавлен!')
			//очистка формы
			setFormData({
				name: '',
				article: '',
				category: '',
				stock: '',
				current_row: '',
				current_shelf: '',
				current_position: '',
			})
		} catch (error) {
			console.error('Ошибка при добавлении товара:', error)
			toast.error('Не удалось добавить товар')
		} finally {
			setLoading(false)
		}
	}

	return (
		<Dialog open={open} onOpenChange={setOpen}>
			<DialogTrigger asChild>
				<Button
					className='add-warehouse-button'
					disabled={denyAdminAccess}
					onClick={() => {
						setOpen(true)
						setMode('robot')
					}}
				>
					Добавить робота или товар
					<AddLarge fill='#7700FF' className='!w-[20px] !h-[20px]' />
				</Button>
			</DialogTrigger>
			<DialogContent className='bg-[#F4F4F5] !p-[20px] !w-[558px]'>
				<DialogHeader>
					<DialogTitle className='dialog-title-text'>
						Добавление робота или товара
					</DialogTitle>
				</DialogHeader>
				<div className='grid gap-3'>
					<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
						<Label className='section-title' htmlFor='name'>
							Что вы хотите добавить?
						</Label>
						<ToggleButtons onChange={setMode} />
					</div>
					{mode === 'robot' ? (
						<form onSubmit={handleAddRobot}>
							<div className='min-h-[20px]'></div>
							<DialogFooter>
								<DialogClose asChild>
									<Button className='cancel-button'>
										<X className='!h-5 !w-5' />
										Отмена
									</Button>
								</DialogClose>
								<Button
									type='submit'
									className='w-[50%] rounded-[10px] text-[18px] text-white font-medium bg-[#7700FF] cursor-pointer transition-all hover:brightness-90'
									disabled={loading}
								>
									<Check className='!h-5 !w-5' />
									{loading ? 'Добавление...' : 'Подтвердить'}
								</Button>
							</DialogFooter>
						</form>
					) : (
						<form onSubmit={handleAddProduct}>
							<div className='grid gap-3 pb-3'>
								<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
									<Label className='section-title' htmlFor='name'>
										Укажите название вашего товара
									</Label>
									<Input
										className='dialog-input-placeholder-text'
										id='name'
										name='name'
										value={formData.name}
										onChange={handleChange}
										placeholder='Например, Apple IPhone 17'
										required
									/>
								</div>
								<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
									<Label className='section-title' htmlFor='address'>
										Введите артикул товара
									</Label>
									<Input
										className='dialog-input-placeholder-text'
										id='article'
										name='article'
										value={formData.article}
										onChange={handleChange}
										placeholder='Например, 9573420'
										required
									/>
								</div>
								<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
									<Label className='section-title' htmlFor='stock'>
										Количество единиц товара (шт)
									</Label>
									<Input
										className='dialog-input-placeholder-text'
										id='stock'
										name='stock'
										value={formData.stock}
										onChange={handleChange}
										placeholder='100'
										required
									/>
								</div>
								<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
									<Label className='section-title' htmlFor='stock'>
										Категория товара
									</Label>
									<Select onValueChange={handleCategoryChange}>
										<SelectTrigger className='w-full'>
											<SelectValue placeholder='Выберите категорию' />
										</SelectTrigger>
										<SelectContent>
											<SelectItem value='Смартфоны'>Смартфоны</SelectItem>
											<SelectItem value='Бытовая техника'>
												Бытовая техника
											</SelectItem>
											<SelectItem value='Комплектующие'>
												Комплектующие
											</SelectItem>
										</SelectContent>
									</Select>
								</div>
								<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
									<Label className='section-title' htmlFor='current_position'>
										Где расположен товар?
									</Label>
									<Input
										className='dialog-input-placeholder-text'
										id='current_position'
										name='current_position'
										value={formData.current_position}
										onChange={handleChange}
										placeholder='Координаты сектора, в формате 1-50, A-Z'
										required
									/>
								</div>
								<DialogFooter>
									<DialogClose asChild>
										<Button className='cancel-button'>
											<X className='!h-5 !w-5' />
											Отмена
										</Button>
									</DialogClose>
									<Button
										type='submit'
										className='bg-[#7700FF] exit-dialog-buttons'
										disabled={loading}
									>
										<Check className='!h-5 !w-5' />
										{loading ? 'Добавление...' : 'Подтвердить'}
									</Button>
								</DialogFooter>
							</div>
						</form>
					)}
				</div>
			</DialogContent>
		</Dialog>
	)
}
export default AddRobotProductDialog
