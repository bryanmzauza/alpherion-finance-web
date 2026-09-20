import type { InputHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & {
  id: string;
  label: ReactNode;
};

// Nunca vem pré-marcado (LGPD art. 8): `defaultChecked` não é aceito.
export function Checkbox({ id, label, className, ...props }: CheckboxProps) {
  return (
    <div className={cn("flex items-start gap-3", className)}>
      <input
        id={id}
        type="checkbox"
        className="mt-1 h-5 w-5 shrink-0 cursor-pointer appearance-none rounded border border-navy-3 bg-navy-2 checked:border-gold checked:bg-gold checked:bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 20 20%22><path fill=%22%230B192C%22 d=%22M7.6 14.2 3.4 10l1.4-1.4 2.8 2.8 7.6-7.6L16.6 5z%22/></svg>')] checked:bg-center checked:bg-no-repeat"
        {...props}
      />
      <label htmlFor={id} className="cursor-pointer text-table text-ice-70">
        {label}
      </label>
    </div>
  );
}
