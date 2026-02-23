import { Badge } from "@/components/ui/badge";
import type { ReorderStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusStyles: Record<ReorderStatus, string> = {
  pending: "bg-muted text-muted-foreground border-border",
  created: "bg-blue-100 text-blue-800 border-blue-200",
  confirmed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  failed: "bg-red-100 text-red-800 border-red-200",
};

export function StatusBadge({ status, className }: { status: ReorderStatus; className?: string }) {
  return (
    <Badge variant="outline" className={cn("font-medium text-xs capitalize", statusStyles[status], className)}>
      {status}
    </Badge>
  );
}
