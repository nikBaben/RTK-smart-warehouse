import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '@/api/axios'

interface User {
	id: string
	name?: string
	first_name?: string
	last_name?: string
	role: string
	email: string
}

interface UserState {
	user: User | null
	token: string | null
	rememberMe: boolean

	setUser: (user: User) => void
	updateUser: (partial: Partial<User>) => void
	setToken: (token: string, remember: boolean) => void
	logout: () => void
	isAuthenticated: () => boolean
	login: (email: string, password: string, remember: boolean) => Promise<void>
}

export const useUserStore = create<UserState>()(
	persist(
		(set, get) => ({
			user: null,
			token: localStorage.getItem('token') || sessionStorage.getItem('token'),
			rememberMe: false,

			setUser: user => set({ user }),

			updateUser: partial =>
				set(state =>
					state.user ? { user: { ...state.user, ...partial } } : state
				),

			setToken: (token, remember) => {
				if (remember) localStorage.setItem('token', token)
				else sessionStorage.setItem('token', token)
				set({ token, rememberMe: remember })
			},

			logout: () => {
				localStorage.removeItem('token')
				sessionStorage.removeItem('token')
				set({ user: null, token: null })
			},

			isAuthenticated: () =>
				!!(localStorage.getItem('token') || sessionStorage.getItem('token')),

			login: async (email, password, remember) => {
				const res = await api.post('/auth/login', { email, password })
				const token = res.data.token
				if (!token) throw new Error('Токен не получен')

				if (remember) localStorage.setItem('token', token)
				else sessionStorage.setItem('token', token)

				set({ token, rememberMe: remember })

				// Получаем данные пользователя
				const profile = await api.get('/auth/profile', {
					headers: { Authorization: `Bearer ${token}` },
				})
				set({ user: profile.data })
			},
		}),
		{
			name: 'user-storage',
			// сохраняем всё, кроме пароля (которого нет)
			partialize: state => ({
				user: state.user,
				token: state.token,
				rememberMe: state.rememberMe,
			}),
		}
	)
)
