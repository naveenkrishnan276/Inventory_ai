import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchReorderList } from "@/lib/api";
import { DashboardLayout, useDashboard } from "@/components/dashboard/DashboardLayout";
import { RiskBadge } from "@/components/dashboard/RiskBadge";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { toast } from "sonner";
import type { ReorderItem } from "@/lib/types";
import { FileText, Zap } from "lucide-react";

function ReorderContent() {
  const { filters } = useDashboard();
  const { data, isLoading } = useQuery({ queryKey: ["reorder-list"], queryFn: fetchReorderList });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [drawerItem, setDrawerItem] = useState<ReorderItem | null>(null);

  const items = useMemo(() => {
    if (!data) return [];
    return data.items.filter((item) => {
      // Default: show only HIGH + CRITICAL unless filter explicitly set
      if (filters.risk_level === "ALL") {
        if (item.risk_level !== "HIGH" && item.risk_level !== "CRITICAL") return false;
      } else if (item.risk_level !== filters.risk_level) return false;
      if (filters.store_id && !item.store_id.toLowerCase().includes(filters.store_id.toLowerCase())) return false;
      if (filters.product_id && !item.product_id.toLowerCase().includes(filters.product_id.toLowerCase())) return false;
      return true;
    });
  }, [data, filters]);

  const toggleSelect = (key: string) => {
    const next = new Set(selected);
    next.has(key) ? next.delete(key) : next.add(key);
    setSelected(next);
  };

  const selectAll = () => {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map((i) => `${i.store_id}-${i.product_id}`)));
  };

  const handleCreateDraft = (item: ReorderItem) => {
    toast.success(`Draft PO created for ${item.product_id} @ ${item.store_id}`);
  };

  const handleAutoConfirm = (item: ReorderItem) => {
    toast.success(`PO auto-confirmed for ${item.product_id} @ ${item.store_id}`);
  };

  const handleBulkDraft = () => {
    toast.success(`${selected.size} draft POs created`);
    setSelected(new Set());
  };

  return (
    <div className="space-y-4">
      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-primary/5 border border-primary/20 rounded-xl px-4 py-2">
          <span className="text-sm font-medium">{selected.size} selected</span>
          <Button size="sm" onClick={handleBulkDraft}><FileText className="h-4 w-4 mr-1" /> Bulk Draft PO</Button>
        </div>
      )}

      <Card className="rounded-xl">
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-semibold">Reorder Queue</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {items.length > 0 ? (
            <div className="overflow-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-background z-10">
                  <TableRow>
                    <TableHead className="w-10">
                      <Checkbox checked={selected.size === items.length && items.length > 0} onCheckedChange={selectAll} aria-label="Select all" />
                    </TableHead>
                    <TableHead>Store</TableHead>
                    <TableHead>Product</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead className="text-right">Reorder Qty</TableHead>
                    <TableHead>Seller</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => {
                    const key = `${item.store_id}-${item.product_id}`;
                    return (
                      <TableRow key={key} className="cursor-pointer" onClick={() => setDrawerItem(item)}>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Checkbox checked={selected.has(key)} onCheckedChange={() => toggleSelect(key)} aria-label={`Select ${key}`} />
                        </TableCell>
                        <TableCell className="font-mono text-sm">{item.store_id}</TableCell>
                        <TableCell className="font-mono text-sm">{item.product_id}</TableCell>
                        <TableCell><RiskBadge level={item.risk_level} /></TableCell>
                        <TableCell className="text-right">{item.recommended_reorder_quantity}</TableCell>
                        <TableCell className="text-sm">{item.seller_name}</TableCell>
                        <TableCell className="text-xs text-muted-foreground">{item.seller_contact}</TableCell>
                        <TableCell><StatusBadge status={item.status} /></TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <div className="flex gap-1">
                            <Button variant="outline" size="sm" onClick={() => handleCreateDraft(item)}>
                              <FileText className="h-3.5 w-3.5" />
                            </Button>
                            {item.auto_confirm_eligible && (
                              <Button variant="outline" size="sm" onClick={() => handleAutoConfirm(item)}>
                                <Zap className="h-3.5 w-3.5" />
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          ) : (
            <EmptyState message="No reorder items matching filters" />
          )}
        </CardContent>
      </Card>

      {/* Detail Drawer */}
      <Sheet open={!!drawerItem} onOpenChange={(o) => !o && setDrawerItem(null)}>
        <SheetContent className="sm:max-w-lg">
          {drawerItem && (
            <>
              <SheetHeader>
                <SheetTitle>Reorder Details</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <Detail label="Store" value={drawerItem.store_id} />
                  <Detail label="Product" value={drawerItem.product_id} />
                  <Detail label="Risk Level"><RiskBadge level={drawerItem.risk_level} /></Detail>
                  <Detail label="Status"><StatusBadge status={drawerItem.status} /></Detail>
                  <Detail label="Current Stock" value={drawerItem.current_stock.toString()} />
                  <Detail label="Daily Demand" value={drawerItem.predicted_daily_demand.toString()} />
                  <Detail label="Days of Cover" value={drawerItem.days_of_cover.toFixed(1)} />
                  <Detail label="Reorder Qty" value={drawerItem.recommended_reorder_quantity.toString()} />
                  <Detail label="Seller" value={drawerItem.seller_name} />
                  <Detail label="Contact" value={drawerItem.seller_contact} />
                  <Detail label="Auto Confirm" value={drawerItem.auto_confirm_eligible ? "Yes" : "No"} />
                  <Detail label="Last Reorder" value={drawerItem.last_reorder_date ?? "Never"} />
                </div>
                <div className="flex gap-2 pt-4">
                  <Button onClick={() => { handleCreateDraft(drawerItem); setDrawerItem(null); }}>
                    <FileText className="h-4 w-4 mr-2" /> Create Draft PO
                  </Button>
                  {drawerItem.auto_confirm_eligible && (
                    <Button variant="secondary" onClick={() => { handleAutoConfirm(drawerItem); setDrawerItem(null); }}>
                      <Zap className="h-4 w-4 mr-2" /> Auto Confirm
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Detail({ label, value, children }: { label: string; value?: string; children?: React.ReactNode }) {
  return (
    <div>
      <p className="text-muted-foreground text-xs">{label}</p>
      {children ?? <p className="font-medium mt-0.5">{value}</p>}
    </div>
  );
}

export default function ReorderPage() {
  return (
    <DashboardLayout title="Reorder">
      <ReorderContent />
    </DashboardLayout>
  );
}
