import { cn } from "../../lib/utils";

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-gst-orange-light/50 border border-gst-border/30", className)}
      {...props}
    />
  );
}

export { Skeleton };
