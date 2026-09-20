import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-md border border-navy-3 bg-navy-2 px-4 text-body text-ice placeholder:text-ice-70/60",
        "focus:border-gold focus:outline-none",
        "aria-[invalid=true]:border-risk",
        className,
      )}
      {...props}
    />
  );
}
