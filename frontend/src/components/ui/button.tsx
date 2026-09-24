import * as React from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "outline" | "ghost" | "destructive" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gst-orange disabled:pointer-events-none disabled:opacity-50 select-none cursor-pointer";
    
    const variants = {
      default: "bg-gst-orange text-gst-dark hover:bg-gst-orange-hover shadow-sm font-semibold",
      secondary: "bg-gst-orange-light text-gst-orange-deep hover:bg-gst-orange-verylight font-semibold border border-gst-orange/20",
      outline: "border border-gst-border bg-white text-gst-dark hover:bg-gst-orange-verylight hover:border-gst-orange/50",
      ghost: "text-gst-dark hover:bg-gst-orange-verylight hover:text-gst-orange-deep",
      destructive: "bg-gst-red text-white hover:bg-gst-red/90 shadow-sm",
      link: "text-gst-orange-deep underline-offset-4 hover:underline",
    };

    const sizes = {
      default: "h-10 px-4 py-2",
      sm: "h-8 rounded-md px-3 text-xs",
      lg: "h-11 rounded-lg px-6 text-base",
      icon: "h-9 w-9 p-0",
    };

    return (
      <button
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);
Button.displayName = "Button";

export { Button };
