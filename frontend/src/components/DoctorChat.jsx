import React, { useState, useEffect, useRef } from 'react';
import { Send, MessageCircle, Search, User, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import client from '../api/client';
import { useSocket } from '../contexts/SocketContext';
import { useAuth } from '../hooks/useAuth';

export default function DoctorChat() {
  const [rooms, setRooms] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeRoom, setActiveRoom] = useState(null);
  const [activeDoctorName, setActiveDoctorName] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [typing, setTyping] = useState(false);
  const [loadingRooms, setLoadingRooms] = useState(true);
  const [expandedForward, setExpandedForward] = useState(null);
  const [forwardReports, setForwardReports] = useState({});
  const messagesEndRef = useRef(null);
  const typingTimeout = useRef(null);
  const { socket, addListener, removeListener } = useSocket() || {};
  const { getUser } = useAuth();
  const currentUser = getUser();

  // Fetch rooms and doctors on mount
  useEffect(() => {
    client.get('/api/messages/rooms')
      .then(res => { setRooms(res.data.rooms || []); setLoadingRooms(false); })
      .catch(() => setLoadingRooms(false));

    client.get('/api/messages/doctors')
      .then(res => setDoctors(res.data.doctors || []))
      .catch(() => setDoctors([]));
  }, []);

  // Open a room with another doctor
  const openRoom = async (otherDoctorUsername) => {
    setActiveDoctorName(otherDoctorUsername);
    try {
      const res = await client.get(`/api/messages/room/${otherDoctorUsername}`);
      setActiveRoom({ room_id: res.data.room_id, other_doctor_username: otherDoctorUsername });
      setMessages(res.data.messages || []);
      // Update unread count in sidebar
      setRooms(prev => prev.map(r =>
        r.other_doctor_username === otherDoctorUsername ? { ...r, unread_count: 0 } : r
      ));
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
        client.post('/api/messages/mark-read', { room_id: data.room_id }).catch(() => {});
      } else {
        setRooms(prev => prev.map(r =>
          r.room_id === data.room_id ? { ...r, unread_count: (r.unread_count || 0) + 1 } : r
        ));
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

    const optimistic = {
      message_id: Date.now(),
      sender_username: currentUser.username,
      content: text,
      message_type: 'text',
      created_at: new Date().toISOString(),
    };
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
      socket.emit('typing', { room_id: activeRoom.room_id, recipient_username: activeRoom.other_doctor_username });
    }
  };

  // Fetch patient reports for a forwarded case
  const fetchReports = async (patientUsername, msgId) => {
    if (expandedForward === msgId) {
      setExpandedForward(null);
      return;
    }
    setExpandedForward(msgId);
    if (forwardReports[patientUsername]) return;
    try {
      const res = await client.get(`/api/reports?username=${patientUsername}`);
      setForwardReports(prev => ({ ...prev, [patientUsername]: res.data.records || res.data.reports || [] }));
    } catch {
      setForwardReports(prev => ({ ...prev, [patientUsername]: [] }));
    }
  };

  // Filter doctors by search
  const filteredDoctors = searchQuery.trim()
    ? doctors.filter(d =>
        d.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        d.specialization.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : [];

  if (loadingRooms) return <div className="text-center py-8 text-slate-500">Loading messages...</div>;

  return (
    <div className="flex h-[550px] bg-white rounded-lg border border-slate-200 overflow-hidden">
      {/* Left Panel: Search + Conversations */}
      <div className="w-72 border-r border-slate-200 flex flex-col">
        {/* Search */}
        <div className="px-3 py-3 border-b border-slate-100">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search doctors..."
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {/* Search results dropdown */}
          {filteredDoctors.length > 0 && (
            <div className="mt-2 max-h-40 overflow-y-auto border border-slate-200 rounded-lg bg-white shadow-lg">
              {filteredDoctors.map(doc => (
                <button
                  key={doc.username}
                  onClick={() => { openRoom(doc.username); setSearchQuery(''); }}
                  className="w-full text-left px-3 py-2 hover:bg-indigo-50 transition flex items-center gap-2"
                >
                  <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center">
                    <User size={14} className="text-indigo-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-700">Dr. {doc.username}</p>
                    <p className="text-xs text-slate-400">{doc.specialization}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Conversation list */}
        <div className="px-3 py-2 border-b border-slate-50">
          <p className="text-xs font-semibold text-slate-500 uppercase">Conversations</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {rooms.length === 0 && <p className="text-sm text-slate-400 p-4">No conversations yet. Search for a doctor to start chatting.</p>}
          {rooms.map(room => (
            <button
              key={room.room_id}
              onClick={() => openRoom(room.other_doctor_username)}
              className={`w-full text-left px-3 py-3 border-b border-slate-50 hover:bg-slate-50 transition ${activeRoom?.room_id === room.room_id ? 'bg-indigo-50' : ''}`}
            >
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0">
                  <User size={14} className="text-indigo-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-700 truncate">Dr. {room.other_doctor_username}</p>
                    {room.unread_count > 0 && (
                      <span className="text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded-full">{room.unread_count}</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 truncate mt-0.5">
                    {room.last_message_type === 'case_forward' ? '📋 Case Forwarded' : (room.last_message || 'No messages yet')}
                  </p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Right Panel: Message Thread */}
      <div className="flex-1 flex flex-col">
        {!activeRoom ? (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 text-sm gap-2">
            <MessageCircle size={32} className="opacity-30" />
            <p>Select a conversation or search for a doctor</p>
          </div>
        ) : (
          <>
            <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
              <p className="font-medium text-sm text-slate-700">Dr. {activeDoctorName}</p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, idx) => {
                const isMine = msg.sender_username === currentUser?.username;

                // Case forward message
                if (msg.message_type === 'case_forward') {
                  let forwardInfo = {};
                  try { forwardInfo = JSON.parse(msg.content); } catch { forwardInfo = {}; }
                  const isExpanded = expandedForward === (msg.message_id || idx);
                  const reports = forwardReports[forwardInfo.patient_username] || [];

                  return (
                    <div key={msg.message_id || idx} className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-[80%] rounded-lg border cursor-pointer transition-all ${
                          isMine ? 'bg-indigo-50 border-indigo-200' : 'bg-amber-50 border-amber-200'
                        }`}
                        onClick={() => fetchReports(forwardInfo.patient_username, msg.message_id || idx)}
                      >
                        <div className="px-4 py-3">
                          <div className="flex items-center gap-2 mb-1">
                            <FileText size={16} className="text-indigo-600" />
                            <span className="text-sm font-semibold text-slate-700">📋 Case Forwarded: {forwardInfo.patient_username}</span>
                          </div>
                          <p className="text-xs text-slate-500">Date: {forwardInfo.slot_date} at {forwardInfo.slot_time}</p>
                          {forwardInfo.notes && <p className="text-xs text-slate-500 mt-1">Notes: {forwardInfo.notes}</p>}
                          <div className="flex items-center gap-1 mt-2 text-xs text-indigo-600">
                            {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                            <span>{isExpanded ? 'Hide reports' : 'Click to view reports'}</span>
                          </div>
                        </div>

                        {/* Expanded: show patient reports */}
                        {isExpanded && (
                          <div className="border-t border-slate-200 px-4 py-3 bg-white rounded-b-lg">
                            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Patient Reports</p>
                            {reports.length === 0 ? (
                              <p className="text-xs text-slate-400">No reports found</p>
                            ) : (
                              <div className="space-y-2 max-h-48 overflow-y-auto">
                                {reports.slice(0, 5).map((report, rIdx) => (
                                  <div key={rIdx} className="text-xs bg-slate-50 rounded p-2 border border-slate-100">
                                    <div className="flex justify-between">
                                      <span className="font-medium text-slate-700">{report.date || report.created_at || 'N/A'}</span>
                                      <span className={`font-semibold ${report.severity_level === 'severe' ? 'text-red-600' : report.severity_level === 'moderate' ? 'text-amber-600' : 'text-green-600'}`}>
                                        {report.severity_level || 'N/A'}
                                      </span>
                                    </div>
                                    <p className="text-slate-500 mt-1">HGB: {report.hgb || '—'} g/dL | Type: {report.anemia_type || '—'}</p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        <p className={`text-xs px-4 pb-2 ${isMine ? 'text-indigo-300' : 'text-slate-400'}`}>
                          {msg.created_at ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                        </p>
                      </div>
                    </div>
                  );
                }

                // Normal text message
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

            {/* Input */}
            <div className="border-t p-3 flex gap-2">
              <input
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type a message..."
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={sendMessage}
                disabled={!input.trim()}
                className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                <Send size={18} />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
