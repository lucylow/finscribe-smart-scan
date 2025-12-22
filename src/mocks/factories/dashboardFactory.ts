import { faker } from '@faker-js/faker';
import { MockDashboardMetrics } from '../types';

/**
 * Factory for creating mock dashboard metrics
 */
export const createMockDashboardMetrics = (): MockDashboardMetrics => {
  const documentsProcessed = faker.number.int({ min: 1000, max: 5000 });
  const quota = 5000;
  const averageProcessingTime = faker.number.float({ min: 1.2, max: 2.5, fractionDigits: 1 });
  const estimatedCostSavings = documentsProcessed * 20; // $20 per document manual cost
  
  // Generate usage data for last 4 months
  const months = ['Jan', 'Feb', 'Mar', 'Apr'];
  const usage = months.map((month, index) => ({
    month,
    documents: faker.number.int({ min: 800 + index * 100, max: 1200 + index * 100 }),
    apiCalls: faker.number.int({ min: 1200 + index * 150, max: 1800 + index * 150 }),
  }));

  // Generate accuracy over time
  const versions = ['v1.0', 'v1.1', 'v1.2', 'v1.3', 'v2.0'];
  const accuracyOverTime = versions.map((version, index) => ({
    version,
    date: `2024-0${index + 1}`,
    accuracy: faker.number.float({ min: 87 + index * 1.5, max: 95, fractionDigits: 1 }),
  }));

  // Generate error distribution
  const fieldTypes = ['Date', 'Line Item Total', 'Vendor Name', 'Tax Amount', 'Invoice Number', 'Subtotal'];
  const errorDistribution = fieldTypes.map(fieldType => ({
    fieldType,
    errorCount: faker.number.int({ min: 5, max: 50 }),
  })).sort((a, b) => b.errorCount - a.errorCount);

  // Generate automation metrics
  const fullyAutomated = faker.number.int({ min: 80, max: 95 });
  const humanInTheLoop = 100 - fullyAutomated;

  // Generate recent activity
  const recentActivity = Array.from({ length: 5 }, () => ({
    time: faker.helpers.arrayElement(['2 min ago', '15 min ago', '1 hour ago', '2 hours ago', '1 day ago']),
    user: faker.person.fullName(),
    action: faker.helpers.arrayElement([
      'processed invoice',
      'exported batch',
      'integrated QuickBooks',
      'reviewed validation',
      'updated settings',
    ]),
    document: faker.datatype.boolean() ? `invoice_${faker.string.alphanumeric(6)}.pdf` : undefined,
  }));

  return {
    overview: {
      documentsProcessed,
      averageProcessingTime,
      estimatedCostSavings,
      overallAccuracyScore: faker.number.float({ min: 92, max: 96, fractionDigits: 1 }),
      mrr: faker.number.int({ min: 150, max: 250 }),
      activeUsers: faker.number.int({ min: 5, max: 15 }),
      accuracy: faker.number.float({ min: 96, max: 99, fractionDigits: 1 }),
      documentsRemaining: quota - documentsProcessed,
      quota,
    },
    usage,
    accuracyOverTime,
    errorDistribution,
    automationMetrics: {
      humanInTheLoop,
      fullyAutomated,
    },
    subscription: {
      tier: faker.helpers.arrayElement(['Starter', 'Growth', 'Enterprise']),
      billingCycle: faker.helpers.arrayElement(['monthly', 'yearly']),
      nextBillingDate: faker.date.future({ years: 1 }).toISOString().split('T')[0],
      monthlyPrice: faker.number.int({ min: 99, max: 299 }),
      status: 'active',
    },
    recentActivity,
    usageAlerts: documentsProcessed > quota * 0.75 ? [
      {
        type: 'warning',
        title: 'API Usage',
        message: `You've used ${Math.round((documentsProcessed / quota) * 100)}% of your monthly API quota`,
      },
    ] : undefined,
  };
};

