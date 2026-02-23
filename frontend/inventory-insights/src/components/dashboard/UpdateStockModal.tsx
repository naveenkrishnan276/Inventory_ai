import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { updateStock } from "@/lib/api";
import { toast } from "sonner";

interface UpdateStockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function UpdateStockModal({ open, onOpenChange, onSuccess }: UpdateStockModalProps) {
  const [storeId, setStoreId] = useState("");
  const [productId, setProductId] = useState("");
  const [stock, setStock] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!storeId.trim() || !productId.trim()) {
      toast.error("Store ID and Product ID are required");
      return;
    }
    const stockNum = Number(stock);
    if (isNaN(stockNum) || stockNum < 0) {
      toast.error("Stock must be a non-negative number");
      return;
    }
    setLoading(true);
    try {
      await updateStock({ store_id: storeId.trim(), product_id: productId.trim(), current_stock: stockNum });
      toast.success("Stock updated successfully");
      onOpenChange(false);
      setStoreId("");
      setProductId("");
      setStock("");
      onSuccess();
    } catch {
      toast.error("Failed to update stock");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Update Stock</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="store-id">Store ID</Label>
            <Input id="store-id" value={storeId} onChange={(e) => setStoreId(e.target.value)} placeholder="e.g. S001" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="product-id">Product ID</Label>
            <Input id="product-id" value={productId} onChange={(e) => setProductId(e.target.value)} placeholder="e.g. P101" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="current-stock">Current Stock</Label>
            <Input id="current-stock" type="number" min={0} value={stock} onChange={(e) => setStock(e.target.value)} placeholder="0" required />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={loading}>
              {loading ? "Updating…" : "Update Stock"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
