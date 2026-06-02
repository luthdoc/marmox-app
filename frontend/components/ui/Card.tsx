import React from "react";

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-[18px] bg-[var(--color-canvas)] p-6 ${className}`}
    >
      {children}
    </div>
  );
}
