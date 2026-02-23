import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchAnalyticsTrends } from "@/lib/api";
import { DashboardLayout } from "@/components/dashboard/DashboardLayout";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { ChartCard } from "@/components/dashboard/ChartCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DollarSign, TrendingUp, RotateCcw, AlertTriangle, ArrowUp, ArrowDown, Minus } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const RISK_COLORS = { LOW: "#10b981", MEDIUM: "#f59e0b", HIGH: "#f97316", CRITICAL: "#ef4444" };
const RANGE_OPTIONS = [7, 14, 30] as const;

export default function AnalyticsPage() {
  const [rangeDays, setRangeDays] = useState<number>(7);
  const { data, isLoading } = useQuery({ queryKey: ["analytics", rangeDays], queryFn: () => fetchAnalyticsTrends(rangeDays) });

  const salesData = data?.sales_trend.slice(-rangeDays) ?? [];
  const demandData = data?.demand_trend.slice(-rangeDays) ?? [];
  const reorderData = data?.reorder_trend.slice(-rangeDays) ?? [];
  const riskDonut = data ? Object.entries(data.risk_distribution).map(([name, value]) => ({ name, value })) : [];

  const trendIcon = (t: string) => t === "up" ? <ArrowUp className="h-3.5 w-3.5 text-emerald-500" /> : t === "down" ? <ArrowDown className="h-3.5 w-3.5 text-destructive" /> : <Minus className="h-3.5 w-3.5 text-muted-foreground" />;

  return (
    <DashboardLayout title="Analytics">
      <div className="space-y-6">
        {/* Range Toggle */}
        <div className="flex gap-1">
          {RANGE_OPTIONS.map((r) => (
            <Button key={r} variant={rangeDays === r ? "default" : "outline"} size="sm" onClick={() => setRangeDays(r)}>
              {r}d
            </Button>
          ))}
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-4 gap-4">
          <KpiCard title="Avg Daily Sales" value={data?.avg_daily_sales.toFixed(1) ?? "—"} icon={DollarSign} loading={isLoading} />
          <KpiCard title="Avg Daily Demand" value={data?.avg_daily_demand.toFixed(1) ?? "—"} icon={TrendingUp} loading={isLoading} />
          <KpiCard title="Reorder Events (7d)" value={data?.reorder_events_count ?? "—"} icon={RotateCcw} loading={isLoading} />
          <KpiCard title="Critical SKUs" value={data?.critical_sku_count ?? "—"} icon={AlertTriangle} loading={isLoading} />
        </div>

        {/* Charts grid */}
        <div className="grid grid-cols-2 gap-4">
          <ChartCard title="Sales Rate Trend" loading={isLoading}>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={salesData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="hsl(222, 47%, 11%)" fill="hsl(222, 47%, 11%)" fillOpacity={0.1} strokeWidth={2} name="Sales" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Demand Rate Trend" loading={isLoading}>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={demandData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.1} strokeWidth={2} name="Demand" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Reorder Trend" loading={isLoading}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={reorderData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(222, 47%, 11%)" radius={[4, 4, 0, 0]} name="Reorders" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Risk Distribution" loading={isLoading}>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={riskDonut} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={2}>
                  {riskDonut.map((e) => <Cell key={e.name} fill={RISK_COLORS[e.name as keyof typeof RISK_COLORS]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex justify-center gap-3 mt-1">
              {riskDonut.map((d) => (
                <div key={d.name} className="flex items-center gap-1 text-xs">
                  <div className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLORS[d.name as keyof typeof RISK_COLORS] }} />
                  {d.name}
                </div>
              ))}
            </div>
          </ChartCard>
        </div>

        {/* Top Movers */}
        <Card className="rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Top Movers</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {data?.top_movers && data.top_movers.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Product</TableHead>
                    <TableHead>Store</TableHead>
                    <TableHead className="text-right">Avg Daily Sales</TableHead>
                    <TableHead>Trend</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.top_movers.map((m) => (
                    <TableRow key={`${m.store_id}-${m.product_id}`}>
                      <TableCell className="font-mono text-sm">{m.product_id}</TableCell>
                      <TableCell className="font-mono text-sm">{m.store_id}</TableCell>
                      <TableCell className="text-right">{m.avg_daily_sales.toFixed(1)}</TableCell>
                      <TableCell><div className="flex items-center gap-1">{trendIcon(m.trend)} <span className="text-xs capitalize">{m.trend}</span></div></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <EmptyState message="No top mover data" />
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
