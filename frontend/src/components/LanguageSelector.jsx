/**
 * LanguageSelector.jsx
 * Compact language dropdown. Changes i18next language and PATCHes user preference.
 */

import { useTranslation } from 'react-i18next';
import client from '../api/client.js';

const LANGUAGES = [
  { code: 'en', label: '🇬🇧 English' },
  { code: 'hi', label: '🇮🇳 Hindi' },
  { code: 'ta', label: '🇮🇳 Tamil' },
  { code: 'kn', label: '🇮🇳 Kannada' },
];

export default function LanguageSelector() {
  // useTranslation gives us i18n instance — changing language via i18n.changeLanguage
  // automatically triggers re-renders in all components using useTranslation
  const { i18n } = useTranslation();
  const current = i18n.language || localStorage.getItem('language') || 'en';

  async function handleChange(e) {
    const lang = e.target.value;
    localStorage.setItem('language', lang);
    // This triggers a re-render of every component using useTranslation
    await i18n.changeLanguage(lang);
    try {
      await client.patch('/api/users/me/language', { language: lang });
    } catch {
      // Non-critical — language is already changed locally
    }
  }

  return (
    <select
      value={current}
      onChange={handleChange}
      className="text-xs rounded border border-slate-600 bg-transparent text-slate-300 px-2 py-1 focus:outline-none focus:ring-1 cursor-pointer"
      style={{ '--tw-ring-color': '#6366f1' }}
    >
      {LANGUAGES.map(({ code, label }) => (
        <option key={code} value={code} className="bg-slate-800 text-slate-200">
          {label}
        </option>
      ))}
    </select>
  );
}
