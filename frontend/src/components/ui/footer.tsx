import React from "react";

export function Footer() {
    return (
        <footer className="w-full bg-none py-4 flex items-center justify-between px-8 mt-auto">
            <div>
                <span className="text-[16px] text-[#9699A3] font-medium">
                    2025 ПАО “Ростелеком”
                </span>
            </div>
            <div className="flex flex-col items-start">
                <div>
                    <span className="text-[12px] text-[#9699A3] font-medium">
                        Служба поддержки
                    </span>
                </div>
                <div>
                    <span className="text-[24px] text-[#111929] font-bold">
                        8 800 350 03 35
                    </span>
                </div>
            </div>
        </footer>
    );
}
