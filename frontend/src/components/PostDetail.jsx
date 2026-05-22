import React, { useState, useEffect } from 'react';
import { ThumbsUp, ArrowLeft, BadgeCheck } from 'lucide-react';
import client from '../api/client';
import { useAuth } from '../hooks/useAuth';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function PostDetail({ postId, onBack }) {
  const [post, setPost] = useState(null);
  const [replies, setReplies] = useState([]);
  const [replyText, setReplyText] = useState('');
  const [loading, setLoading] = useState(true);
  const { getRole } = useAuth();
  const isDoctor = getRole() === 'doctor';

  useEffect(() => {
    if (!postId) return;
    client.get(`/api/forum/posts/${postId}`)
      .then(res => {
        setPost(res.data.post || res.data);
        setReplies(res.data.replies || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [postId]);

  const handleUpvotePost = async () => {
    try {
      const res = await client.post(`/api/forum/posts/${postId}/upvote`);
      setPost(prev => ({ ...prev, upvotes: res.data.upvotes ?? (prev.upvotes || 0) + 1 }));
    } catch {}
  };

  const handleUpvoteReply = async (replyId) => {
    try {
      await client.post(`/api/forum/replies/${replyId}/upvote`);
      setReplies(prev => prev.map(r =>
        r.id === replyId ? { ...r, upvotes: (r.upvotes || 0) + 1 } : r
      ));
    } catch {}
  };

  const handleVerify = async (replyId) => {
    try {
      await client.post(`/api/forum/replies/${replyId}/verify`);
      setReplies(prev => prev.map(r =>
        r.id === replyId ? { ...r, verified: true } : r
      ));
    } catch {}
  };

  const submitReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim()) return;
    try {
      const res = await client.post(`/api/forum/posts/${postId}/replies`, { body: replyText });
      setReplies(prev => [...prev, res.data.reply || res.data]);
      setReplyText('');
    } catch {}
  };

  if (loading) return <div className="py-8 text-center text-slate-500">Loading...</div>;
  if (!post) return <div className="py-8 text-center text-slate-500">Post not found</div>;

  return (
    <div className="space-y-4">
      <button onClick={onBack} className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-800">
        <ArrowLeft size={16} /> Back
      </button>

      {/* Post */}
      <div className="bg-white border rounded-lg p-5">
        <h2 className="text-xl font-semibold mb-2">{post.title}</h2>
        <p className="text-slate-700 whitespace-pre-wrap mb-3">{post.body}</p>
        <div className="flex items-center gap-4 text-sm text-slate-500">
          <span>{post.is_anonymous ? 'Anonymous' : post.author}</span>
          <button onClick={handleUpvotePost} className="flex items-center gap-1 hover:text-indigo-600">
            <ThumbsUp size={14} /> {post.upvotes || 0}
          </button>
          <span>{timeAgo(post.created_at)}</span>
        </div>
        {post.tags?.length > 0 && (
          <div className="flex gap-1 mt-3">
            {post.tags.map(t => (
              <span key={t} className="px-2 py-0.5 text-xs bg-slate-100 rounded-full">{t}</span>
            ))}
          </div>
        )}
      </div>

      {/* Replies */}
      <div className="space-y-3">
        <h3 className="font-medium text-sm text-slate-600">Replies ({replies.length})</h3>
        {replies.map(reply => (
          <div key={reply.id} className="bg-white border rounded-lg p-4">
            <p className="text-sm text-slate-700 mb-2">{reply.body}</p>
            <div className="flex items-center gap-3 text-xs text-slate-500">
              <span>{reply.author}</span>
              {reply.is_doctor && (
                <span className="flex items-center gap-0.5 text-green-600">
                  <BadgeCheck size={12} /> Verified Doctor
                </span>
              )}
              {reply.verified && (
                <span className="text-green-600 font-medium">✓ Verified</span>
              )}
              <button onClick={() => handleUpvoteReply(reply.id)} className="flex items-center gap-1 hover:text-indigo-600">
                <ThumbsUp size={12} /> {reply.upvotes || 0}
              </button>
              <span>{timeAgo(reply.created_at)}</span>
              {isDoctor && !reply.verified && (
                <button
                  onClick={() => handleVerify(reply.id)}
                  className="ml-auto text-green-600 hover:text-green-700 font-medium"
                >
                  Verify
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Reply form */}
      <form onSubmit={submitReply} className="flex gap-2">
        <textarea
          value={replyText}
          onChange={e => setReplyText(e.target.value)}
          placeholder="Write a reply..."
          className="flex-1 border rounded-lg px-3 py-2 text-sm resize-none h-16"
          required
        />
        <button
          type="submit"
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 self-end"
        >
          Reply
        </button>
      </form>
    </div>
  );
}
