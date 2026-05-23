import React, { useState, useEffect } from 'react';
import { ThumbsUp, MessageSquare, Plus } from 'lucide-react';
import client from '../api/client';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const SORT_OPTIONS = ['hot', 'top', 'new'];

export default function Forum({ onSelectPost, onNewPost }) {
  const [posts, setPosts] = useState([]);
  const [sort, setSort] = useState('hot');
  const [page, setPage] = useState(1);
  const [tag, setTag] = useState('');
  const [tags, setTags] = useState([]);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ sort, page });
    if (tag) params.set('tag', tag);
    client.get(`/api/forum/posts?${params}`)
      .then(res => {
        setPosts(res.data.posts || []);
        setTotalPages(res.data.total_pages || 1);
        if (res.data.tags) setTags(res.data.tags);
      })
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, [sort, page, tag]);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {SORT_OPTIONS.map(s => (
            <button
              key={s}
              onClick={() => { setSort(s); setPage(1); }}
              className={`px-3 py-1.5 text-sm capitalize rounded ${
                sort === s ? 'text-indigo-600 border-b-2 border-indigo-600 font-medium' : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <button
          onClick={onNewPost}
          className="flex items-center gap-1 px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700"
        >
          <Plus size={16} /> New Post
        </button>
      </div>

      {/* Tag filters */}
      {tags.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => { setTag(''); setPage(1); }}
            className={`px-2 py-1 text-xs rounded-full ${!tag ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}
          >
            All
          </button>
          {tags.map(t => (
            <button
              key={t}
              onClick={() => { setTag(t); setPage(1); }}
              className={`px-2 py-1 text-xs rounded-full ${tag === t ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {/* Posts */}
      {loading ? (
        <p className="text-slate-500 text-sm py-4">Loading posts...</p>
      ) : posts.length === 0 ? (
        <p className="text-slate-500 text-sm py-4">No posts found</p>
      ) : (
        <div className="space-y-3">
          {posts.map(post => (
            <div
              key={post.id}
              onClick={() => onSelectPost?.(post)}
              className="bg-white border rounded-lg p-4 cursor-pointer hover:border-indigo-200"
            >
              <h3 className="font-medium mb-1">{post.title}</h3>
              <p className="text-sm text-slate-600 mb-2">
                {post.body?.slice(0, 100)}{post.body?.length > 100 ? '...' : ''}
              </p>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <span>{post.is_anonymous ? 'Anonymous' : post.author}</span>
                <span className="flex items-center gap-1"><ThumbsUp size={12} /> {post.upvotes || 0}</span>
                <span className="flex items-center gap-1"><MessageSquare size={12} /> {post.reply_count || 0}</span>
                <span>{timeAgo(post.created_at)}</span>
              </div>
              {post.tags?.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {(Array.isArray(post.tags) ? post.tags : (() => { try { return JSON.parse(post.tags); } catch { return []; } })()).map(t => (
                    <span key={t} className="px-2 py-0.5 text-xs bg-slate-100 rounded-full">{t}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      <div className="flex justify-center gap-2 pt-2">
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="px-3 py-1 text-sm border rounded disabled:opacity-50"
        >
          Prev
        </button>
        <span className="px-3 py-1 text-sm text-slate-600">Page {page} of {totalPages}</span>
        <button
          onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="px-3 py-1 text-sm border rounded disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
