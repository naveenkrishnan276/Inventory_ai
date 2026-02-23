import { useState, createContext, useContext } from "react";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "./AppSidebar";
import { FilterBar } from "./FilterBar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import type { GlobalFilters } from "@/lib/types";
import { useQueryClient } from "@tanstack/react-query";

interface DashboardContextValue {
  filters: GlobalFilters;
  setFilters: (f: GlobalFilters) => void;
}

const DashboardContext = createContext<DashboardContextValue | null>(null);
export const useDashboard = () => {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used inside DashboardLayout");
  return ctx;
};

export function DashboardLayout({ children, title }: { children: React.ReactNode; title: string }) {
  const [filters, setFilters] = useState<GlobalFilters>({
    store_id: "",
    product_id: "",
    date_range: [null, null],
    risk_level: "ALL",
  });
  const queryClient = useQueryClient();
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const handleRefresh = () => {
    queryClient.invalidateQueries();
    setLastRefresh(new Date());
  };

  return (
    <DashboardContext.Provider value={{ filters, setFilters }}>
      <SidebarProvider>
        <div className="min-h-screen flex w-full bg-muted/30">
          <AppSidebar />
          <div className="flex-1 flex flex-col min-w-0">
            {/* Top Header */}
            <header className="flex items-center justify-between border-b border-border bg-background px-6 py-3">
              <div className="flex items-center gap-3">
                <SidebarTrigger className="-ml-1" />
                <h1 className="text-xl font-bold text-foreground">{title}</h1>
                <Badge variant="secondary" className="text-xs font-mono">v2.4.1</Badge>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">
                  Last refresh: {lastRefresh.toLocaleTimeString()}
                </span>
                <Button variant="outline" size="sm" onClick={handleRefresh} aria-label="Refresh data">
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>
            </header>
            {/* Filter Bar */}
            <FilterBar filters={filters} onChange={setFilters} />
            {/* Page Content */}
            <main className="flex-1 overflow-auto p-6">
              {children}
            </main>
          </div>
        </div>
      </SidebarProvider>
    </DashboardContext.Provider>
  );
}
