import React, { useState, useEffect } from 'react';
import { Search, Heart } from 'lucide-react';
import client from '../api/client';

export default function EducationCenter({ onSelectArticle }) {
  const [articles, setArticles] = useState([]);
  const [search, setSearch] = useState('');
  const [tag, setTag] = useState('');
  const [tags, setTags] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [bookmarks, setBookmarks] = useState(new Set());

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ page });
    if (tag) params.set('tag', tag);
    if (search) params.set('search', search);
    client.get(`/api/articles?${params}`)
      .then(res => {
        setArticles(res.data.articles || []);
        setTotalPages(res.data.total_pages || 1);
        if (res.data.tags) setTags(res.data.tags);
      })
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  }, [page, tag, search]);

  const toggleBookmark = (articleId) => {
    setBookmarks(prev => {
      const next = new Set(prev);
      if (next.has(articleId)) {
        next.delete(articleId);
        client.delete(`/api/articles/${articleId}/bookmark`).catch(() => {});
      } else {
        next.add(articleId);
        client.post(`/api/articles/${articleId}/bookmark`).catch(() => {});
      }
      return next;
    });
  };

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <form onSubmit={handleSearch} className="relative">
        <Search size={18} className="absolute left-3 top-2.5 text-slate-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search articles..."
          className="w-full border rounded-lg pl-10 pr-4 py-2"
        />
      </form>

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

      {/* Articles grid */}
      {loading ? (
        <p className="text-slate-500 text-sm py-4">Loading articles...</p>
      ) : articles.length === 0 ? (
        <p className="text-slate-500 text-sm py-4">No articles found</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {articles.map(article => (
            <div
              key={article.id}
              className="bg-white border rounded-lg p-4 hover:border-indigo-200 cursor-pointer relative"
              onClick={() => onSelectArticle?.(article)}
            >
              <button
                onClick={(e) => { e.stopPropagation(); toggleBookmark(article.id); }}
                className="absolute top-3 right-3"
              >
                <Heart
                  size={18}
                  className={bookmarks.has(article.id) ? 'fill-red-500 text-red-500' : 'text-slate-300 hover:text-red-400'}
                />
              </button>
              <h3 className="font-medium mb-1 pr-6">{article.title}</h3>
              <p className="text-sm text-slate-600 line-clamp-2 mb-2">{article.summary}</p>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                {article.read_time && <span>{article.read_time} min read</span>}
                {article.author && <span>• {article.author}</span>}
              </div>
              {article.tags?.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {article.tags.map(t => (
                    <span key={t} className="px-1.5 py-0.5 text-xs bg-slate-100 rounded">{t}</span>
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
