/**
 * Chatbot.jsx
 * Floating bottom-right chat panel. 320×480px slide-up panel.
 * User bubbles right (indigo), bot bubbles left (gray).
 */

import { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import client from '../api/client.js';

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'bot', text: '✨ Hello! I\'m AnemiaBot, powered by Gemini AI with WHO & NHLBI knowledge. Ask me anything about anemia, symptoms, diet, or your CBC results!', sources: [] },
  ]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const sessionId = useRef(
    typeof crypto !== 'undefined' && crypto.randomUUID 
      ? crypto.randomUUID() 
      : Math.random().toString(36).substring(2) + Date.now().toString(36)
  );
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  async function sendMessage() {
    const text = input.trim();
    if (!text || typing) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setTyping(true);
    try {
      const res = await client.post('/api/chat/message', {
        message: text,
        session_id: sessionId.current,
      });
      
      const data = res.data || {};
      const reply = data.response || data.reply || data.message || 'Sorry, I could not process that.';
      const sources = data.sources || [];
      
      setMessages((prev) => [...prev, { role: 'bot', text: reply, sources }]);
    } catch (err) {
      console.error('Chatbot error:', err);
      const errMsg = err.response?.data?.message || err.message || 'Sorry, something went wrong. Please try again.';
      setMessages((prev) => [...prev, { role: 'bot', text: `Error: ${errMsg}`, sources: [] }]);
    } finally {
      setTyping(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-5 right-5 z-50 w-12 h-12 rounded-full text-white shadow-lg flex items-center justify-center transition hover:scale-105"
        style={{ backgroundColor: '#6366f1' }}
        aria-label="Open chat"
      >
        {open ? <X size={20} /> : <MessageCircle size={20} />}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          className="fixed bottom-20 right-5 z-50 bg-white rounded-xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
          style={{ width: '320px', height: '480px' }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100" style={{ backgroundColor: '#6366f1' }}>
            <div className="flex items-center gap-2">
              <MessageCircle size={16} className="text-white" />
              <span className="text-white font-semibold text-sm">AnemiaBot · Gemini AI</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-white/50 text-xs">WHO · NHLBI</span>
              <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white transition">
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className="max-w-[85%] space-y-1">
                  <div
                    className={`px-3 py-2 rounded-xl text-sm leading-snug ${
                      msg.role === 'user'
                        ? 'text-white rounded-br-sm'
                        : 'bg-slate-100 text-slate-700 rounded-bl-sm'
                    }`}
                    style={msg.role === 'user' ? { backgroundColor: '#6366f1' } : {}}
                  >
                    {msg.text}
                  </div>
                  {msg.role === 'bot' && msg.sources && msg.sources.length > 0 && (
                    <div className="flex flex-wrap gap-1 px-1">
                      {msg.sources.map((src, i) => (
                        <a
                          key={i}
                          href={src}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-indigo-400 hover:text-indigo-600 underline"
                        >
                          {src.includes('who.int') ? 'WHO' : 'NHLBI'}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {typing && (
              <div className="flex justify-start">
                <div className="bg-slate-100 rounded-xl rounded-bl-sm">
                  <TypingIndicator />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="flex items-center gap-2 px-3 py-2.5 border-t border-slate-100">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              className="flex-1 text-sm rounded border border-slate-200 bg-slate-50 px-3 py-1.5 focus:outline-none focus:ring-2 focus:border-transparent transition"
              disabled={typing}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || typing}
              className="w-8 h-8 rounded flex items-center justify-center text-white transition disabled:opacity-50"
              style={{ backgroundColor: '#6366f1' }}
            >
              <Send size={14} />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
