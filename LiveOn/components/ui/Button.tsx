import Link from "next/link";
import clsx from "clsx";
import { ComponentPropsWithoutRef, ReactNode } from "react";

type ButtonProps = {
  variant?: "primary" | "outline" | "ghost";
  href?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
} & ComponentPropsWithoutRef<"button">;

const baseStyles =
  "inline-flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f6c35d]";

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-[#f6c35d] text-[#0f253d] shadow-ring hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60",
  outline:
    "border border-white/15 bg-white/[0.04] text-white/85 hover:border-white/25 hover:text-white disabled:cursor-not-allowed disabled:opacity-50",
  ghost:
    "text-white/70 hover:text-white hover:bg-white/[0.06] disabled:cursor-not-allowed disabled:opacity-50",
};

export function Button({
  variant = "primary",
  leftIcon,
  rightIcon,
  href,
  className,
  children,
  ...props
}: ButtonProps) {
  const classes = clsx(baseStyles, variants[variant], className);

  if (href) {
    return (
      <Link href={href} className={classes}>
        {leftIcon}
        {children}
        {rightIcon}
      </Link>
    );
  }

  return (
    <button className={classes} {...props}>
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}

