import api from '@/api/axios'
import { useEffect, useState } from 'react'
import { useUserStore } from '@/store/useUserStore'
import { useWarehouseStore } from '@/store/useWarehouseStore'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { Warehouse } from '../types/warehouse.ts'
import AddSmall from '@atomaro/icons/24/action/AddSmall'
import { UserAvatar } from '../ui/UserAvatar.tsx'
import { AddWarehouseDialog } from '../ui/AddWarehouseDialog.tsx'
import { Check } from 'lucide-react'
import { toast } from 'sonner'
import { WarehouseList } from '../warehouses/WarehousesList.tsx'
import { Skeleton } from '@/components/ui/skeleton'
import type { Robot } from '@/components/types/robot.ts'
import type { Product } from '@/components/types/product.ts'
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select'
import { X } from 'lucide-react'
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
	ContextMenu,
	ContextMenuContent,
	ContextMenuItem,
	ContextMenuTrigger,
} from '@/components/ui/context-menu'


function ListPage() {
	const token = localStorage.getItem('token')
	//-----ОБРАБОТКА СОСТОЯНИЙ-----
	const { user } = useUserStore()

	const [openAdd, setOpenAdd] = useState(false)
	const [openEdit, setOpenEdit] = useState(false)
	const [contextRobot, setContextRobot] = useState<Robot | null>(null)
	const [contextProduct, setContextProduct] = useState<Robot | null>(null)

	const {
		warehouses,
		loading,
		error,
		fetchWarehouses,
		selectedWarehouse,
		setSelectedWarehouse,
		updateWarehouse,
		deleteWarehouse,
	} = useWarehouseStore()

	const [editedWarehouse, setEditedWarehouse] = useState({
		name: '',
		address: '',
		max_products: 0,
	})

	const [editedProduct, setEditedProduct] = useState<Product | null>(null)
	const [products, setProducts] = useState<Product[]>([])

	const [robots, setRobots] = useState<Robot[]>([])

	const [formData, setFormData] = useState({
		name: '',
		article: '',
		category: '',
		stock: '',
		current_row: '',
		current_shelf: '',
		current_position: '',
	})

	const getRobotStatus = (status: string) => {
		switch (status) {
			case 'idle':
				return 'активен'
			case 'scanning':
				return 'сканирует'
			case 'charging':
				return 'зарядка'
			default:
				return 'неизвестен'
		}
	}

	const getStatusName = (status: string) => {
		switch (status) {
			case 'ok':
				return 'ОК'
			case 'low':
				return 'низкий остаток'
			case 'critical':
				return 'критично'
			default:
				return 'неизвестен'
		}
	}

	const [loadingInfo, setLoadingInfo] = useState(false)
	const [contextWarehouse, setContextWarehouse] = useState<Warehouse>()
	/* 	const [error, setError] = useState<string | null>(null) */

	let denyAdminAccess = !(user?.role === 'operator')
	useEffect(() => {
		fetchWarehouses()
		setSelectedWarehouse(null)
	}, [fetchWarehouses])

	/* 	useEffect(() => {
		if (!token) {
			console.warn('Токен отсутствует — пользователь не авторизован')
			alert('Токен отсутствует — пользователь не авторизован')
			return
		}
		fetchWarehouses(token)
		setSelectedWarehouse(null)
	}, [token]) */

	//-----СИНХРОНИЗАЦИЯ ДАННЫХ ПРИ ВЫБОРЕ СКЛАДА-----
	useEffect(() => {
		if (selectedWarehouse) {
			setEditedWarehouse({
				name: selectedWarehouse.name,
				address: selectedWarehouse.address,
				max_products: selectedWarehouse.max_products,
			})
		}
	}, [selectedWarehouse])

	//-----ВЫБОР СКЛАДА-----
	const handleSelectWarehouse = async (warehouse: Warehouse) => {
		setLoadingInfo(true)

		if (selectedWarehouse?.id === warehouse.id) {
			setSelectedWarehouse(null)
			setRobots([])
			setProducts([])
			return
		}

		setSelectedWarehouse(warehouse)
		setRobots([])
		setProducts([])

		try {
			const [robotsRes, productsRes] = await Promise.all([
				api.get(`/robot/get_robots_by_warehouse_id/${warehouse.id}`),
				api.get(`/products/get_products_by_warehouse_id/${warehouse.id}`),
			])
			setRobots(robotsRes.data)
			setProducts(productsRes.data)
		} catch (err) {
			console.error('Ошибка при загрузке данных склада:', err)
			toast.error('Не удалось получить данные склада')
		} finally {
			setLoadingInfo(false)
		}
	}

	//-----ДОБАВЛЕНИЕ РОБОТА-----
	const handleAddRobot = async () => {
		setLoadingInfo(true)
		if (!selectedWarehouse)
			return alert('Выберите склад для добавления робота.')
		try {
			const payload = {
				warehouse_id: selectedWarehouse.id,
			}

			const response = await api.post('/robot', payload)

			console.log('Робот успешно добавлен:', response.data)
			toast.success(`Робот успешно добавлен на склад ${selectedWarehouse.name}`)

			// обновляем список роботов для текущего склада
			fetchRobots()
		} catch (error) {
			console.error('Ошибка при добавлении робота:', error)
			alert('Не удалось добавить робота')
			setLoadingInfo(false)
		}
	}
	//-----РЕДАКТИРОВАНИЕ СКЛАДА-----
	const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const { name, value } = e.target
		setEditedWarehouse(prev => ({ ...prev, [name]: value }))
	}

	const handleSave = async (field: 'name' | 'address' | 'max_products') => {
		if (!selectedWarehouse) return

		try {
			const updatedData = {
				...selectedWarehouse,
				[field]: editedWarehouse[field],
			}

			const response = await api.patch(
				`/warehouse/${selectedWarehouse.id}`,
				updatedData,
				{ headers: { 'Content-Type': 'application/json' } }
			)

			updateWarehouse(response.data)
			console.log('Обновлено:', response.data)
			toast.success('Данные склада успешно обновлены!')

			// Обновляем выбранный склад
			/* setSelectedWarehouse(response.data) */
		} catch (error) {
			console.error('Ошибка при обновлении склада:', error)
			toast.error('Не удалось сохранить изменения')
		}
	}

	//-----ДОБАВЛЕНИЕ ТОВАРА-----
	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const { name, value } = e.target
		setFormData(prev => ({ ...prev, [name]: value }))
	}
	const handleCategoryChange = (value: string) => {
		setFormData(prev => ({ ...prev, category: value }))
	}

	const handleAddProduct = async (e: React.FormEvent) => {
		e.preventDefault()

		if (!selectedWarehouse) {
			alert('Сначала выберите склад')
			return
		}
		setLoadingInfo(true)
		try {
			const [rowPos, shelfPos] = formData.current_position
				.split(',')
				.map(s => s.trim())
			const payload = {
				name: formData.name,
				article: formData.article,
				category: formData.category,
				stock: Number(formData.stock),
				current_row: Number(rowPos),
				current_shelf: shelfPos,
				warehouse_id: selectedWarehouse.id,
			}

			const response = await api.post('/products', payload)

			console.log('Товар добавлен:', response.data)
			toast.success('Товар успешно добавлен!')

			//обновляем список товаров текущего склада
			fetchProducts()
			setOpenAdd(false)

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
			setLoadingInfo(false)
		}
	}

	//-----РЕДАКТИРОВАНИЕ ТОВАРА-----
	const handleProductEditChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		const { name, value } = e.target
		setEditedProduct(prev => {
			if (!prev) return prev
			// если редактируется позиция
			if (name === 'current_position') {
				const [row, shelf] = value.split(',').map(s => s.trim())
				return { ...prev, current_row: Number(row), current_shelf: shelf }
			}
			return { ...prev, [name]: value }
		})
	}

	const handleOpenProduct = (product: Product) => {
		setEditedProduct(product)
		setOpenEdit(true)
	}

	const handleUpdateProduct = async (e: React.FormEvent) => {
		e.preventDefault()
		if (!selectedWarehouse || !editedProduct) return

		try {
			const payload = {
				name: editedProduct.name,
				article: editedProduct.article,
				category: editedProduct.category,
				stock: Number(editedProduct.stock),
				current_row: editedProduct.current_row,
				current_shelf: editedProduct.current_shelf,
				warehouse_id: selectedWarehouse.id,
			}

			await api.patch(`/products/${editedProduct.id}`, payload)
			toast.success('Изменения успешно сохранены!')
			const updatedProducts = await api.get(
				`/products/get_products_by_warehouse_id/${selectedWarehouse.id}`
			)
			setProducts(updatedProducts.data)
			setOpenEdit(false)
		} catch (error) {
			console.error('Ошибка при обновлении товара:', error)
			toast.error('Не удалось обновить товар')
		}
	}

	//-----СПИСОК 	РОБОТОВ-----
	const fetchRobots = async () => {
		setLoadingInfo(true)
		if (!selectedWarehouse) {
			toast.warning('Сначала выберите склад')
			return
		}
		try {
			const robotsResponse = await api.get(
				`/robot/get_robots_by_warehouse_id/${selectedWarehouse.id}`
			)
			setRobots(robotsResponse.data)
			toast.success('Список роботов обновлен')
		} catch (err) {
			console.error(err)
			toast.error('Ошибка при загрузке списка роботов')
		} finally {
			setLoadingInfo(false)
		}
	}

	//-----СПИСОК ТОВАРОВ-----
	const fetchProducts = async () => {
		setLoadingInfo(true)
		if (!selectedWarehouse) {
			toast.warning('Сначала выберите склад')
			return
		}
		try{
			const productsResponse = await api.get(
				`/products/get_products_by_warehouse_id/${selectedWarehouse.id}`
			)
			setProducts(productsResponse.data)
			toast.success('Список товаров обновлен')
		} catch (err) {
			console.error(err)
			toast.error('Ошибка при загрузке списка товаров')
		} finally {
			setLoadingInfo(false)
		}
	}

	//-----УДАЛЕНИЕ РОБОТА-----
	const handleDeleteRobot = async (robot: Robot) => {
		if (
			!confirm(
				`Вы действительно хотите удалить робота "${robot.id}"? Данное действие невозможно отменить`
			)
		)
			return
		setLoadingInfo(true)
		try {
			await api.delete(`/robot/${robot.id}`)
			setContextRobot(null)
			toast.success(`Робот ${robot.id} успешно удалён`)
			//обновляем список роботов
			await fetchRobots()
		} catch (err) {
			console.error(err)
			toast.error(`Не удалось удалить робота ${robot.id}`)
		} finally{
			setLoadingInfo(false)
		}
	}

	//-----УДАЛЕНИЕ ТОВАРА-----
	const handleDeleteProduct = async (product: Product) => {
		if (
			!confirm(
				`Вы действительно хотите удалить товар "${product.name}"? Данное действие невозможно отменить`
			)
		)
			return
		setLoadingInfo(true)
		try {
			await api.delete(`/products/${product.id}`)
			setContextProduct(null)
			toast.success(`Товар ${product.name} успешно удален`)
			//обновляем список товаров
			await fetchProducts()
		} catch (err) {
			console.error(err)
			toast.error(`Не удалось удалить товар ${product.name}`)
			setLoadingInfo(false)
		}
	}
	return (
		<div className='flex bg-[#F4F4F5] min-h-screen'>
			<div className='flex flex-col flex-1 overflow-hidden ml-[60px]'>
				<header className='header-style'>
					<span className='pagename-font'>Список складов</span>
					<div className='flex items-center space-x-5'>
						<AddWarehouseDialog />
						<UserAvatar />
					</div>
				</header>

				<main className='flex-1 p-3 h-full'>
					<div className='grid grid-cols-24 gap-3 justify-between h-full'>
						<section className='bg-white rounded-[15px] col-span-10 h-full p-[10px]'>
							<h2 className='big-section-font mb-3'>Список складов</h2>
							<WarehouseList
								warehouses={warehouses}
								selectedWarehouse={selectedWarehouse}
								loading={loading}
								error={error}
								onSelect={handleSelectWarehouse}
								onContextMenu={setContextWarehouse}
								onDelete={deleteWarehouse}
							/>
						</section>

						<section className='bg-white rounded-[15px] col-span-14 h-full p-[10px] space-y-5'>
							<h2 className='big-section-font'>
								Подробная информация о складе
							</h2>

							{!selectedWarehouse ? (
								<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
									выберите склад для отображения подробной информации
								</div>
							) : (
								<>
									<div>
										<Label
											htmlFor='name'
											className='text-[20px] font-medium text-black'
										>
											Название
										</Label>
										<div className='flex w-full items-center gap-2'>
											<Input
												type='text'
												id='name'
												name='name'
												className='main-input'
												value={editedWarehouse.name}
												onChange={handleInputChange}
											/>
											<Button
												type='submit'
												className='warehouse-save-changes-button'
												onClick={() => handleSave('name')}
												disabled={
													editedWarehouse.name == selectedWarehouse.name
												}
											>
												Сохранить
											</Button>
										</div>
									</div>

									<div>
										<Label
											htmlFor='address'
											className='text-[20px] font-medium text-black'
										>
											Адрес
										</Label>
										<div className='flex w-full items-center gap-2'>
											<Input
												type='text'
												id='address'
												name='address'
												className='main-input'
												value={editedWarehouse.address}
												onChange={handleInputChange}
											/>
											<Button
												type='submit'
												className='warehouse-save-changes-button'
												onClick={() => handleSave('address')}
												disabled={
													editedWarehouse.address == selectedWarehouse.address
												}
											>
												Сохранить
											</Button>
										</div>
									</div>

									<div>
										<Label
											htmlFor='max_products'
											className='text-[20px] font-medium text-black'
										>
											Вместимость
										</Label>
										<div className='flex w-full items-center gap-2'>
											<Input
												type='number'
												id='max_products'
												name='max_products'
												className='main-input'
												value={editedWarehouse.max_products}
												onChange={handleInputChange}
											/>
											<Button
												type='submit'
												className='warehouse-save-changes-button'
												onClick={() => handleSave('max_products')}
												disabled={
													editedWarehouse.max_products ==
													selectedWarehouse.max_products
												}
											>
												Сохранить
											</Button>
										</div>
									</div>

									{/* ==== Роботы ==== */}
									<div>
										<div className='flex justify-between items-center mb-0'>
											<span className='text-[20px] font-medium'>
												Роботы, задействованные на складе
											</span>
											<Button
												variant='outline'
												size='icon'
												aria-label='Add Robot'
												className='small-add-button'
												onClick={handleAddRobot}
												disabled={denyAdminAccess}
											>
												<AddSmall
													style={{ width: '22px', height: '22px' }}
													fill='#7700FF'
												/>
											</Button>
										</div>
										{loadingInfo ? (
											<div className='space-y-2'>
												{[...Array(4)].map((_, i) => (
													<div
														key={i}
														className='flex justify-between items-center bg-[#F2F3F4] rounded-[10px] px-[10px] py-[10px]'
													>
														<div className='flex items-center gap-3'>
															<Skeleton className='bg-[#CDCED2] h-[20px] w-[120px] rounded-md' />
														</div>
														<div className='text-right space-y-1'>
															<Skeleton className='bg-[#CDCED2] h-[14px] w-[180px] rounded-md' />
															<Skeleton className='bg-[#CDCED2] h-[14px] w-[200px] rounded-md' />
														</div>
													</div>
												))}
											</div>
										) : error ? (
											<div className='not-found-container'>
												не удалось получить данные о роботах
											</div>
										) : robots.length === 0 ? (
											<div className='not-found-container'>
												<p>роботы не найдены</p>
											</div>
										) : (
											<div className='max-h-[235px] overflow-y-auto space-y-2'>
												{robots.map(robot => (
													<ContextMenu key={robot.id}>
														<ContextMenuTrigger asChild>
															<div className='product-button-elem'>
																<span className='text-[18px] font-medium text-black'>
																	{robot.id}
																</span>
																<div className='text-right text-[#5A606D] text-[14px]'>
																	<div>заряд: {robot.battery_level}%</div>
																	<div>
																		статус: {getRobotStatus(robot.status)}
																	</div>
																</div>
															</div>
														</ContextMenuTrigger>
														<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
															<ContextMenuItem
																className='context-menu-delete'
																onClick={() => handleDeleteRobot(robot)}
															>
																Удалить
															</ContextMenuItem>
														</ContextMenuContent>
													</ContextMenu>
												))}
											</div>
										)}
									</div>

									{/* ==== Товары ==== */}
									<div>
										<div className='flex justify-between items-center mb-0'>
											<span className='text-[20px] font-medium'>
												Товары на складе
											</span>
											<Dialog open={openAdd} onOpenChange={setOpenAdd}>
												<DialogTrigger asChild>
													<Button
														variant='outline'
														size='icon'
														aria-label='Add Product'
														className='small-add-button'
														disabled={denyAdminAccess}
														onClick={() => setOpenAdd(true)}
													>
														<AddSmall
															style={{ width: '22px', height: '22px' }}
															fill='#7700FF'
														/>
													</Button>
												</DialogTrigger>
												<DialogContent className='bg-[#F4F4F5] !p-[20px] !w-[558px]'>
													<form onSubmit={handleAddProduct}>
														<DialogHeader>
															<DialogTitle className='dialog-title-text'>
																Добавление товара
															</DialogTitle>
														</DialogHeader>
														<div className='grid gap-4'>
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
																<Label
																	className='section-title'
																	htmlFor='address'
																>
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
																<Label
																	className='section-title'
																	htmlFor='stock'
																>
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
																<Label
																	className='section-title'
																	htmlFor='stock'
																>
																	Категория товара
																</Label>
																<Select onValueChange={handleCategoryChange}>
																	<SelectTrigger className='w-full'>
																		<SelectValue placeholder='Выберите категорию' />
																	</SelectTrigger>
																	<SelectContent>
																		<SelectItem value='Смартфоны'>
																			Смартфоны
																		</SelectItem>
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
																<Label
																	className='section-title'
																	htmlFor='current_position'
																>
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
														</div>
														<DialogFooter className='mt-2'>
															<DialogClose asChild>
																<Button className='w-[50%] items-center rounded-[10px] text-[18px] text-white font-medium bg-[#FF4F12] cursor-pointer transition-all hover:brightness-90'>
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
												</DialogContent>
											</Dialog>
										</div>
										{loadingInfo ? (
											<div className='space-y-2'>
												{[...Array(4)].map((_, i) => (
													<div
														key={i}
														className='flex justify-between items-center bg-[#F2F3F4] rounded-[10px] px-[10px] py-[10px]'
													>
														<div className='flex items-center gap-3'>
															<Skeleton className='bg-[#CDCED2] h-[20px] w-[120px] rounded-md' />
														</div>
														<div className='text-right space-y-1'>
															<Skeleton className='bg-[#CDCED2] h-[14px] w-[180px] rounded-md' />
															<Skeleton className='bg-[#CDCED2] h-[14px] w-[200px] rounded-md' />
														</div>
													</div>
												))}
											</div>
										) : error ? (
											<div className='flex items-center justify-center font-medium text-center h-full text-[#9699A3] text-[24px]'>
												не удалось получить данные о товарах
											</div>
										) : products.length === 0 ? (
											<div className='not-found-container'>
												<p>товары не найдены</p>
											</div>
										) : (
											<div className='!max-h-[235px] overflow-y-auto !space-y-2'>
												{products.map(p => (
													<ContextMenu key={p.id}>
														<ContextMenuTrigger asChild>
															<Button
																key={p.id}
																onClick={() => handleOpenProduct(p)}
																className='product-button'
															>
																<div className='product-button-elem'>
																	<span className='text-[18px] font-medium text-black'>
																		{p.name}
																	</span>
																	<div className='text-right text-[#5A606D] text-[14px]'>
																		<div>статус: {getStatusName(p.status)}</div>
																		<div>количество: {p.stock} шт</div>
																	</div>
																</div>
															</Button>
														</ContextMenuTrigger>
														<ContextMenuContent className='bg-[#F2F3F4] border-[#9699A3] p-0 rounded-[10px]'>
															<ContextMenuItem
																className='context-menu-delete'
																onClick={() => handleDeleteProduct(p)}
															>
																Удалить
															</ContextMenuItem>
														</ContextMenuContent>
													</ContextMenu>
												))}
												<Dialog open={openEdit} onOpenChange={setOpenEdit}>
													<DialogContent className='bg-[#F4F4F5] !p-[20px] !w-[558px]'>
														<form onSubmit={handleUpdateProduct}>
															<DialogHeader>
																<DialogTitle className='dialog-title-text'>
																	Просмотр и редактирование
																</DialogTitle>
															</DialogHeader>
															<div className='grid gap-3'>
																<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
																	<Label
																		className='section-title'
																		htmlFor='name'
																	>
																		Название товара
																	</Label>
																	<Input
																		className='dialog-input-placeholder-text'
																		id='name'
																		name='name'
																		value={editedProduct?.name}
																		onChange={handleProductEditChange}
																		placeholder='Например, Apple IPhone 17'
																		required
																	/>
																</div>
																<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
																	<Label
																		className='section-title'
																		htmlFor='address'
																	>
																		Артикул товара
																	</Label>
																	<Input
																		className='dialog-input-placeholder-text'
																		id='article'
																		name='article'
																		value={editedProduct?.article}
																		onChange={handleProductEditChange}
																		placeholder='Например, 9573420'
																		required
																	/>
																</div>
																<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
																	<Label
																		className='section-title'
																		htmlFor='stock'
																	>
																		Количество единиц товара (шт)
																	</Label>
																	<Input
																		className='dialog-input-placeholder-text'
																		id='stock'
																		name='stock'
																		value={editedProduct?.stock}
																		onChange={handleProductEditChange}
																		placeholder='100'
																		required
																	/>
																</div>
																<div className='grid gap-3 bg-white p-[10px] rounded-[10px]'>
																	<Label
																		className='section-title'
																		htmlFor='stock'
																	>
																		Категория товара
																	</Label>
																	<Select
																		value={editedProduct?.category}
																		onValueChange={value =>
																			setEditedProduct(prev =>
																				prev
																					? { ...prev, category: value }
																					: prev
																			)
																		}
																	>
																		<SelectTrigger className='w-full'>
																			<SelectValue placeholder='Выберите категорию' />
																		</SelectTrigger>
																		<SelectContent>
																			<SelectItem value='Смартфоны'>
																				Смартфоны
																			</SelectItem>
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
																	<Label
																		className='section-title'
																		htmlFor='current_position'
																	>
																		Расположение товара
																	</Label>
																	<Input
																		className='dialog-input-placeholder-text'
																		id='current_position'
																		name='current_position'
																		value={`${editedProduct?.current_row}, ${editedProduct?.current_shelf}`}
																		onChange={handleProductEditChange}
																		placeholder='Координаты сектора, в формате 1-50, A-Z'
																		required
																	/>
																</div>
															</div>
															<DialogFooter className='mt-3'>
																<DialogClose asChild>
																	<Button className='w-[50%] items-center rounded-[10px] text-[18px] text-white font-medium bg-[#FF4F12] cursor-pointer transition-all hover:brightness-90'>
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
																	{loading ? 'Изменение...' : 'Подтвердить'}
																</Button>
															</DialogFooter>
														</form>
													</DialogContent>
												</Dialog>
											</div>
										)}
									</div>
								</>
							)}
						</section>
					</div>
				</main>
			</div>
		</div>
	)
}

export default ListPage
