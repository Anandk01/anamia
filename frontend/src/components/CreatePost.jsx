import React, { useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import client from '../api/client';

export default function CreatePost({ onBack, onCreated }) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [tags, setTags] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await client.post('/api/forum/posts', {
        title,
        body,
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        is_anonymous: anonymous,
      });
      onCreated?.(res.data.post || res.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create post');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-800 mb-4">
        <ArrowLeft size={16} /> Back
      </button>

      <h2 className="text-xl font-semibold mb-4">Create New Post</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Title</label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            placeholder="Post title"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Body</label>
          <textarea
            value={body}
            onChange={e => setBody(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 h-40 resize-none"
            placeholder="Write your post... (Markdown supported)"
            required
          />
          <p className="text-xs text-slate-400 mt-1">Markdown formatting is supported</p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Tags</label>
          <input
            value={tags}
            onChange={e => setTags(e.target.value)}
            className="w-full border rounded-lg px-3 py-2"
            placeholder="iron-deficiency, diet, symptoms (comma-separated)"
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={anonymous}
            onChange={e => setAnonymous(e.target.checked)}
            className="rounded"
          />
          Post anonymously
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Posting...' : 'Create Post'}
        </button>
      </form>
    </div>
  );
}
