import * as React from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning" | "destructive" | "info";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const base = "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-gst-orange select-none";
  const variants = {
    default: "bg-gst-orange/20 text-gst-orange-deep border border-gst-orange/40",
    secondary: "bg-gst-orange-light text-gst-dark border border-gst-border",
    outline: "border border-gst-border text-gst-dark bg-white",
    success: "bg-gst-green/15 text-gst-green border border-gst-green/30",
    warning: "bg-amber-100 text-amber-800 border border-amber-300",
    destructive: "bg-gst-red/15 text-gst-red border border-gst-red/30",
    info: "bg-blue-50 text-blue-700 border border-blue-200",
  };

  return (
    <div className={cn(base, variants[variant], className)} {...props} />
  );
}

export { Badge };
