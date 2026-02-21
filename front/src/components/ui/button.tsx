import * as React from "react";
import { cn } from "@/lib/utils";

const base =
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50";

const variants: Record<string, string> = {
  default: "bg-zinc-900 text-zinc-50 shadow hover:bg-zinc-800",
  destructive: "bg-red-600 text-white shadow-sm hover:bg-red-500",
  outline:
    "border border-zinc-200 bg-white shadow-sm hover:bg-zinc-100 hover:text-zinc-900",
  secondary: "bg-zinc-100 text-zinc-900 shadow-sm hover:bg-zinc-200",
  ghost: "hover:bg-zinc-100 hover:text-zinc-900",
  link: "text-zinc-900 underline-offset-4 hover:underline",
};

const sizes: Record<string, string> = {
  default: "h-10 px-4 py-2",
  sm: "h-9 rounded-md px-3 text-xs",
  lg: "h-11 rounded-lg px-8",
  icon: "h-10 w-10",
};

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    return (
      <button
        className={cn(base, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
