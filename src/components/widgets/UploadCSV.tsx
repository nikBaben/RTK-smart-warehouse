'use client';

import { useState } from 'react';
import { Dropzone, DropzoneContent, DropzoneEmptyState } from '@/components/ui/shadcn-io/dropzone';
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
	DialogFooter,
} from '@/components/ui/dialog';
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from '@/components/ui/button';
import Download from '@atomaro/icons/24/action/Download';
import CSV from '@atomaro/icons/24/document/CSV';
import CheckLarge from "@atomaro/icons/24/navigation/CheckLarge";
import CloseLarge from "@atomaro/icons/24/navigation/CloseLarge";

import MiniSelectWarehouse from '../ui/MiniSelectWarehouse.tsx';
import { useWarehouseStore } from '@/store/useWarehouseStore';
import { toast } from 'sonner';
import { FancyProgress } from '@/components/ui/FancyProgress';



const readFileWithEncoding = (file: File): Promise<string> => {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();

		reader.onload = () => {
			const text = reader.result as string;
			if (text.includes('�') || !/[а-яА-Я]/.test(text)) {
				const reader1251 = new FileReader();
				reader1251.onload = () => resolve(reader1251.result as string);
				reader1251.onerror = reject;
				reader1251.readAsText(file, 'windows-1251');
			} else {
				resolve(text);
			}
		};

		reader.onerror = reject;
		reader.readAsText(file, 'utf-8');
	});
};

const parseCSV = (text: string) => {
	text = text.replace(/^\uFEFF/, '');

	const firstLine = text.split('\n')[0];
	const delimiter = firstLine.includes(';')
		? ';'
		: firstLine.includes('\t')
		? '\t'
		: ',';

	const rows = text
		.trim()
		.split(/\r?\n/)
		.map(line => {
			const cleaned = line.replace(/^"|"$/g, '').replace(/"{2}/g, '"');
			return cleaned.split(delimiter).map(cell => cell.trim());
		});

	return rows;
};

export function UploadCSV() {
	const [files, setFiles] = useState<File[] | undefined>();
	const [csvPreview, setCsvPreview] = useState<string[][] | null>(null);
	const [isUploading, setIsUploading] = useState(false);
	const [success, setSuccess] = useState(false);
	const [uploadProgress, setUploadProgress] = useState(0);

	const { selectedWarehouse } = useWarehouseStore();

	const expectedHeaders = [
		'product_id',
		'product_name',
		'quantity',
		'zone',
		'date',
		'row',
		'shelf',
	];

	const handleDrop = async (acceptedFiles: File[]) => {
		setCsvPreview(null);

		const csvFiles = acceptedFiles.filter(file => file.name.toLowerCase().endsWith('.csv'));
		if (csvFiles.length === 0) {
			toast.error('Пожалуйста, выберите CSV файл');
			return;
		}

		const file = csvFiles[0];
		setFiles([file]);

		try {
			const text = await readFileWithEncoding(file);
			if (!text.trim()) {
				toast.error('CSV файл пустой');
				return;
			}

			const rows = parseCSV(text);
			if (!rows.length) {
				toast.error('Не удалось прочитать содержимое CSV');
				return;
			}

			const headers = rows[0].map(h => h.toLowerCase().trim());
			const missing = expectedHeaders.filter(h => !headers.includes(h));

			if (missing.length > 0) {
				toast.error(`Некорректный CSV формат. Отсутствуют колонки: ${missing.join(', ')}`);
				return;
			}

			const previewRows = rows.slice(0, 6);
			setCsvPreview(previewRows);
		} catch (err) {
			toast.error('Ошибка при чтении файла');
			console.error(err);
		}
	};

	const token = localStorage.getItem('token');

	const handleUpload = async () => {
		if (!selectedWarehouse?.id) {
			toast.error("Выберите склад перед загрузкой файла");
			return;
		}
		if (!files?.[0]) {
			toast.error("Файл не выбран");
			return;
		}

		setIsUploading(true);
		setSuccess(false);
		setUploadProgress(0);

		const formData = new FormData();
		formData.append('csv_file', files[0]);

		try {
			await new Promise<void>((resolve, reject) => {
				const xhr = new XMLHttpRequest();
				xhr.open('POST', `https://dev.rtk-smart-warehouse.ru/api/v1/inventory_history/import_inventory_from_csv/${selectedWarehouse.id}`);
				xhr.setRequestHeader('Authorization', `Bearer ${token}`);

				xhr.upload.onprogress = (event) => {
					if (event.lengthComputable) {
						const percent = Math.round((event.loaded / event.total) * 100);
						setUploadProgress(percent);
					}
				};

				xhr.onload = () => {
					if (xhr.status >= 200 && xhr.status < 300) {
						setSuccess(true);
						toast.success("Файл успешно загружен!");
						setTimeout(() => {
							setFiles(undefined);
							setCsvPreview(null);
							setSuccess(false);
							setUploadProgress(0);
						}, 2000);
						resolve();
					} else {
						reject(xhr.responseText);
					}
				};

				xhr.onerror = () => reject('Ошибка при загрузке файла');
				xhr.send(formData);
			});
		} catch (err) {
			console.error(err);
			toast.error('Не удалось отправить файл на сервер');
		} finally {
			setIsUploading(false);
		}
	};

	return (
		<Dialog>
			<DialogTrigger>
				<button title='Импорт CSV' className='transition-transform'>
					<Download
						fill='#9CA3AF'
						className='hover:fill-white cursor-pointer transition-colors duration-200 w-[30px] h-auto'
					/>
				</button>
			</DialogTrigger>

			<DialogContent className='max-w-[558px] max-h-[326px] bg-[#F4F4F5] text-black py-[10px] px-[20px] rounded-[15px] flex flex-col gap-[5px]'>
				<DialogHeader className='flex flex-row justify-between pr-[15px]'>
					<DialogTitle className='text-[24px]'>Загрузить CSV</DialogTitle>
					<MiniSelectWarehouse />
				</DialogHeader>

				{/* === Этап выбора файла === */}
				{!csvPreview && (
					<div className='h-[207px] flex flex-col items-center justify-center'>
						<Dropzone
							accept={{ 'text/csv': ['.csv'] }}
							maxFiles={1}
							onDrop={handleDrop}
							src={files}
							className={cn(
								'relative w-[450px] h-[150px] rounded-[12px] border-2 border-dashed flex flex-col ring-0 items-center justify-center transition-all duration-300 ease-out cursor-pointer overflow-hidden',
								files && files.length > 0
									? 'border-[#7700FF] bg-[#F3EFFF]'
									: 'border-[#c28dff] bg-[#F4F4F5] hover:border-[#7700FF] hover:bg-[#F3F1FF]'
							)}
						>
							<AnimatePresence mode="wait">
								{files && files.length > 0 ? (
									<motion.div
										key="file"
										initial={{ opacity: 0, scale: 0.95 }}
										animate={{ opacity: 1, scale: 1 }}
										exit={{ opacity: 0, scale: 0.95 }}
										transition={{ duration: 0.25 }}
									>
										<DropzoneContent>
											<div className="flex flex-col items-center gap-2">
												<CSV fill='#7700FF' size={40} />
												<p className="text-[#7700FF] font-semibold text-[16px]">
													{files[0].name}
												</p>
											</div>
										</DropzoneContent>
									</motion.div>
								) : (
									<motion.div
										key="empty"
										initial={{ opacity: 0, y: 10 }}
										animate={{ opacity: 1, y: 0 }}
										exit={{ opacity: 0, y: -10 }}
										transition={{ duration: 0.25 }}
									>
										<DropzoneEmptyState>
											<motion.div
												className="flex flex-col items-center gap-2 text-center"
												whileHover={{ scale: 1.03 }}
												whileTap={{ scale: 0.97 }}
											>
												<Download fill='#7700FF' size={40} />
												<p className="text-[#7700FF] font-medium text-[16px]">
													Выберите CSV файл
												</p>
												<p className="text-[#9699A3] text-[11px] font-medium">
													или перетащите сюда
												</p>
											</motion.div>
										</DropzoneEmptyState>
									</motion.div>
								)}
							</AnimatePresence>
						</Dropzone>
					</div>
				)}

				{csvPreview && (
					<div className='flex flex-col w-[518px] h-[276px] gap-[5px] relative'>

						{isUploading ? (
							<div className='flex flex-col items-center justify-center w-full h-full bg-white rounded-[10px]'>
								<FancyProgress value={uploadProgress}/>
								<p className='text-[#5A606D] text-[14px] mb-2'>Загрузка: {uploadProgress}%</p>
							</div>
						) : (
							<div className='bg-white w-[518px] h-auto rounded-[10px] px-[10px]'>
								<div className='w-[498px] h-[26px]'>
									<h2 className='text-black text-[18px] font-medium'>
										{files?.[0]?.name ? `${files[0].name} — предпросмотр` : 'предпросмотр'}
									</h2>
								</div>
								<Table className='w-[498px] text-center border-separate border-spacing-y-[5px] text-[10px]'>
									<TableHeader className="sticky top-0 bg-white z-10">
										<TableRow>
											{csvPreview[0].map((col, i) => (
												<TableHead key={i} className='border-none'>
													{col}
												</TableHead>
											))}
										</TableRow>
									</TableHeader>
									<TableBody>
										{csvPreview.slice(1).map((row, i) => (
											<TableRow key={i} className='bg-[#F2F3F4] h-[20px]'>
												{row.map((cell, j) => (
													<TableCell
														key={j}
														className={`border-none align-middle text-center p-0 
															${j === 0 ? 'rounded-l-[5px]' : ''} 
															${j === row.length - 1 ? 'rounded-r-[5px]' : ''}`}
													>
														{cell}
													</TableCell>
												))}
											</TableRow>
										))}
									</TableBody>
								</Table>
							</div>
						)}

						<DialogFooter className='flex justify-end gap-2'>
							<Button
								variant='outline'
								onClick={() => {
									setFiles(undefined);
									setCsvPreview(null);
								}}
								className='h-[26px] w-[145px] bg-[#FF4F12] text-white text-[12px] border-none rounded-[5px]'
								disabled={isUploading}
							>
								<CloseLarge fill="#FFFFFF" className="w-[7px] h-[7px]" />
								Отмена
							</Button>

							<Button
								className='h-[26px] w-[145px] bg-[#7700FF] hover:bg-[#5e00cc] text-white text-[12px] border-none rounded-[5px]'
								onClick={handleUpload}
								disabled={isUploading}
							>
								{isUploading ? (
									<span className="animate-pulse">Загрузка...</span>
								) : success ? (
									<>
										<CheckLarge fill="#FFFFFF" className="w-[7px] h-[7px]" />
										Успешно
									</>
								) : (
									<>
										<CheckLarge fill="#FFFFFF" className="w-[7px] h-[7px]" />
										Загрузить
									</>
								)}
							</Button>
						</DialogFooter>
					</div>
				)}
			</DialogContent>
		</Dialog>
	);
}

export default UploadCSV;
