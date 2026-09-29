type NotificationItem = {
  title: string;
  subtitle: string;
  date: string;
  status: string;
  type?: "scan" | "forecast";
}
export function Notification(){
  // Notifications are not connected to the API yet.
  const notifications: NotificationItem[] = []
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