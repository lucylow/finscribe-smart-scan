import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { 
  Activity, 
  DollarSign, 
  Users, 
  FileText, 
  TrendingUp, 
  AlertCircle,
  CheckCircle,
  Clock,
  Zap
} from "lucide-react";

interface DashboardData {
  overview: {
    documentsProcessed: number;
    mrr: number;
    activeUsers: number;
    accuracy: number;
    documentsRemaining: number;
    quota: number;
  };
  usage: Array<{
    month: string;
    documents: number;
    apiCalls: number;
  }>;
  subscription: {
    tier: string;
    billingCycle: string;
    nextBillingDate: string;
    monthlyPrice: number;
    status: string;
  };
  recentActivity: Array<{
    time: string;
    user: string;
    action: string;
    document?: string;
  }>;
  usageAlerts?: Array<{
    type: string;
    title: string;
    message: string;
    action?: string;
  }>;
}

const SaaSDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    // Real-time updates every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      // In production, this would call your API
      // const response = await fetch(`/api/v1/dashboard`);
      // const data = await response.json();
      
      // Mock data for demonstration
      const mockData: DashboardData = {
        overview: {
          documentsProcessed: 1247,
          mrr: 199,
          activeUsers: 8,
          accuracy: 98.5,
          documentsRemaining: 3753,
          quota: 5000,
        },
        usage: [
          { month: "Jan", documents: 800, apiCalls: 1200 },
          { month: "Feb", documents: 950, apiCalls: 1450 },
          { month: "Mar", documents: 1100, apiCalls: 1650 },
          { month: "Apr", documents: 1247, apiCalls: 1890 },
        ],
        subscription: {
          tier: "Growth",
          billingCycle: "monthly",
          nextBillingDate: "2025-02-15",
          monthlyPrice: 199,
          status: "active",
        },
        recentActivity: [
          { time: "2 min ago", user: "John Doe", action: "processed invoice", document: "invoice_123.pdf" },
          { time: "15 min ago", user: "Jane Smith", action: "exported batch", document: "batch_456.csv" },
          { time: "1 hour ago", user: "John Doe", action: "integrated QuickBooks" },
        ],
        usageAlerts: [
          { type: "warning", title: "API Usage", message: "You've used 75% of your monthly API quota" },
        ],
      };
      
      setDashboardData(mockData);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
          <p className="mt-2 text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return <div>Error loading dashboard</div>;
  }

  const usagePercent = dashboardData.overview.quota > 0
    ? (dashboardData.overview.documentsProcessed / dashboardData.overview.quota) * 100
    : 0;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">FinScribe Dashboard</h1>
          <p className="text-muted-foreground mt-1">Welcome back! Here's your overview.</p>
        </div>
        <Badge variant={dashboardData.subscription.status === "active" ? "default" : "secondary"}>
          {dashboardData.subscription.tier} • ${dashboardData.subscription.monthlyPrice}/month
        </Badge>
      </div>

      {/* Usage Alerts */}
      {dashboardData.usageAlerts && dashboardData.usageAlerts.length > 0 && (
        <div className="space-y-2">
          {dashboardData.usageAlerts.map((alert, index) => (
            <div
              key={index}
              className={`flex items-center gap-2 p-3 rounded-lg border ${
                alert.type === "warning" 
                  ? "bg-yellow-50 border-yellow-200 dark:bg-yellow-900/20 dark:border-yellow-800"
                  : "bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800"
              }`}
            >
              <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
              <div className="flex-1">
                <strong>{alert.title}</strong>: {alert.message}
              </div>
              {alert.action && (
                <Button variant="outline" size="sm">
                  {alert.action}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Documents Processed</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.overview.documentsProcessed.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {dashboardData.overview.documentsRemaining.toLocaleString()} remaining this month
            </p>
            <Progress value={usagePercent} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {usagePercent.toFixed(1)}% of quota used
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Current MRR</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${dashboardData.overview.mrr.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              +8% from last month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.overview.activeUsers}</div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              +3 this week
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Processing Accuracy</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboardData.overview.accuracy}%</div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
              <TrendingUp className="h-3 w-3 text-green-500" />
              +2% improvement
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Details */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Monthly Usage</CardTitle>
            <CardDescription>Documents and API calls over time</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dashboardData.usage.map((month, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{month.month}</span>
                    <span className="text-muted-foreground">
                      {month.documents} docs • {month.apiCalls} API calls
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1 bg-blue-100 dark:bg-blue-900/30 rounded" style={{ height: '8px', width: `${(month.documents / 1500) * 100}%` }} />
                    <div className="flex-1 bg-green-100 dark:bg-green-900/30 rounded" style={{ height: '8px', width: `${(month.apiCalls / 2000) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Subscription Details</CardTitle>
            <CardDescription>Current plan and billing information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Tier:</span>
                <span className="font-medium">{dashboardData.subscription.tier}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Billing Cycle:</span>
                <span className="font-medium capitalize">{dashboardData.subscription.billingCycle}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Next Billing:</span>
                <span className="font-medium">{new Date(dashboardData.subscription.nextBillingDate).toLocaleDateString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Monthly Price:</span>
                <span className="font-medium">${dashboardData.subscription.monthlyPrice}</span>
              </div>
            </div>
            <Button className="w-full" variant="outline">
              Manage Subscription
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest actions from your team</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dashboardData.recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center gap-4 pb-4 border-b last:border-0">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Activity className="h-4 w-4 text-primary" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{activity.user}</p>
                  <p className="text-sm text-muted-foreground">
                    {activity.action}
                    {activity.document && <span className="ml-1 font-mono text-xs">({activity.document})</span>}
                  </p>
                </div>
                <div className="flex-shrink-0 text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {activity.time}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SaaSDashboard;


