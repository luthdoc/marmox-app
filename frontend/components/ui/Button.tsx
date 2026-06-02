import React from "react";

type ButtonVariant = "primary" | "utility";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant: ButtonVariant;
  children: React.ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "rounded-[9999px] bg-action-blue text-white px-6 py-2 font-medium hover:opacity-90 transition-opacity",
  utility:
    "rounded-[8px] border border-[var(--color-hairline)] bg-transparent text-[var(--color-ink)] px-4 py-2 hover:bg-[var(--color-canvas-parchment)] transition-colors",
};

export function Button({ variant, children, className = "", ...props }: ButtonProps) {
  return (
    <button className={`${variantClasses[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
