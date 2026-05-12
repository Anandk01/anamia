/**
 * pdf_properties.test.js
 *
 * Property-based and unit tests for pdfService.js
 *
 * Property 19: Filename regex match for any username/date combo
 *   Validates: Requirements 11.4
 *
 * Property 20: jsPDF output text contains all required field labels
 *   Validates: Requirements 11.2, 11.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { generateFilename } from '../services/pdfService.js';

// ─────────────────────────────────────────────────────────────────────────────
// Property 19: Filename regex match for any username/date combo
// Validates: Requirements 11.4
// ─────────────────────────────────────────────────────────────────────────────

describe('Property 19 — generateFilename matches required pattern', () => {
  // Pattern: anemia_report_{username}_{YYYYMMDD}.pdf
  // Username may contain underscores, so we match greedily up to the last _YYYYMMDD.pdf
  const FILENAME_REGEX = /^anemia_report_.+_\d{8}\.pdf$/;

  // Parametrized examples covering various username/date combinations
  const testCases = [
    { username: 'john_doe', date: '2024-01-15 10:30:00', expectedDate: '20240115' },
    { username: 'alice', date: '2023-12-31 23:59:59', expectedDate: '20231231' },
    { username: 'dr.smith', date: '2025-06-01 00:00:00', expectedDate: '20250601' },
    { username: 'patient123', date: '2024-02-29 12:00:00', expectedDate: '20240229' },
    { username: 'user', date: '2000-01-01 08:00:00', expectedDate: '20000101' },
    { username: 'longusernamehere', date: '2024-07-04 15:45:00', expectedDate: '20240704' },
    { username: 'a', date: '2024-11-30 09:00:00', expectedDate: '20241130' },
    { username: 'test.user', date: '2024-03-15 14:22:33', expectedDate: '20240315' },
  ];

  testCases.forEach(({ username, date, expectedDate }) => {
    it(`filename for username="${username}" date="${date}" matches regex`, () => {
      const filename = generateFilename(username, date);
      expect(filename).toMatch(FILENAME_REGEX);
    });

    it(`filename for username="${username}" date="${date}" has correct date part "${expectedDate}"`, () => {
      const filename = generateFilename(username, date);
      expect(filename).toBe(`anemia_report_${username}_${expectedDate}.pdf`);
    });
  });

  it('filename always starts with anemia_report_', () => {
    const usernames = ['alice', 'bob', 'charlie', 'dr.jones', 'patient99'];
    const date = '2024-05-20 10:00:00';
    usernames.forEach((username) => {
      const filename = generateFilename(username, date);
      expect(filename.startsWith('anemia_report_')).toBe(true);
    });
  });

  it('filename always ends with .pdf', () => {
    const usernames = ['alice', 'bob', 'charlie'];
    const date = '2024-05-20 10:00:00';
    usernames.forEach((username) => {
      const filename = generateFilename(username, date);
      expect(filename.endsWith('.pdf')).toBe(true);
    });
  });

  it('date portion is always exactly 8 digits', () => {
    const dates = [
      '2024-01-01 00:00:00',
      '2024-12-31 23:59:59',
      '2000-06-15 12:00:00',
    ];
    dates.forEach((date) => {
      const filename = generateFilename('testuser', date);
      // Extract the date part: last segment before .pdf
      const parts = filename.replace('.pdf', '').split('_');
      const datePart = parts[parts.length - 1];
      expect(datePart).toMatch(/^\d{8}$/);
    });
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Property 20: jsPDF output text contains all required field labels
// Validates: Requirements 11.2, 11.3
// ─────────────────────────────────────────────────────────────────────────────

// Capture array must be module-level so the mock factory can reference it
const _mockTextCalls = [];

// vi.mock is hoisted to the top of the file by Vitest, so the factory must
// be self-contained — it cannot reference variables defined in describe blocks.
vi.mock('jspdf', () => {
  const mockDoc = {
    setFont: vi.fn(),
    setFontSize: vi.fn(),
    setTextColor: vi.fn(),
    setFillColor: vi.fn(),
    setDrawColor: vi.fn(),
    rect: vi.fn(),
    line: vi.fn(),
    text: vi.fn((...args) => {
      const textArg = args[0];
      if (Array.isArray(textArg)) {
        textArg.forEach((t) => _mockTextCalls.push(String(t)));
      } else {
        _mockTextCalls.push(String(textArg));
      }
    }),
    splitTextToSize: vi.fn((text) => [text]),
    addPage: vi.fn(),
    save: vi.fn(),
    internal: {
      pageSize: {
        getWidth: vi.fn(() => 210),
        getHeight: vi.fn(() => 297),
      },
    },
  };
  return { jsPDF: vi.fn(() => mockDoc) };
});

// Also mock i18n to avoid localStorage issues in test environment
vi.mock('../i18n/index.js', () => ({
  default: {
    t: vi.fn((key) => key),
    getFixedT: vi.fn(() => (key) => key),
    changeLanguage: vi.fn(),
  },
}));

// Import generatePDF after mocks are set up
const { generatePDF } = await import('../services/pdfService.js');

describe('Property 20 — generatePDF calls doc.text() with all required labels', () => {
  beforeEach(() => {
    _mockTextCalls.length = 0;
  });

  const sampleReportData = {
    date: '2024-01-15 10:30:00',
    cbc: {
      rbc: 4.5,
      mcv: 85.0,
      mch: 28.0,
      mchc: 33.0,
      rdw: 13.5,
      tlc: 7.0,
      plt: 250.0,
      hgb: 11.5,
    },
    anemia_detected: 1,
    severity_level: 'Mild',
    anemia_type: 'Iron-Deficiency',
    anemia_confidence: 0.87,
    explanation: [
      { feature: 'HGB', direction: 'Low', shap_value: -0.45 },
      { feature: 'MCV', direction: 'Low', shap_value: -0.32 },
      { feature: 'MCH', direction: 'Low', shap_value: -0.21 },
    ],
    diet_recs: [
      { name: 'Spinach', rationale: 'High in non-haem iron', is_vegan: true },
      { name: 'Lentils', rationale: 'Rich in iron and protein', is_vegan: true },
    ],
    health_tips: [
      'Take iron supplements as prescribed.',
      'Avoid tea/coffee with meals.',
    ],
  };

  it('doc.text() is called with text containing "HGB"', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    expect(allText).toContain('HGB');
  });

  it('doc.text() is called with text containing "RBC"', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    expect(allText).toContain('RBC');
  });

  it('doc.text() is called with text containing "Anemia"', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    expect(allText).toContain('Anemia');
  });

  it('doc.text() is called with text containing "Severity"', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    expect(allText).toContain('Severity');
  });

  it('doc.text() is called with text containing "Diet"', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    // i18n mock returns the key 'diet_recommendations'; food item names also appear
    expect(allText.toLowerCase()).toContain('diet');
  });

  it('doc.text() is called with text containing "Disclaimer"', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    // The disclaimer key is used via i18n.t('disclaimer') which returns 'disclaimer'
    // OR the fallback string contains 'Disclaimer'
    expect(allText.toLowerCase()).toContain('disclaimer');
  });

  it('all required labels are present in a single generatePDF call', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ').toLowerCase();
    // These labels appear as CBC field names, section headers, or i18n keys
    const requiredLabels = ['hgb', 'rbc', 'anemia', 'severity', 'diet'];
    requiredLabels.forEach((label) => {
      expect(allText, `Expected label "${label}" to appear in PDF text`).toContain(label);
    });
  });

  it('patient username appears in PDF text', async () => {
    await generatePDF(sampleReportData, 'dr.jones');
    const allText = _mockTextCalls.join(' ');
    expect(allText).toContain('dr.jones');
  });

  it('generation date appears in PDF text', async () => {
    await generatePDF(sampleReportData, 'testuser');
    const allText = _mockTextCalls.join(' ');
    expect(allText).toContain('2024-01-15 10:30:00');
  });
});
