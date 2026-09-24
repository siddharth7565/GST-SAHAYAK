import * as React from "react";
import { cn } from "../../lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-lg border border-gst-border bg-white px-3 py-2 text-sm text-gst-dark placeholder:text-gst-muted/70 focus:outline-none focus:ring-2 focus:ring-gst-orange focus:border-gst-orange disabled:cursor-not-allowed disabled:opacity-50 shadow-xs transition-colors",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
