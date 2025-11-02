import { Navigate } from 'react-router-dom'
import { useUserStore } from '@/store/useUserStore'

interface ProtectedRouteProps {
	children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
	const { user } = useUserStore()
	const token =
		localStorage.getItem('token') || sessionStorage.getItem('token')

	// если токена нет — редирект на страницу авторизации
	if (!token || !user) {
		return <Navigate to="/auth" replace />
	}

	return <>{children}</>
}