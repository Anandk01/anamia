import React, { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';
import client from '../api/client';
import { useSocket } from '../contexts/SocketContext';
import { useAuth } from '../hooks/useAuth';

export default function DoctorChat({ roomId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const { socket } = useSocket() || {};
  const { getUser } = useAuth();
  const currentUser = getUser();

  useEffect(() => {
    if (!roomId) return;
    client.get(`/api/chat/rooms/${roomId}/messages`)
      .then(res => setMessages(res.data.messages || []))
      .catch(() => setMessages([]));
  }, [roomId]);

  useEffect(() => {
    if (!socket || !roomId) return;

    socket.emit('join_room', { room_id: roomId });

    const handleMessage = (msg) => {
      setMessages(prev => [...prev, msg]);
    };
    const handleTyping = () => {
      setTyping(true);
      setTimeout(() => setTyping(false), 2000);
    };

    socket.on('new_message', handleMessage);
    socket.on('user_typing', handleTyping);

    return () => {
      socket.off('new_message', handleMessage);
      socket.off('user_typing', handleTyping);
      socket.emit('leave_room', { room_id: roomId });
    };
  }, [socket, roomId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const text = input.trim();
    setInput('');

    try {
      if (socket?.connected) {
        socket.emit('send_message', { room_id: roomId, content: text });
      } else {
        const res = await client.post(`/api/chat/rooms/${roomId}/messages`, { content: text });
        setMessages(prev => [...prev, res.data.message]);
      }
    } catch (err) {
      console.error('Failed to send message', err);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    } else {
      socket?.emit('typing', { room_id: roomId });
    }
  };

  if (!roomId) {
    return <div className="flex-1 flex items-center justify-center text-slate-400">Select a conversation</div>;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, idx) => {
          const isMine = msg.sender_id === currentUser?.id || msg.sender === currentUser?.username;
          return (
            <div key={msg.id || idx} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] px-3 py-2 rounded-lg text-sm ${
                isMine ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-800'
              }`}>
                <p>{msg.content}</p>
                <p className={`text-xs mt-1 ${isMine ? 'text-indigo-200' : 'text-slate-400'}`}>
                  {msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                </p>
              </div>
            </div>
          );
        })}
        {typing && (
          <div className="flex justify-start">
            <div className="bg-slate-200 px-3 py-2 rounded-lg">
              <span className="flex gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t p-3 flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          className="flex-1 border rounded-lg px-3 py-2 text-sm"
        />
        <button
          onClick={sendMessage}
          disabled={!input.trim()}
          className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
