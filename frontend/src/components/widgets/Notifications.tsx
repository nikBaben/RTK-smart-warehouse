import api from '@/api/axios'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
const token = localStorage.getItem('token')


type NotificationItem = {
  title: string;
  subtitle: string;
  date: string;
  status: string;
  type?: "scan" | "forecast";
}
/* const notifications: NotificationItem[] = [
  {
    title: "Результаты сканирования робота ID-432332",
    subtitle: "Apple IPhone 17 Pro Max",
    date: "18.10.2025",
    status: "новый статус: критический",
    type: "scan",
  },
  {
    title: "Новый прогноз от ИИ",
    subtitle: "Фигурка коллекционная",
    date: "18.10.2025",
    status: "проверьте рекомендованные действия дашборде",
    type: "forecast",
  },
  {
    title: "Результаты сканирования робота ID-432332",
    subtitle: "Apple IPhone 17 Pro Max – обновление статуса",
    date: "06.05.2025",
    status: "новый статус: критический",
    type: "scan",
  },
  {
    title: "Результаты сканирования робота ID-432332",
    subtitle: "Apple IPhone 17 Pro Max – обновление статуса",
    date: "06.05.2025",
    status: "новый статус: критический",
    type: "scan",
  },
  {
    title: "Новый прогноз от ИИ",
    subtitle: "Фигурка коллекционная",
    date: "18.10.2025",
    status: "проверьте рекомендованные действия дашборде",
    type: "forecast",
  },
  {
    title: "Результаты сканирования робота ID-432332",
    subtitle: "Apple IPhone 17 Pro Max – обновление статуса",
    date: "06.05.2025",
    status: "новый статус: критический",
    type: "scan",
  },
  {
    title: "Результаты сканирования робота ID-432332",
    subtitle: "Apple IPhone 17 Pro Max – обновление статуса",
    date: "06.05.2025",
    status: "новый статус: критический",
    type: "scan",
  },
]; */


export function Notification(){
  const [loading, setLoading] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
 
  const handleNotifications = async(token: string) => {
    setLoading(true)
    try{
     /*  const response = await api.get('/notifications') */
      /* setNotifications(response.data) */
    }
    catch(error){
      toast.error('Не удалось загрузить уведомления')
    }
    finally{
      setLoading(false)
    }
  }

  useEffect(()=>{
/*     if (!token){
      console.warn('Токен отсутствует — пользователь не авторизован')
			alert('Токен отсутствует — пользователь не авторизован')
      return
    }
    handleNotifications(token) */
  })
  return (
    <div className="bg-white rounded-[15px]">
      <div className="flex flex-col gap-[10px]">
        {notifications.map((item, index) => (
          <div
            key={index}
            className="flex justify-between items-center bg-[#F6F7F7] rounded-[10px] h-[59px] px-3 py-2"
          >
            <div className="flex flex-col gap-0.5">
              <span className="text-[16px] font-medium text-[#000]">
                {item.title}
              </span>
              <span className="text-[14px] text-[#5A606D] font-light">{item.subtitle}</span>
            </div>

            <div className="flex flex-col gap-1.5 text-right">
              <span className="text-[12px] text-[#5A606D] font-light">
                {item.date}
              </span>
              <span
                className={"text-[12px] text-[#5E5E5E] font-light"}
              >
                {item.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};