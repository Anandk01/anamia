/**
 * PredictionResult.test.jsx
 * Snapshot tests for each severity level verifying correct badge color class.
 */

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PredictionResult from '../components/PredictionResult.jsx';

const makeResult = (severity, anemiaDetected = 1) => ({
  anemia_detected: anemiaDetected,
  severity_level: severity,
  anemia_type: 'Iron-Deficiency',
  anemia_confidence: 0.87,
  explanation: [
    { feature: 'HGB', direction: 'Low', shap_value: -0.45 },
    { feature: 'MCV', direction: 'Low', shap_value: -0.32 },
    { feature: 'MCH', direction: 'Low', shap_value: -0.21 },
  ],
});

describe('PredictionResult — severity badge colors', () => {
  it('renders None severity with emerald (green) badge', () => {
    render(<PredictionResult result={makeResult('None', 0)} />);
    const badge = screen.getByTestId('severity-badge');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/emerald/);
    expect(badge.textContent).toBe('None');
  });

  it('renders Mild severity with amber (yellow) badge', () => {
    render(<PredictionResult result={makeResult('Mild')} />);
    const badge = screen.getByTestId('severity-badge');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/amber/);
    expect(badge.textContent).toBe('Mild');
  });

  it('renders Moderate severity with orange badge', () => {
    render(<PredictionResult result={makeResult('Moderate')} />);
    const badge = screen.getByTestId('severity-badge');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/orange/);
    expect(badge.textContent).toBe('Moderate');
  });

  it('renders Severe severity with red badge', () => {
    render(<PredictionResult result={makeResult('Severe')} />);
    const badge = screen.getByTestId('severity-badge');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/red/);
    expect(badge.textContent).toBe('Severe');
  });

  it('shows Anemia Detected status for anemia_detected=1', () => {
    render(<PredictionResult result={makeResult('Mild', 1)} />);
    const statusBar = screen.getByTestId('prediction-status-bar');
    expect(statusBar.textContent).toContain('Anemia Detected');
  });

  it('shows No Anemia status for anemia_detected=0', () => {
    render(<PredictionResult result={makeResult('None', 0)} />);
    const statusBar = screen.getByTestId('prediction-status-bar');
    expect(statusBar.textContent).toContain('No Anemia');
  });

  it('renders SHAP table when explanation is provided', () => {
    render(<PredictionResult result={makeResult('Mild')} />);
    const table = screen.getByTestId('shap-table');
    expect(table).toBeInTheDocument();
    expect(table.textContent).toContain('HGB');
    expect(table.textContent).toContain('MCV');
  });

  it('renders null when result is null', () => {
    const { container } = render(<PredictionResult result={null} />);
    expect(container.firstChild).toBeNull();
  });
});
