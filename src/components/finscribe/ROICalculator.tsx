import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Calculator, TrendingUp, DollarSign } from "lucide-react";
import { toast } from "sonner";

interface ROIResult {
  invoices_per_month: number;
  manual_cost_per_invoice: number;
  autom_cost_per_invoice: number;
  monthly_fixed_cost: number;
  manual_total: number;
  autom_total: number;
  monthly_savings: number;
  savings_pct: number;
  annual_savings: number;
  payback_months: number;
}

export default function ROICalculator() {
  const [invoices, setInvoices] = useState<number>(1000);
  const [manualCost, setManualCost] = useState<number>(30);
  const [autoCost, setAutoCost] = useState<number>(0.15);
  const [fixedCost, setFixedCost] = useState<number>(200);
  const [initialCost, setInitialCost] = useState<number>(0);
  const [result, setResult] = useState<ROIResult | null>(null);
  const [loading, setLoading] = useState(false);

  const calculateROI = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        invoices_per_month: invoices.toString(),
        manual_cost_per_invoice: manualCost.toString(),
        autom_cost_per_invoice: autoCost.toString(),
        monthly_fixed_cost: fixedCost.toString(),
        initial_cost: initialCost.toString(),
      });

      const resp = await fetch(`/api/v1/roi?${params}`);
      if (!resp.ok) {
        throw new Error("Failed to calculate ROI");
      }
      const data = await resp.json();
      setResult(data);
      toast.success("ROI calculated successfully");
    } catch (error) {
      console.error("ROI calculation error:", error);
      toast.error("Failed to calculate ROI. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Calculator className="h-5 w-5" />
          <CardTitle>ROI Calculator</CardTitle>
        </div>
        <CardDescription>
          Calculate your potential savings with FinScribe automation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="invoices">Invoices per month</Label>
            <Input
              id="invoices"
              type="number"
              min="0"
              value={invoices}
              onChange={(e) => setInvoices(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="manual-cost">Manual cost per invoice ($)</Label>
            <Input
              id="manual-cost"
              type="number"
              min="0"
              step="0.01"
              value={manualCost}
              onChange={(e) => setManualCost(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="auto-cost">Automated cost per invoice ($)</Label>
            <Input
              id="auto-cost"
              type="number"
              min="0"
              step="0.01"
              value={autoCost}
              onChange={(e) => setAutoCost(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="fixed-cost">Monthly fixed cost ($)</Label>
            <Input
              id="fixed-cost"
              type="number"
              min="0"
              step="0.01"
              value={fixedCost}
              onChange={(e) => setFixedCost(Number(e.target.value))}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <Label htmlFor="initial-cost">One-time setup cost ($) - Optional</Label>
            <Input
              id="initial-cost"
              type="number"
              min="0"
              step="0.01"
              value={initialCost}
              onChange={(e) => setInitialCost(Number(e.target.value))}
            />
          </div>
        </div>

        <Button onClick={calculateROI} className="w-full" disabled={loading}>
          {loading ? "Calculating..." : "Calculate ROI"}
        </Button>

        {result && (
          <div className="mt-6 p-4 bg-muted rounded-lg space-y-3 border">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <h4 className="font-semibold">Results</h4>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-muted-foreground">Manual Total</div>
                <div className="font-semibold">${result.manual_total.toLocaleString()}/month</div>
              </div>
              <div>
                <div className="text-muted-foreground">Automated Total</div>
                <div className="font-semibold">${result.autom_total.toLocaleString()}/month</div>
              </div>
              <div className="col-span-2 pt-2 border-t">
                <div className="flex items-center gap-2">
                  <DollarSign className="h-4 w-4 text-green-600" />
                  <div>
                    <div className="text-muted-foreground">Monthly Savings</div>
                    <div className="text-lg font-bold text-green-600">
                      ${result.monthly_savings.toLocaleString()}/month
                    </div>
                    <div className="text-xs text-muted-foreground">
                      ({result.savings_pct.toFixed(1)}% reduction)
                    </div>
                  </div>
                </div>
              </div>
              <div className="col-span-2">
                <div className="text-muted-foreground">Annual Savings</div>
                <div className="font-semibold text-green-600">
                  ${result.annual_savings.toLocaleString()}/year
                </div>
              </div>
              {result.payback_months > 0 && (
                <div className="col-span-2">
                  <div className="text-muted-foreground">Payback Time</div>
                  <div className="font-semibold">
                    {result.payback_months.toFixed(1)} months
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

