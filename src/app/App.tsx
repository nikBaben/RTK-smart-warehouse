import {
	BrowserRouter as Router,
	Routes,
	Route,
	useLocation,
} from 'react-router-dom'

import { Navbar } from "@/components/widgets/navbar";
import { Toaster } from '@/components/ui/sonner'
import { useState } from 'react'
import DashboardPage from '@/components/pages/DashboardPage'
import  AuthPage  from '@/components/pages/AuthPage';
import HistoryPage from "@/components/pages/HistoryPage";
import SuppliesPage from '@/components/pages/SuppliesPage'
import ListPage from '@/components/pages/ListPage';
import InfoPage from '@/components/pages/InfoPage'
import SettingsPage from '@/components/pages/SettingsPage'
import NotFound from '@/app/not-found'
import ServerErrorPage from '@/components/pages/ServerErrorPage';
import { ProtectedRoute } from '@/components/routes/ProtectedRoute';

function AppLayout() {
	const location = useLocation()
	
	const hideNavbarPaths = ['/auth']

	const isNotFoundPage =
		location.pathname !== '/' &&
		!['/auth', '/history', '/supplies', '/list', '/info', '/settings'].includes(
			location.pathname
		)

	const isHideNavbar =
		hideNavbarPaths.includes(location.pathname) || isNotFoundPage
	return (
		<div className='min-h-screen flex flex-row bg-gray-50 text-gray-900 font-rostelecom'>
			{!isHideNavbar && <Navbar />}
			<main className='flex-1'>
				<Routes>
					<Route
						path='/'
						element={
							<ProtectedRoute>
								<DashboardPage />
							</ProtectedRoute>
						}
					/>
					<Route path='/auth' element={<AuthPage />} />
					<Route
						path='/history'
						element={
							<ProtectedRoute>
								<HistoryPage />
							</ProtectedRoute>
						}
					/>
					<Route
						path='/supplies'
						element={
							<ProtectedRoute>
								<SuppliesPage />
							</ProtectedRoute>
						}
					/>
					<Route
						path='/list'
						element={
							<ProtectedRoute>
								<ListPage />
							</ProtectedRoute>
						}
					/>
					<Route
						path='/info'
						element={
							<ProtectedRoute>
								<InfoPage />
							</ProtectedRoute>
						}
					/>
					<Route
						path='/settings'
						element={
							<ProtectedRoute>
								<SettingsPage />
							</ProtectedRoute>
						}
					/>
					<Route
						path='/500'
						element={
							<ProtectedRoute>
								<ServerErrorPage />
							</ProtectedRoute>
						}
					/>
					<Route path='*' element={<NotFound />} />
				</Routes>
			</main>
			<Toaster richColors position='bottom-right' />
		</div>
	)
}

export default function App(){
  return(
    <Router>
      <AppLayout/>
    </Router>
  )
}