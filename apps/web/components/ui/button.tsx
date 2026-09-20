import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "lg";

// Classes exportadas para usar em <Link> (sem asChild): <Link className={buttonVariants({...})}>.
export function buttonVariants({ variant = "primary", size = "md" }: { variant?: Variant; size?: Size } = {}) {
  return cn(
    "inline-flex items-center justify-center gap-2 rounded-md font-medium whitespace-nowrap transition-colors",
    "disabled:pointer-events-none disabled:opacity-60",
    size === "md" ? "h-11 px-5 text-body" : "h-12 px-6 text-lg",
    variant === "primary" && "bg-gold text-navy hover:bg-gold-2",
    variant === "secondary" && "border border-navy-3 bg-navy-2 text-ice hover:border-gold hover:text-gold",
    variant === "ghost" && "text-ice-70 hover:text-ice",
  );
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size };

export function Button({ className, variant, size, type = "button", ...props }: ButtonProps) {
  return <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
