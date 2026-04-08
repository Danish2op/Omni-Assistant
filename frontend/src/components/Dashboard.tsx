"use client";

import React, { useState, useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { 
  Send, 
  Database, 
  CheckCircle2, 
  Clock, 
  MessageSquare, 
  Search, 
  Zap,
  LayoutDashboard,
  Cpu,
  RefreshCw,
  Plus
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [messages, setMessages] = useState<{ role: 'user' | 'ai', text: string, intent?: string }[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [tasks, setTasks] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchData();
    //Initial mock message
    setMessages([{ 
      role: 'ai', 
      text: 'Omni-Assistant Online. Systems ready. How can I assist you in your command center today?',
      intent: 'SYSTEM'
    }]);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      const { data: taskData } = await supabase
        .from('tasks')
        .select('*')
        .order('created_at', { ascending: false });
      
      const { data: kbData } = await supabase
        .from('knowledge_base')
        .select('*')
        .order('timestamp', { ascending: false });

      setTasks(taskData || []);
      setKnowledge(kbData || []);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/chat`, { message: userMessage });
      const data = response.data;

      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: data.response || data.message || (data.status === 'Error' ? `System Error: ${data.error}` : "I've processed your request."),
        intent: data.intent
      }]);

      // AUTO-REFRESH Logic: If the agent did something, refresh the state
      if (data.intent === 'ORGANIZER' || data.intent === 'ARCHIVIST') {
        setTimeout(fetchData, 1000); // Small delay to let DB settle
      }
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: "Error communicating with the brain. Check backend status.",
        intent: 'ERROR'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {/* LEFT SIDEBAR: KNOWLEDGE PANEL */}
      <aside className="w-80 glass-panel border-r flex flex-col">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-accent animate-neon" />
            <h2 className="font-bold tracking-wider text-sm uppercase">Neural Core</h2>
          </div>
          <button onClick={fetchData} className={cn("text-gray-400 hover:text-accent transition-all", isRefreshing && "animate-spin")}>
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="text-[10px] uppercase text-gray-500 font-bold mb-2 tracking-[0.2em]">Knowledge Base</div>
          {knowledge.length === 0 ? (
            <div className="text-sm text-gray-600 italic p-4 text-center">No neural entries found.</div>
          ) : (
            knowledge.map((item) => (
              <div key={item.id} className="glass-card p-4 rounded-lg space-y-2">
                <div className="flex items-center gap-2 text-accent text-xs font-mono">
                  <Database className="w-3 h-3" />
                  <span>ENTRY_{item.id.slice(0, 4)}</span>
                </div>
                <p className="text-sm line-clamp-3 leading-relaxed opacity-90">{item.content}</p>
                <div className="text-[10px] text-gray-500 font-mono">
                  {new Date(item.timestamp).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* CENTER: CHAT HUB */}
      <main className="flex-1 flex flex-col relative">
        <header className="p-6 glass-panel border-b z-10">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-black italic tracking-tighter neon-text flex items-center gap-2">
              OMNI-AGENT <span className="text-xs font-normal not-italic text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">V1.0 LIVE</span>
            </h1>
            <div className="flex gap-4">
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                Backend: Online
              </div>
            </div>
          </div>
        </header>

        {/* Message Area */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth"
        >
          {messages.map((msg, i) => (
            <div 
              key={i} 
              className={cn(
                "flex flex-col max-w-[80%] space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300",
                msg.role === 'user' ? "ml-auto items-end" : "items-start"
              )}
            >
              <div className={cn(
                "px-5 py-3 rounded-2xl text-sm leading-relaxed",
                msg.role === 'user' 
                  ? "bg-accent-secondary text-white rounded-tr-none shadow-lg shadow-accent-secondary/20" 
                  : "glass-card rounded-tl-none border-l-2 border-l-accent"
              )}>
                {msg.role === 'ai' ? (
                  <article className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                        h1: ({ children }) => <h1 className="text-lg font-bold mb-2 text-blue-400">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-md font-bold mb-2 text-blue-300">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-sm font-bold mb-1 text-blue-200">{children}</h3>,
                        ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
                        li: ({ children }) => <li className="mb-1">{children}</li>,
                        strong: ({ children }) => <strong className="font-bold text-blue-300">{children}</strong>,
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  </article>
                ) : (
                  msg.text
                )}
              </div>
              {msg.intent && msg.intent !== 'UNKNOWN' && (
                <span className="text-[9px] font-mono text-accent uppercase tracking-widest px-2 py-1 rounded bg-accent/5 border border-accent/10">
                  INTENT_DETECTED: {msg.intent}
                </span>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex items-start gap-2 animate-pulse">
              <div className="glass-card px-5 py-3 rounded-2xl rounded-tl-none border-l-2 border-l-accent">
                <div className="flex gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce [animation-delay:0.2s]" />
                  <div className="w-1.5 h-1.5 rounded-full bg-accent animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-8 mt-auto">
          <form 
            onSubmit={sendMessage}
            className="flex items-center gap-3 glass-panel p-2 rounded-2xl border-white/10 ring-1 ring-white/5 shadow-2xl"
          >
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Input command for neural network..."
              className="flex-1 bg-transparent px-4 py-2 outline-none text-sm placeholder:text-gray-600"
              autoFocus
            />
            <button 
              type="submit"
              disabled={isLoading}
              className="aspect-square w-10 flex items-center justify-center bg-accent text-background rounded-xl hover:scale-105 transition-all shadow-[0_0_15px_rgba(0,242,255,0.4)] disabled:opacity-50 disabled:scale-100"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </main>

      {/* RIGHT SIDEBAR: TASK BOARD */}
      <aside className="w-80 glass-panel border-l flex flex-col">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent-secondary animate-pulse" />
            <h2 className="font-bold tracking-wider text-sm uppercase">Active Tasks</h2>
          </div>
          <div className="text-[10px] bg-accent-secondary/20 text-accent-secondary px-2 py-0.5 rounded-full font-bold">
            {tasks.filter(t => t.status === 'pending').length} ACTIVE
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="text-[10px] uppercase text-gray-500 font-bold mb-2 tracking-[0.2em]">Live Queue</div>
          {tasks.length === 0 ? (
            <div className="text-sm text-gray-600 italic p-4 text-center">Neural queue empty.</div>
          ) : (
            tasks.map((task) => (
              <div key={task.id} className={cn(
                "glass-card p-4 rounded-lg border-l-2 transition-all group",
                task.status === 'completed' ? "border-l-green-500 opacity-60" : "border-l-accent-secondary"
              )}>
                <div className="flex items-start justify-between mb-2">
                  <p className={cn(
                    "text-sm font-medium",
                    task.status === 'completed' && "line-through text-gray-500"
                  )}>{task.task_name}</p>
                  {task.status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : (
                    <div className="flex gap-1">
                      {task.priority === 'high' && <div className="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_5px_rgba(239,68,68,0.5)]" title="High Priority" />}
                      <Clock className="w-4 h-4 text-accent-secondary group-hover:rotate-12 transition-transform" />
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between text-[10px] text-gray-500 font-mono">
                  <span>DUE: {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'N/A'}</span>
                  <span className="uppercase text-[8px] bg-white/5 px-2 py-0.5 rounded">{task.status}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>
    </div>
  );
}
