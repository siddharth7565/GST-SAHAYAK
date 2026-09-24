import * as React from "react";
import { cn } from "../../lib/utils";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[80px] w-full rounded-lg border border-gst-border bg-white px-3 py-2 text-sm text-gst-dark placeholder:text-gst-muted/70 focus:outline-none focus:ring-2 focus:ring-gst-orange focus:border-gst-orange disabled:cursor-not-allowed disabled:opacity-50 shadow-xs transition-colors resize-y",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
