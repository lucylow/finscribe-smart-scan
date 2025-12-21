import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download, FileJson, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function ExportPanel() {
  const [loading, setLoading] = useState<string | null>(null);

  const downloadFile = async (endpoint: string, filename: string, type: string) => {
    setLoading(type);
    try {
      const r = await fetch(`/api/v1/${endpoint}`);
      if (!r.ok) {
        const error = await r.json().catch(() => ({ error: "Export failed" }));
        throw new Error(error.error || "Export failed");
      }

      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      toast.success(`${type} exported successfully`);
    } catch (error) {
      console.error("Export error:", error);
      toast.error(`Failed to export ${type}. ${error instanceof Error ? error.message : ""}`);
    } finally {
      setLoading(null);
    }
  };

  const handleExportJSON = () => {
    downloadFile("exports/json", "finscribe_export.json", "JSON");
  };

  const handleExportCSV = () => {
    downloadFile("exports/csv", "finscribe_export.csv", "CSV");
  };

  const handleExportQuickBooks = () => {
    downloadFile("exports/quickbooks_csv", "finscribe_qb_export.csv", "QuickBooks CSV");
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Download className="h-5 w-5" />
          <CardTitle>Export Data</CardTitle>
        </div>
        <CardDescription>
          Export processed documents in various formats for integration
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button
          onClick={handleExportJSON}
          variant="outline"
          className="w-full justify-start"
          disabled={loading !== null}
        >
          {loading === "JSON" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileJson className="mr-2 h-4 w-4" />
          )}
          Download JSON (NDJSON)
        </Button>

        <Button
          onClick={handleExportCSV}
          variant="outline"
          className="w-full justify-start"
          disabled={loading !== null}
        >
          {loading === "CSV" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileSpreadsheet className="mr-2 h-4 w-4" />
          )}
          Download CSV
        </Button>

        <Button
          onClick={handleExportQuickBooks}
          variant="outline"
          className="w-full justify-start"
          disabled={loading !== null}
        >
          {loading === "QuickBooks CSV" ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <FileText className="mr-2 h-4 w-4" />
          )}
          Download QuickBooks CSV
        </Button>

        <div className="mt-4 p-3 bg-muted rounded-md text-xs text-muted-foreground">
          <p className="font-semibold mb-1">Tip:</p>
          <p>
            CSV files can be imported into Excel, Google Sheets, or accounting software.
            QuickBooks CSV is formatted for QuickBooks Online import.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

