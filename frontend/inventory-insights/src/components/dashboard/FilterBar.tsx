import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { GlobalFilters, RiskLevel } from "@/lib/types";

interface FilterBarProps {
  filters: GlobalFilters;
  onChange: (filters: GlobalFilters) => void;
}

const riskOptions: Array<RiskLevel | "ALL"> = ["ALL", "LOW", "MEDIUM", "HIGH", "CRITICAL"];

export function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="sticky top-0 z-10 flex items-center gap-3 bg-background border-b border-border px-6 py-3">
      <Input
        placeholder="Store ID"
        value={filters.store_id}
        onChange={(e) => onChange({ ...filters, store_id: e.target.value })}
        className="w-36 h-9 text-sm"
        aria-label="Filter by store"
      />
      <Input
        placeholder="Product ID"
        value={filters.product_id}
        onChange={(e) => onChange({ ...filters, product_id: e.target.value })}
        className="w-36 h-9 text-sm"
        aria-label="Filter by product"
      />
      <Select
        value={filters.risk_level}
        onValueChange={(v) => onChange({ ...filters, risk_level: v as RiskLevel | "ALL" })}
      >
        <SelectTrigger className="w-36 h-9 text-sm" aria-label="Filter by risk level">
          <SelectValue placeholder="Risk Level" />
        </SelectTrigger>
        <SelectContent>
          {riskOptions.map((r) => (
            <SelectItem key={r} value={r}>
              {r === "ALL" ? "All Risks" : r}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
