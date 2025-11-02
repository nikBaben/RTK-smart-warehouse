import api from '@/api/axios'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'
const token = localStorage.getItem('token')


export function Notification(){
 
  const handleNotifications = async(token: string) => {
  }
  return (
    <div className="bg-white rounded-[15px]">
      <div className="flex flex-col gap-[10px]">
        <div className='flex items-center justify-center font-medium text-center text-[#9699A3] text-[28px]'>
				  <h1>раздел в разработке</h1>
				</div>
      </div>
    </div>
  );
};