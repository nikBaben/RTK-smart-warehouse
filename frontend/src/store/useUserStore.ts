import { create } from 'zustand'
import { persist } from 'zustand/middleware'
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
	setUser: (user: User) => void
	updateUser: (partial: Partial<User>) => void
	clearUser: () => void
}


export const useUserStore = create<UserState>()(
	persist(
		set => ({
			user: null,
			setUser: user => set({ user }),
			updateUser: partial =>
				set(state =>
					state.user ? { user: { ...state.user, ...partial } } : state
				),
			clearUser: () => set({ user: null }),
		}),
		{
			name: 'user-storage',
			// сохраняем минимально (например, только id/email) если нужно
			partialize: state => ({
				user: state.user
					? { id: state.user.id, email: state.user.email }
					: null,
			}),
		}
	)
)