import React, { useState } from 'react';
import { FileText } from 'lucide-react';
import client from '../api/client';

export default function ArticleEditor({ onSaved }) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [summary, setSummary] = useState('');

  const handleSave = async (publish = false) => {
    setLoading(true);
    setError('');
    setSuccess('');
    setSummary('');
    try {
      const payload = {
        title,
        content,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      };
      const res = await client.post('/api/articles', payload);
      const articleId = res.data.article?.id || res.data.id;

      if (publish && articleId) {
        const pubRes = await client.post(`/api/articles/${articleId}/publish`);
        setSummary(pubRes.data.summary || '');
        setSuccess('Article published successfully!');
      } else {
        setSuccess('Draft saved successfully!');
      }

      onSaved?.(res.data.article || res.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save article');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
        <FileText size={20} className="text-indigo-600" />
        Write Article
      </h2>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Title</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            placeholder="Article title"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Content</label>
          <textarea
            value={content}
            onChange={e => setContent(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 h-64 resize-none font-mono text-sm"
            placeholder="Write your article content here..."
            required
          />
          <p className="text-xs text-slate-400 mt-1">Supports Markdown</p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Tags</label>
          <input
            value={tags}
            onChange={e => setTags(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            placeholder="iron-deficiency, nutrition, treatment (comma-separated)"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {success && <p className="text-sm text-green-600">{success}</p>}
        {summary && (
          <div className="bg-slate-50 border rounded-lg p-3">
            <p className="text-xs font-medium text-slate-500 mb-1">Generated Summary</p>
            <p className="text-sm text-slate-700">{summary}</p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => handleSave(false)}
            disabled={loading || !title || !content}
            className="px-4 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50 disabled:opacity-50"
          >
            Save Draft
          </button>
          <button
            onClick={() => handleSave(true)}
            disabled={loading || !title || !content}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Publish'}
          </button>
        </div>
      </div>
    </div>
  );
}
