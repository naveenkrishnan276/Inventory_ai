import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchHomeSummary } from "@/lib/api";
import { DashboardLayout, useDashboard } from "@/components/dashboard/DashboardLayout";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { RiskBadge } from "@/components/dashboard/RiskBadge";
import { ChartCard } from "@/components/dashboard/ChartCard";
import { UpdateStockModal } from "@/components/dashboard/UpdateStockModal";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Package, AlertTriangle, DollarSign, TrendingDown, Edit } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const RISK_COLORS = { LOW: "#10b981", MEDIUM: "#f59e0b", HIGH: "#f97316", CRITICAL: "#ef4444" };

function HomeContent() {
  const { filters } = useDashboard();
  const { data, isLoading, refetch } = useQuery({ queryKey: ["home-summary"], queryFn: fetchHomeSummary });
  const [stockModalOpen, setStockModalOpen] = useState(false);

  const filteredHealth = data?.inventory_health.filter((row) => {
    if (filters.store_id && !row.store_id.toLowerCase().includes(filters.store_id.toLowerCase())) return false;
    if (filters.product_id && !row.product_id.toLowerCase().includes(filters.product_id.toLowerCase())) return false;
    if (filters.risk_level !== "ALL" && row.risk_level !== filters.risk_level) return false;
    return true;
  });

  const donutData = data
    ? Object.entries(data.risk_distribution).map(([key, value]) => ({ name: key, value }))
    : [];

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <KpiCard title="Total Inventory" value={data?.total_inventory_units.toLocaleString() ?? "—"} icon={Package} loading={isLoading} />
        <KpiCard title="At-Risk Products" value={data?.at_risk_products ?? "—"} icon={AlertTriangle} loading={isLoading} />
        <KpiCard title="Today's Revenue" value={data ? `$${data.today_sales_revenue.toLocaleString()}` : "—"} icon={DollarSign} loading={isLoading} />
        <KpiCard title="Stockout Risk" value={data ? `${data.stockout_risk_percent}%` : "—"} icon={TrendingDown} loading={isLoading} />
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Inventory Health Table */}
        <Card className="col-span-8 rounded-xl">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Inventory Health</CardTitle>
              <Button size="sm" onClick={() => setStockModalOpen(true)}>
                <Edit className="h-4 w-4 mr-1" /> Update Stock
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {filteredHealth && filteredHealth.length > 0 ? (
              <div className="max-h-[400px] overflow-auto">
                <Table>
                  <TableHeader className="sticky top-0 bg-background z-10">
                    <TableRow>
                      <TableHead>Store</TableHead>
                      <TableHead>Product</TableHead>
                      <TableHead className="text-right">Stock</TableHead>
                      <TableHead className="text-right">Daily Demand</TableHead>
                      <TableHead className="text-right">Days Cover</TableHead>
                      <TableHead>Risk</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredHealth.map((row) => (
                      <TableRow key={`${row.store_id}-${row.product_id}`}>
                        <TableCell className="font-mono text-sm">{row.store_id}</TableCell>
                        <TableCell className="font-mono text-sm">{row.product_id}</TableCell>
                        <TableCell className="text-right">{row.current_stock}</TableCell>
                        <TableCell className="text-right">{row.predicted_daily_demand}</TableCell>
                        <TableCell className="text-right">{row.days_of_cover.toFixed(1)}</TableCell>
                        <TableCell><RiskBadge level={row.risk_level} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <EmptyState message="No inventory data matching filters" />
            )}
          </CardContent>
        </Card>

        {/* Right column */}
        <div className="col-span-4 space-y-4">
          {/* Risk Donut */}
          <ChartCard title="Risk Snapshot" loading={isLoading}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={donutData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={2}>
                  {donutData.map((entry) => (
                    <Cell key={entry.name} fill={RISK_COLORS[entry.name as keyof typeof RISK_COLORS]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-4 mt-2">
              {donutData.map((d) => (
                <div key={d.name} className="flex items-center gap-1.5 text-xs">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[d.name as keyof typeof RISK_COLORS] }} />
                  {d.name}: {d.value}
                </div>
              ))}
            </div>
          </ChartCard>

          {/* Top At-Risk */}
          <Card className="rounded-xl">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold">Top At-Risk</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {data?.top_at_risk && data.top_at_risk.length > 0 ? (
                <Table>
                  <TableBody>
                    {data.top_at_risk.map((item) => (
                      <TableRow key={`${item.store_id}-${item.product_id}`}>
                        <TableCell className="font-mono text-xs py-2">{item.product_id}</TableCell>
                        <TableCell className="text-xs py-2">{item.days_of_cover.toFixed(1)}d</TableCell>
                        <TableCell className="py-2"><RiskBadge level={item.risk_level} /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <EmptyState />
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <UpdateStockModal open={stockModalOpen} onOpenChange={setStockModalOpen} onSuccess={() => refetch()} />
    </div>
  );
}

export default function HomePage() {
  return (
    <DashboardLayout title="Home">
      <HomeContent />
    </DashboardLayout>
  );
}
