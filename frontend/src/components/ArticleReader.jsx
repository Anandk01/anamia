import React, { useState, useEffect } from 'react';
import { ArrowLeft, Heart, Clock } from 'lucide-react';
import client from '../api/client';

export default function ArticleReader({ articleId, onBack }) {
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bookmarked, setBookmarked] = useState(false);

  useEffect(() => {
    if (!articleId) return;
    client.get(`/api/articles/${articleId}`)
      .then(res => {
        setArticle(res.data.article || res.data);
        setBookmarked(res.data.bookmarked || false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [articleId]);

  const toggleBookmark = async () => {
    try {
      if (bookmarked) {
        await client.delete(`/api/articles/${articleId}/bookmark`);
      } else {
        await client.post(`/api/articles/${articleId}/bookmark`);
      }
      setBookmarked(!bookmarked);
    } catch {}
  };

  if (loading) return <div className="py-8 text-center text-slate-500">Loading article...</div>;
  if (!article) return <div className="py-8 text-center text-slate-500">Article not found</div>;

  return (
    <div className="max-w-3xl mx-auto">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-800 mb-4">
        <ArrowLeft size={16} /> Back to articles
      </button>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <h1 className="text-2xl font-bold">{article.title}</h1>
          <button onClick={toggleBookmark} className="p-2 hover:bg-slate-100 rounded">
            <Heart
              size={20}
              className={bookmarked ? 'fill-red-500 text-red-500' : 'text-slate-400'}
            />
          </button>
        </div>
        <div className="flex items-center gap-3 mt-2 text-sm text-slate-500">
          {article.author && <span>{article.author}</span>}
          {article.published_at && <span>{new Date(article.published_at).toLocaleDateString()}</span>}
          {article.read_time && (
            <span className="flex items-center gap-1">
              <Clock size={14} /> {article.read_time} min
            </span>
          )}
        </div>
        {article.tags?.length > 0 && (
          <div className="flex gap-1 mt-3">
            {article.tags.map(t => (
              <span key={t} className="px-2 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded-full">{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div
        className="prose prose-slate max-w-none"
        dangerouslySetInnerHTML={{ __html: article.content || article.body || '' }}
      />
    </div>
  );
}
