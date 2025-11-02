
import { UserAvatar } from '../ui/UserAvatar.tsx'

import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from '@/components/ui/accordion'

function InfoPage() {
	return (
		<div className='flex bg-[#F4F4F5] min-h-screen'>
			<div className='flex flex-col flex-1 overflow-hidden ml-[60px]'>
				<header className='header-style'>
					<span className='pagename-font'>Информация</span>
					<div className='flex items-center space-x-5'>
						<UserAvatar />
					</div>
				</header>

				<main className='flex-1 p-3 h-full'>
					<div className='grid grid-cols-12 gap-3 justify-between h-full'>
						<section className='bg-white rounded-[10px] col-span-12 h-full p-[10px]'>
							<h2 className='big-section-font mb-3'>FAQ</h2>
							<div>
								<Accordion
									type='single'
									collapsible
									className='w-full'
									defaultValue='item-1'
								>
									<AccordionItem value='item-1'>
										<AccordionTrigger className='text-[18px]'>
											Что такое Ростелеком Умный склад?
										</AccordionTrigger>
										<AccordionContent className='faq-elem-style'>
											<p>
												Ростелеком Умный склад - это решение кейса "Умный склад
												- система управления складской логистикой с
												использованием автономных роботов" для кейс-чемпионата
												"Войти в IT".
											</p>
											<p>
												Данный сайт позволяет сотрудникам наблюдать за складами
												нового поколения, оснащенных роботами и системами IoT,
												контролировать ключевые метрики, отслеживать поставки, а
												также следить за картой склада и роботами.
											</p>
										</AccordionContent>
									</AccordionItem>
									<AccordionItem value='item-2'>
										<AccordionTrigger className='text-[18px]'>
											Как работать с сайтом?
										</AccordionTrigger>
										<AccordionContent className='faq-elem-style'>
											<p>
												We offer worldwide shipping through trusted courier
												partners. Standard delivery takes 3-5 business days,
												while express shipping ensures delivery within 1-2
												business days.
											</p>
											<p>
												All orders are carefully packaged and fully insured.
												Track your shipment in real-time through our dedicated
												tracking portal.
											</p>
										</AccordionContent>
									</AccordionItem>
									<AccordionItem value='item-3'>
										<AccordionTrigger className='text-[18px]'>
											Технологический стек
										</AccordionTrigger>
										<AccordionContent className='faq-elem-style'>
											<p>
												We stand behind our products with a comprehensive 30-day
												return policy. If you&apos;re not completely satisfied,
												simply return the item in its original condition.
											</p>
											<p>
												Our hassle-free return process includes free return
												shipping and full refunds processed within 48 hours of
												receiving the returned item.
											</p>
										</AccordionContent>
									</AccordionItem>
									<AccordionItem value='item-4'>
										<AccordionTrigger className='text-[18px]'>
											Наша команда
										</AccordionTrigger>
										<AccordionContent className='faq-elem-style'>
											<p>
												We stand behind our products with a comprehensive 30-day
												return policy. If you&apos;re not completely satisfied,
												simply return the item in its original condition.
											</p>
											<p>
												Our hassle-free return process includes free return
												shipping and full refunds processed within 48 hours of
												receiving the returned item.
											</p>
										</AccordionContent>
									</AccordionItem>
								</Accordion>
							</div>
						</section>
					</div>
				</main>
			</div>
		</div>
	)
}

export default InfoPage
