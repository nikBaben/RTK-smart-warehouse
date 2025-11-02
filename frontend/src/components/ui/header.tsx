import React from "react";
import Logo from "/src/assets/logos/RTKlogo.svg";

export function Header() {
  return (
    <nav className="sticky top-0 left-0 z-50 w-screen bg-white backdrop-blur-md">
      <div className="flex items-center justify-between h-[98px] px-4 sm:px-6 lg:px-8">
        <div className="w-[175px] h-[56px] flex gap-[3px] relative">
            <a href="/">
                <img src={Logo} alt="RTK" className="h-[56] w-auto object-contain" />
            </a>
            <div className="flex flex-col justify-center absolute bottom-[0px] right-[0px]">
                <span className="font-rostelecom font-bold text-[22px] leading-[28px]">
                Умный склад
                </span>
                <span className="font-rostelecom font-semibold text-[12px] leading-[14px] text-gray-700">
                Ростелеком
                </span>
            </div>
        </div>
      </div>
    </nav>
  );
}
