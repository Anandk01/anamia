import React, { useState, useEffect, useRef } from 'react';
import { Send, MessageCircle } from 'lucide-react';
import client from '../api/client';
import { useSocket } from '../contexts/SocketContext';
import { useAuth } from '../hooks/useAuth';

export default function DoctorChat() {
  const [rooms, setRooms] = useState([]);
  const [activeRoom, setActiveRoom] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [loadingRooms, setLoadingRooms] = useState(true);
  const messagesEndRef = useRef(null);
  const typingTimeout = useRef(null);
  const { socket, addListener, removeListener } = useSocket() || {};
  const { getUser } = useAuth();
  const currentUser = getUser();
  const role = currentUser?.role;

  // For patient: auto-load room with assigned doctor
  useEffect(() => {
    if (role === 'patient') {
      client.get(`/api/messages/room/${currentUser.username}`)
        .then(res => {
          setActiveRoom({ room_id: res.data.room_id, patient_username: currentUser.username, doctor_username: res.data.doctor_username });
          setMessages(res.data.messages || []);
          setLoadingRooms(false);
        })
        .catch(() => setLoadingRooms(false));
    } else if (role === 'doctor') {
      client.get('/api/messages/rooms')
        .then(res => { setRooms(res.data.rooms || []); setLoadingRooms(false); })
        .catch(() => setLoadingRooms(false));
    } else {
      setLoadingRooms(false);
    }
  }, [role]);

  // Load messages when doctor selects a room
  const openRoom = async (room) => {
    setActiveRoom(room);
    try {
      const res = await client.get(`/api/messages/room/${room.patient_username}`);
      setMessages(res.data.messages || []);
      // Update unread count in sidebar
      setRooms(prev => prev.map(r => r.room_id === room.room_id ? { ...r, unread_count: 0 } : r));
    } catch {
      setMessages([]);
    }
  };

  // Socket listener for new messages
  useEffect(() => {
    if (!addListener) return;
    const handleNewMessage = (data) => {
      if (activeRoom && data.room_id === activeRoom.room_id) {
        setMessages(prev => [...prev, data]);
        // Mark as read
        client.post('/api/messages/mark-read', { room_id: data.room_id }).catch(() => {});
      } else {
        // Increment unread in sidebar
        setRooms(prev => prev.map(r => r.room_id === data.room_id ? { ...r, unread_count: (r.unread_count || 0) + 1 } : r));
      }
    };
    const handleTyping = () => {
      setTyping(true);
      if (typingTimeout.current) clearTimeout(typingTimeout.current);
      typingTimeout.current = setTimeout(() => setTyping(false), 3000);
    };

    addListener('new_message', handleNewMessage);
    addListener('typing', handleTyping);
    return () => {
      if (removeListener) {
        removeListener('new_message', handleNewMessage);
        removeListener('typing', handleTyping);
      }
    };
  }, [activeRoom, addListener, removeListener]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || !activeRoom) return;
    const text = input.trim();
    setInput('');

    // Optimistic update
    const optimistic = { message_id: Date.now(), sender_username: currentUser.username, content: text, created_at: new Date().toISOString() };
    setMessages(prev => [...prev, optimistic]);

    try {
      await client.post('/api/messages/send', { room_id: activeRoom.room_id, content: text });
    } catch (err) {
      console.error('Failed to send message', err);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    } else if (socket && activeRoom) {
      const recipient = role === 'doctor' ? activeRoom.patient_username : activeRoom.doctor_username;
      socket.emit('typing', { room_id: activeRoom.room_id, recipient_username: recipient });
    }
  };

  if (loadingRooms) return <div className="text-center py-8 text-slate-500">Loading messages...</div>;

  // Patient view: no sidebar, just messages
  if (role === 'patient') {
    if (!activeRoom) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-slate-400 text-sm gap-2">
          <MessageCircle size={32} className="opacity-30" />
          <p>No doctor assigned yet. Contact admin.</p>
        </div>
      );
    }
    return (
      <div className="flex flex-col h-[500px] bg-white rounded-lg border border-slate-200">
        <div className="px-4 py-3 border-b border-slate-100 bg-slate-50 rounded-t-lg">
          <p className="font-medium text-sm">Dr. {activeRoom.doctor_username}</p>
        </div>
        <MessageThread messages={messages} currentUser={currentUser} typing={typing} messagesEndRef={messagesEndRef} />
        <MessageInput input={input} setInput={setInput} handleKeyDown={handleKeyDown} sendMessage={sendMessage} />
      </div>
    );
  }

  // Doctor view: sidebar + messages
  return (
    <div className="flex h-[500px] bg-white rounded-lg border border-slate-200 overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 border-r border-slate-200 flex flex-col">
        <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
          <p className="text-xs font-semibold text-slate-500 uppercase">Conversations</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {rooms.length === 0 && <p className="text-sm text-slate-400 p-4">No conversations yet</p>}
          {rooms.map(room => (
            <button
              key={room.room_id}
              onClick={() => openRoom(room)}
              className={`w-full text-left px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition ${activeRoom?.room_id === room.room_id ? 'bg-indigo-50' : ''}`}
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-slate-700 truncate">{room.patient_username}</p>
                {room.unread_count > 0 && (
                  <span className="text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded-full">{room.unread_count}</span>
                )}
              </div>
              {room.last_message && <p className="text-xs text-slate-400 truncate mt-0.5">{room.last_message}</p>}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 flex flex-col">
        {!activeRoom ? (
          <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">Select a conversation</div>
        ) : (
          <>
            <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
              <p className="font-medium text-sm">{activeRoom.patient_username}</p>
            </div>
            <MessageThread messages={messages} currentUser={currentUser} typing={typing} messagesEndRef={messagesEndRef} />
            <MessageInput input={input} setInput={setInput} handleKeyDown={handleKeyDown} sendMessage={sendMessage} />
          </>
        )}
      </div>
    </div>
  );
}

function MessageThread({ messages, currentUser, typing, messagesEndRef }) {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.map((msg, idx) => {
        const isMine = msg.sender_username === currentUser?.username;
        return (
          <div key={msg.message_id || idx} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[70%] px-3 py-2 rounded-lg text-sm ${isMine ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-800'}`}>
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
  );
}

function MessageInput({ input, setInput, handleKeyDown, sendMessage }) {
  return (
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
  );
}
