import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { fetchDemandPredictions, fetchRetrainStatus, triggerRetrain } from "@/lib/api";
import { DashboardLayout, useDashboard } from "@/components/dashboard/DashboardLayout";
import { ChartCard } from "@/components/dashboard/ChartCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Loader2, RefreshCw, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { useEffect, useRef } from "react";

const PAGE_SIZE = 20;

function DemandContent() {
  const { filters } = useDashboard();
  const { data, isLoading } = useQuery({ queryKey: ["demand-predictions"], queryFn: () => fetchDemandPredictions(200) });
  const { data: retrainData, refetch: refetchRetrain } = useQuery({ queryKey: ["retrain-status"], queryFn: fetchRetrainStatus });

  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isRetraining, setIsRetraining] = useState(false);

  const retrainMutation = useMutation({
    mutationFn: triggerRetrain,
    onSuccess: () => {
      toast.success("Retrain initiated");
      setIsRetraining(true);
    },
    onError: () => toast.error("Failed to trigger retrain"),
  });

  // Poll retrain status
  useEffect(() => {
    if (isRetraining) {
      pollingRef.current = setInterval(async () => {
        const result = await refetchRetrain();
        const s = result.data?.status;
        if (s === "completed" || s === "failed") {
          setIsRetraining(false);
          clearInterval(pollingRef.current!);
          toast(s === "completed" ? "Model retrained successfully" : "Retrain failed");
        }
      }, 5000);
    }
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, [isRetraining, refetchRetrain]);

  // Aggregate chart data (daily avg predicted vs actual)
  const chartData = useMemo(() => {
    if (!data) return [];
    const byDate: Record<string, { predicted: number[]; actual: number[] }> = {};
    data.predictions.forEach((p) => {
      if (!byDate[p.date]) byDate[p.date] = { predicted: [], actual: [] };
      byDate[p.date].predicted.push(p.predicted_demand);
      if (p.actual_demand !== null) byDate[p.date].actual.push(p.actual_demand);
    });
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, v]) => ({
        date,
        predicted: Math.round(v.predicted.reduce((a, b) => a + b, 0) / v.predicted.length),
        actual: v.actual.length ? Math.round(v.actual.reduce((a, b) => a + b, 0) / v.actual.length) : null,
      }));
  }, [data]);

  // Filtered + paginated table
  const filtered = useMemo(() => {
    if (!data) return [];
    return data.predictions.filter((p) => {
      if (filters.store_id && !p.store_id.toLowerCase().includes(filters.store_id.toLowerCase())) return false;
      if (filters.product_id && !p.product_id.toLowerCase().includes(filters.product_id.toLowerCase())) return false;
      if (search && !`${p.store_id} ${p.product_id} ${p.date}`.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [data, filters, search]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const pageData = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const statusIcon = retrainData?.status === "completed" ? <CheckCircle2 className="h-4 w-4 text-emerald-500" /> :
    retrainData?.status === "failed" ? <XCircle className="h-4 w-4 text-destructive" /> :
    retrainData?.status === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : null;

  return (
    <div className="space-y-6">
      {/* Chart */}
      <ChartCard title="Demand Trend — Predicted vs Actual" loading={isLoading}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} className="text-muted-foreground" />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="predicted" stroke="hsl(222, 47%, 11%)" strokeWidth={2} dot={{ r: 4 }} name="Predicted" />
            <Line type="monotone" dataKey="actual" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} name="Actual" connectNulls={true} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid grid-cols-12 gap-4">
        {/* Retrain Panel */}
        <Card className="col-span-4 rounded-xl">
          <CardHeader className="pb-2">
            <CardTitle className="text-base font-semibold">Model Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              {statusIcon}
              <span className="text-sm capitalize font-medium">{retrainData?.status ?? "—"}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div><span className="text-muted-foreground">Version:</span> <Badge variant="secondary" className="font-mono ml-1">{retrainData?.model_version}</Badge></div>
              <div><span className="text-muted-foreground">RMSE:</span> <span className="font-mono ml-1">{retrainData?.rmse?.toFixed(2) ?? "—"}</span></div>
              <div><span className="text-muted-foreground">R²:</span> <span className="font-mono ml-1">{retrainData?.r2?.toFixed(3) ?? "—"}</span></div>
              <div><span className="text-muted-foreground">Last Run:</span> <span className="text-xs ml-1">{retrainData?.last_run ? new Date(retrainData.last_run).toLocaleString() : "—"}</span></div>
            </div>
            <Button onClick={() => retrainMutation.mutate()} disabled={isRetraining || retrainMutation.isPending} className="w-full mt-2">
              {isRetraining ? <><Loader2 className="h-4 w-4 animate-spin mr-2" /> Retraining…</> : <><RefreshCw className="h-4 w-4 mr-2" /> Retrain Model</>}
            </Button>
          </CardContent>
        </Card>

        {/* Data Table */}
        <Card className="col-span-8 rounded-xl">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Predictions</CardTitle>
              <Input placeholder="Search…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(0); }} className="w-48 h-8 text-sm" aria-label="Search predictions" />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {pageData.length > 0 ? (
              <>
                <div className="max-h-[350px] overflow-auto">
                  <Table>
                    <TableHeader className="sticky top-0 bg-background z-10">
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Store</TableHead>
                        <TableHead>Product</TableHead>
                        <TableHead className="text-right">Predicted</TableHead>
                        <TableHead className="text-right">Actual</TableHead>
                        <TableHead className="text-right">Confidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {pageData.map((r, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-xs">{r.date}</TableCell>
                          <TableCell className="font-mono text-xs">{r.store_id}</TableCell>
                          <TableCell className="font-mono text-xs">{r.product_id}</TableCell>
                          <TableCell className="text-right">{r.predicted_demand}</TableCell>
                          <TableCell className="text-right">{r.actual_demand ?? "—"}</TableCell>
                          <TableCell className="text-right">{(r.confidence * 100).toFixed(0)}%</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
                <div className="flex items-center justify-between px-4 py-2 border-t text-sm text-muted-foreground">
                  <span>{filtered.length} rows</span>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Prev</Button>
                    <span className="flex items-center px-2">{page + 1}/{totalPages}</span>
                    <Button variant="ghost" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>Next</Button>
                  </div>
                </div>
              </>
            ) : (
              <EmptyState message="No predictions found" />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function DemandPage() {
  return (
    <DashboardLayout title="Demand">
      <DemandContent />
    </DashboardLayout>
  );
}
