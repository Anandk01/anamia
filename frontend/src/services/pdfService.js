/**
 * pdfService.js
 * Generates and downloads PDF reports for anemia detection results.
 * Uses jsPDF programmatically (no html2canvas capture) for reliability.
 *
 * Task 20.3 — i18n integration:
 * Section labels use i18next.t() so they are rendered in the user's
 * selected language. The locale param allows overriding the current
 * language for a specific PDF generation call.
 */

import { jsPDF } from 'jspdf';
import i18next from '../i18n/index.js';

// CBC field metadata: [label, unit]
const CBC_FIELDS = [
  ['RBC', 'M/uL'],
  ['MCV', 'fL'],
  ['MCH', 'pg'],
  ['MCHC', 'g/dL'],
  ['RDW', '%'],
  ['TLC', 'K/uL'],
  ['PLT', 'K/uL'],
  ['HGB', 'g/dL'],
];

/**
 * Derives a YYYYMMDD string from a datetime string like "2024-01-15 10:30:00".
 * @param {string} dateStr - datetime string
 * @returns {string} formatted as YYYYMMDD
 */
export function formatDateYYYYMMDD(dateStr) {
  if (!dateStr) {
    // Fallback to today's date if no date provided
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
  }
  const d = new Date(dateStr.replace(' ', 'T'));
  if (isNaN(d.getTime())) {
    const now = new Date();
    return `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}`;
  }
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}${month}${day}`;
}

/**
 * Generates the PDF filename using the pattern anemia_report_{username}_{YYYYMMDD}.pdf
 * @param {string} username
 * @param {string} dateStr - datetime string from reportData.date
 * @returns {string} filename
 */
export function generateFilename(username, dateStr) {
  const datePart = formatDateYYYYMMDD(dateStr);
  return `anemia_report_${username}_${datePart}.pdf`;
}

/**
 * Generates a PDF report programmatically using jsPDF.
 *
 * @param {Object} reportData - The report data object
 * @param {string} reportData.date - Submission datetime "YYYY-MM-DD HH:MM:SS"
 * @param {Object} reportData.cbc - CBC values { rbc, mcv, mch, mchc, rdw, tlc, plt, hgb }
 * @param {number} reportData.anemia_detected - 0 or 1
 * @param {string} reportData.severity_level - "None"|"Mild"|"Moderate"|"Severe"
 * @param {string} reportData.anemia_type - anemia type string
 * @param {number} reportData.anemia_confidence - confidence float 0.0–1.0
 * @param {Array}  reportData.explanation - [{feature, direction, shap_value}, ...]
 * @param {Array}  reportData.diet_recs - [{name, rationale, is_vegan}, ...]
 * @param {Array}  reportData.health_tips - [str, ...]
 * @param {string} username - patient/doctor username
 * @param {string} [locale] - optional locale override (e.g. 'hi', 'ta', 'kn')
 * @returns {Promise<jsPDF>} resolves with the jsPDF document instance
 */
export function generatePDF(reportData, username, locale) {
  return new Promise((resolve, reject) => {
    try {
      // Use locale override if provided, otherwise use current i18next language
      const t = locale
        ? (key) => i18next.getFixedT(locale)(key)
        : (key) => i18next.t(key);

      // Normalise date — API may not always return it
      const reportDate = reportData.date || new Date().toISOString().replace('T', ' ').slice(0, 19);

      // Normalise CBC — API returns it nested under 'cbc' key
      const cbcData = reportData.cbc || reportData || {};

      const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });

      // Page dimensions
      const pageWidth = doc.internal.pageSize.getWidth();
      const pageHeight = doc.internal.pageSize.getHeight();
      const marginLeft = 15;
      const marginRight = 15;
      const contentWidth = pageWidth - marginLeft - marginRight;

      // White background
      doc.setFillColor(255, 255, 255);
      doc.rect(0, 0, pageWidth, pageHeight, 'F');

      let y = 15;

      // ── Header ──────────────────────────────────────────────────────────────
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(18);
      doc.setTextColor(30, 30, 30);
      doc.text('Anemia Detection Report', pageWidth / 2, y, { align: 'center' });
      y += 7;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(100, 100, 100);
      doc.text(`Generated: ${reportDate}`, pageWidth / 2, y, { align: 'center' });
      y += 5;

      // Divider line
      doc.setDrawColor(180, 180, 180);
      doc.line(marginLeft, y, pageWidth - marginRight, y);
      y += 6;

      // ── Patient Section ──────────────────────────────────────────────────────
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(t('patient_information') || 'Patient Information', marginLeft, y);      y += 5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.text(`Patient: ${username}`, marginLeft, y);
      y += 5;
      doc.text(`Date: ${reportDate}`, marginLeft, y);
      y += 7;

      // ── CBC Values Table ─────────────────────────────────────────────────────
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(t('cbc_values') || 'CBC Values', marginLeft, y);
      y += 5;

      // Table header
      const colField = marginLeft;
      const colValue = marginLeft + 60;
      const colUnit = marginLeft + 110;
      const rowHeight = 6;

      doc.setFillColor(240, 240, 245);
      doc.rect(marginLeft, y - 4, contentWidth, rowHeight, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(50, 50, 50);
      doc.text('Field', colField, y);
      doc.text('Value', colValue, y);
      doc.text('Unit', colUnit, y);
      y += rowHeight;

      // Table rows
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      CBC_FIELDS.forEach(([field, unit], idx) => {
        const key = field.toLowerCase();
        const value = cbcData[key] !== undefined ? String(cbcData[key]) : 'N/A';

        if (idx % 2 === 0) {
          doc.setFillColor(250, 250, 252);
          doc.rect(marginLeft, y - 4, contentWidth, rowHeight, 'F');
        }

        doc.setTextColor(30, 30, 30);
        doc.text(field, colField, y);
        doc.text(value, colValue, y);
        doc.text(unit, colUnit, y);
        y += rowHeight;
      });

      // Bottom border of table
      doc.setDrawColor(200, 200, 200);
      doc.line(marginLeft, y - 2, pageWidth - marginRight, y - 2);
      y += 5;

      // ── Prediction Result ────────────────────────────────────────────────────
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(t('prediction_result') || 'Prediction Result', marginLeft, y);
      y += 5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      const anemiaDetectedText = reportData.anemia_detected === 1 ? 'Yes' : 'No';
      doc.text(`Anemia Detected: ${anemiaDetectedText}`, marginLeft, y);
      y += 5;
      doc.text(`Severity: ${reportData.severity_level}`, marginLeft, y);
      y += 5;
      doc.text(`Type: ${reportData.anemia_type}`, marginLeft, y);
      y += 5;
      const confidencePct = reportData.anemia_confidence !== undefined
        ? `${(reportData.anemia_confidence * 100).toFixed(1)}%`
        : 'N/A';
      doc.text(`Confidence: ${confidencePct}`, marginLeft, y);
      y += 8;

      // ── SHAP Explanation Table ───────────────────────────────────────────────
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(t('explanation') || 'Top Feature Explanations (SHAP)', marginLeft, y);
      y += 5;

      // Table header
      const colFeature = marginLeft;
      const colDirection = marginLeft + 55;
      const colShap = marginLeft + 110;

      doc.setFillColor(240, 240, 245);
      doc.rect(marginLeft, y - 4, contentWidth, rowHeight, 'F');
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(8);
      doc.setTextColor(50, 50, 50);
      doc.text('Feature', colFeature, y);
      doc.text('Direction', colDirection, y);
      doc.text('SHAP Value', colShap, y);
      y += rowHeight;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      const explanations = Array.isArray(reportData.explanation) ? reportData.explanation.slice(0, 3) : [];
      explanations.forEach((item, idx) => {
        if (idx % 2 === 0) {
          doc.setFillColor(250, 250, 252);
          doc.rect(marginLeft, y - 4, contentWidth, rowHeight, 'F');
        }
        doc.setTextColor(30, 30, 30);
        doc.text(String(item.feature || ''), colFeature, y);
        doc.text(String(item.direction || ''), colDirection, y);
        doc.text(String(item.shap_value !== undefined ? item.shap_value.toFixed(4) : ''), colShap, y);
        y += rowHeight;
      });

      doc.setDrawColor(200, 200, 200);
      doc.line(marginLeft, y - 2, pageWidth - marginRight, y - 2);
      y += 5;

      // ── Diet Recommendations ─────────────────────────────────────────────────
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(t('diet_recommendations') || 'Diet Recommendations', marginLeft, y);
      y += 5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      const dietRecs = Array.isArray(reportData.diet_recs) ? reportData.diet_recs : [];
      dietRecs.forEach((item, idx) => {
        // Check if we need a new page
        if (y > pageHeight - 40) {
          doc.addPage();
          y = 15;
        }
        const label = `${idx + 1}. ${item.name}`;
        const rationale = item.rationale ? ` — ${item.rationale}` : '';
        const fullText = label + rationale;
        const lines = doc.splitTextToSize(fullText, contentWidth);
        doc.setTextColor(30, 30, 30);
        doc.text(lines, marginLeft, y);
        y += lines.length * 5;
      });
      y += 3;

      // ── Health Tips ──────────────────────────────────────────────────────────
      if (y > pageHeight - 40) {
        doc.addPage();
        y = 15;
      }

      doc.setFont('helvetica', 'bold');
      doc.setFontSize(10);
      doc.setTextColor(30, 30, 30);
      doc.text(t('health_tips') || 'Health Tips', marginLeft, y);
      y += 5;

      doc.setFont('helvetica', 'normal');
      doc.setFontSize(8);
      const healthTips = Array.isArray(reportData.health_tips) ? reportData.health_tips : [];
      healthTips.forEach((tip, idx) => {
        if (y > pageHeight - 30) {
          doc.addPage();
          y = 15;
        }
        const lines = doc.splitTextToSize(`${idx + 1}. ${tip}`, contentWidth);
        doc.setTextColor(30, 30, 30);
        doc.text(lines, marginLeft, y);
        y += lines.length * 5;
      });

      // ── Disclaimer Footer ────────────────────────────────────────────────────
      // Place disclaimer at the bottom of the last page
      const disclaimerY = pageHeight - 12;
      doc.setDrawColor(180, 180, 180);
      doc.line(marginLeft, disclaimerY - 4, pageWidth - marginRight, disclaimerY - 4);
      doc.setFont('helvetica', 'italic');
      doc.setFontSize(7);
      doc.setTextColor(120, 120, 120);
      doc.text(
        t('disclaimer') || 'Disclaimer: This report is not a substitute for professional medical advice.',
        pageWidth / 2,
        disclaimerY,
        { align: 'center' }
      );

      resolve(doc);
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * Generates a PDF and triggers a browser download.
 * Filename follows the pattern: anemia_report_{username}_{YYYYMMDD}.pdf
 *
 * @param {Object} reportData - see generatePDF for structure
 * @param {string} username
 * @param {string} [locale] - optional locale override
 * @returns {Promise<void>}
 */
export async function downloadPDF(reportData, username, locale) {
  const doc = await generatePDF(reportData, username, locale);
  const dateStr = reportData.date || new Date().toISOString().replace('T', ' ').slice(0, 19);
  const filename = generateFilename(username, dateStr);
  doc.save(filename);
}
