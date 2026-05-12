/**
 * HbTrendChart.test.jsx
 * Verify ReferenceLine props have y=11.9, 9.9, 8.0.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/react';

// ─── Capture ReferenceLine props ──────────────────────────────────────────────
const capturedReferenceLines = [];

vi.mock('recharts', () => ({
  ComposedChart: ({ children }) => React.createElement('div', { 'data-testid': 'composed-chart' }, children),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }) => React.createElement('div', null, children),
  Dot: () => null,
  ReferenceLine: (props) => {
    capturedReferenceLines.push(props);
    return null;
  },
}));

// Mock API client — return 3 data points so chart renders
vi.mock('../api/client.js', () => ({
  default: {
    get: vi.fn(() =>
      Promise.resolve({
        data: {
          trend: [
            { date: '2024-01-01', hgb: 12.5, severity_level: 'None' },
            { date: '2024-02-01', hgb: 10.5, severity_level: 'Mild' },
            { date: '2024-03-01', hgb: 8.5,  severity_level: 'Moderate' },
          ],
        },
      })
    ),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

import HbTrendChart from '../components/HbTrendChart.jsx';

describe('HbTrendChart — ReferenceLine thresholds', () => {
  beforeEach(() => {
    capturedReferenceLines.length = 0;
  });

  it('renders 3 ReferenceLine components', async () => {
    const { findByTestId } = render(<HbTrendChart username="testuser" />);
    // Wait for async data load
    await findByTestId('composed-chart');
    expect(capturedReferenceLines.length).toBe(3);
  });

  it('has a ReferenceLine at y=11.9 (Mild threshold)', async () => {
    const { findByTestId } = render(<HbTrendChart username="testuser" />);
    await findByTestId('composed-chart');
    const line = capturedReferenceLines.find((l) => l.y === 11.9);
    expect(line).toBeDefined();
    expect(line.stroke).toBe('#f59e0b');
  });

  it('has a ReferenceLine at y=9.9 (Moderate threshold)', async () => {
    const { findByTestId } = render(<HbTrendChart username="testuser" />);
    await findByTestId('composed-chart');
    const line = capturedReferenceLines.find((l) => l.y === 9.9);
    expect(line).toBeDefined();
    expect(line.stroke).toBe('#f97316');
  });

  it('has a ReferenceLine at y=8.0 (Severe threshold)', async () => {
    const { findByTestId } = render(<HbTrendChart username="testuser" />);
    await findByTestId('composed-chart');
    const line = capturedReferenceLines.find((l) => l.y === 8.0);
    expect(line).toBeDefined();
    expect(line.stroke).toBe('#ef4444');
  });
});
