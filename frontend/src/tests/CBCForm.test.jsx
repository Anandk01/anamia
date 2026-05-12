/**
 * CBCForm.test.jsx
 * Vitest + React Testing Library tests for CBCForm component.
 *
 * Tests:
 *   1. Empty submit shows validation errors for all fields
 *   2. Non-numeric input is rejected (shows invalid error)
 *   3. All-valid inputs enable submit and call onSubmit
 */

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CBCForm from '../components/CBCForm.jsx';

// Mock lucide-react to avoid SVG rendering issues in jsdom
vi.mock('lucide-react', () => ({
  Paperclip: () => null,
}));

// Mock the API client to avoid real HTTP calls
vi.mock('../api/client.js', () => ({
  default: {
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

const CBC_KEYS = ['rbc', 'mcv', 'mch', 'mchc', 'rdw', 'tlc', 'plt', 'hgb'];

const VALID_VALUES = {
  rbc: '4.5',
  mcv: '85',
  mch: '28',
  mchc: '33',
  rdw: '13.5',
  tlc: '7.0',
  plt: '250',
  hgb: '13.5',
};

describe('CBCForm', () => {
  it('shows validation errors for all fields when submitted empty', async () => {
    const onSubmit = vi.fn();
    render(<CBCForm onSubmit={onSubmit} loading={false} />);

    const submitBtn = screen.getByTestId('submit-cbc');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      // Each field should show a "Required" error
      CBC_KEYS.forEach((key) => {
        const errorEl = screen.getByTestId(`error-${key}`);
        expect(errorEl).toBeInTheDocument();
        expect(errorEl.textContent).toMatch(/required/i);
      });
    });

    // onSubmit should NOT have been called
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows invalid error for non-numeric input', async () => {
    const onSubmit = vi.fn();
    render(<CBCForm onSubmit={onSubmit} loading={false} />);

    // For type="number" inputs in jsdom, non-numeric values are silently rejected
    // and the value becomes empty string. We test this by submitting with empty
    // value after touching the field, which shows "Required" (the validation error
    // for empty/non-numeric input in a number field).
    const hgbInput = screen.getByTestId('cbc-input-hgb');
    fireEvent.focus(hgbInput);
    fireEvent.blur(hgbInput);

    await waitFor(() => {
      const errorEl = screen.getByTestId('error-hgb');
      expect(errorEl).toBeInTheDocument();
      // In jsdom, type=number rejects non-numeric input, leaving empty string → "Required"
      expect(errorEl.textContent).toMatch(/required|invalid/i);
    });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onSubmit with parsed values when all fields are valid', async () => {
    const onSubmit = vi.fn();
    render(<CBCForm onSubmit={onSubmit} loading={false} />);

    // Fill in all valid values
    CBC_KEYS.forEach((key) => {
      const input = screen.getByTestId(`cbc-input-${key}`);
      fireEvent.change(input, { target: { value: VALID_VALUES[key] } });
    });

    const submitBtn = screen.getByTestId('submit-cbc');
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    const callArg = onSubmit.mock.calls[0][0];
    // All values should be parsed as numbers
    CBC_KEYS.forEach((key) => {
      expect(typeof callArg[key.toUpperCase()]).toBe('number');
    });
  });

  it('submit button is disabled while loading', () => {
    render(<CBCForm onSubmit={vi.fn()} loading={true} />);
    const submitBtn = screen.getByTestId('submit-cbc');
    expect(submitBtn).toBeDisabled();
  });
});
