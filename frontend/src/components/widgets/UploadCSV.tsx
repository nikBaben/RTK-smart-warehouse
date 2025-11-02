'use client';
import { Dropzone, DropzoneContent, DropzoneEmptyState } from '@/components/ui/shadcn-io/dropzone';
import { useState } from 'react';
import { Button } from '../ui/button';
import {
	Dialog,
	DialogClose,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from '@/components/ui/dialog'
import Download from '@atomaro/icons/24/action/Download'




export function UploadCSV(){
  const [files, setFiles] = useState<File[] | undefined>();
  const handleDrop = (files: File[]) => {
    console.log(files);
    setFiles(files);
  };
  return (
		<Dialog>
			<DialogTrigger>
				<button title='Экспорт CSV' className='transition-transform'>
					<Download
						fill='#9CA3AF'
						className='hover:fill-white cursor-pointer transition-colors duration-200 w-[30px] h-auto'
					/>
				</button>
			</DialogTrigger>
			<DialogContent
				className='max-w-[600px] bg-white text-black p-6 rounded-2xl'
			>
				<DialogHeader>
					<DialogTitle>Загрузить CSV</DialogTitle>
					<DialogDescription>Описание (заглушка)</DialogDescription>
				</DialogHeader>
				<Dropzone
					maxSize={1024 * 1024 * 10}
					minSize={1024}
					onDrop={handleDrop}
					onError={console.error}
					src={files}
				>
					<DropzoneEmptyState />
					<DropzoneContent />
				</Dropzone>
			</DialogContent>
		</Dialog>
	)
};
export default UploadCSV
