import React from "react";

interface ContainerProps {
  className?: string;
  children?: React.ReactNode;
}

export default function Container({ className = "", children }: ContainerProps) {
  return (
    <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 ${className}`}>
      {children}
    </div>
  );
}
