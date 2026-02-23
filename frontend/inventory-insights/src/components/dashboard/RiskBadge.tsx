import { Badge } from "@/components/ui/badge";
import type { RiskLevel } from "@/lib/types";
import { cn } from "@/lib/utils";

const riskStyles: Record<RiskLevel, string> = {
  LOW: "bg-emerald-100 text-emerald-800 border-emerald-200",
  MEDIUM: "bg-amber-100 text-amber-800 border-amber-200",
  HIGH: "bg-orange-100 text-orange-800 border-orange-200",
  CRITICAL: "bg-red-100 text-red-800 border-red-200",
};

export function RiskBadge({ level, className }: { level: RiskLevel; className?: string }) {
  return (
    <Badge variant="outline" className={cn("font-semibold text-xs", riskStyles[level], className)}>
      {level}
    </Badge>
  );
}
