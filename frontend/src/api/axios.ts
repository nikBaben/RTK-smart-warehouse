import axios from 'axios';

const api = axios.create({
  baseURL: 'https://dev.rtk-smart-warehouse.ru/api/v1',
  headers: {
    "Content-Type": "application/json",
    timeout: 1000,
  },
});

//работа с JWT токеном
api.interceptors.request.use(config => {
	const token = localStorage.getItem('token')
	if (token) {
		config.headers.Authorization = `Bearer ${token}`
	}
	return config
})

//перехватываем ошибки и выводим страницу 500
api.interceptors.response.use(
	response => response,
	error => {
		if (error.response?.status === 500) {
			window.location.href = '/500'
		}

		//  если токен невалиден — отправляем на авторизацию
		if (error.response?.status === 401) {
			localStorage.removeItem('token')
			window.location.href = '/auth'
		}

		return Promise.reject(error)
	}
)

export default api;