import React, { useState, useEffect } from 'react';
import { MessageCircle } from 'lucide-react';
import client from '../api/client';

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  return `${Math.floor(hrs / 24)}d`;
}

export default function ChatRoomList({ onSelectRoom, activeRoomId }) {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get('/api/chat/rooms')
      .then(res => {
        const sorted = (res.data.rooms || []).sort(
          (a, b) => new Date(b.last_message_at || 0) - new Date(a.last_message_at || 0)
        );
        setRooms(sorted);
      })
      .catch(() => setRooms([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-4 text-slate-500 text-sm">Loading chats...</div>;

  if (rooms.length === 0) {
    return <div className="p-4 text-slate-500 text-sm">No conversations yet</div>;
  }

  return (
    <div className="divide-y">
      {rooms.map(room => (
        <div
          key={room.id}
          onClick={() => onSelectRoom?.(room)}
          className={`p-3 cursor-pointer hover:bg-slate-50 flex items-start gap-3 ${
            activeRoomId === room.id ? 'bg-indigo-50' : ''
          }`}
        >
          <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
            <MessageCircle size={16} className="text-indigo-600" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <p className="font-medium text-sm truncate">{room.other_user_name || 'User'}</p>
              <span className="text-xs text-slate-400">{timeAgo(room.last_message_at)}</span>
            </div>
            <p className="text-xs text-slate-500 truncate">
              {room.last_message ? room.last_message.slice(0, 50) : 'No messages'}
            </p>
          </div>
          {room.unread_count > 0 && (
            <span className="bg-indigo-600 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {room.unread_count}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
