"use client";

import React, { useState, useEffect, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Database, 
  CheckCircle2, 
  Clock, 
  MessageSquare, 
  User,
  Cpu, 
  Zap,
  LayoutDashboard,
  RefreshCw,
  Search,
  Activity,
  Terminal,
  ChevronRight,
  ShieldCheck,
  BrainCircuit,
  Command
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Real Tool-Chain Sequence Config
const STEP_SEQUENCES: Record<string, string[]> = {
  ANALYST: [
    "Router: Intent Identified (Analyst)",
    "Analyst: Querying Financial News API...",
    "Gemini: Synthesizing Market Briefing..."
  ],
  ARCHIVIST: [
    "Router: Intent Identified (Archivist)",
    "Archivist: Accessing Long-Term Memory...",
    "Gemini: Formatting Knowledge Retrieval..."
  ],
  ORGANIZER: [
    "Router: Intent Identified (Organizer)",
    "Organizer: Updating Task Queue...",
    "Gemini: Confirming Schedule Change..."
  ],
  GENERAL: [
    "Router: Intent Identified (General)",
    "Core: Accessing Linguistic Models...",
    "Gemini: Drafting Neural Response..."
  ],
  DEFAULT: [
    "Router: Identifying Neural Intent...",
    "Neural Core: Allocating Sub-Processors...",
    "Gemini: Processing Request..."
  ]
};

export default function Dashboard() {
  const [messages, setMessages] = useState<{ role: 'user' | 'ai', text: string, intent?: string }[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState(0);
  const [currentIntent, setCurrentIntent] = useState<string | null>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initial Fetch & Connection Health
  useEffect(() => {
    fetchData();
    console.log("Neural Core: Verifying Database Connection...");
    setMessages([{ 
      role: 'ai', 
      text: 'Neural Core Online. All monolith modules synchronized. Command line ready for neural orchestration.',
      intent: 'SYSTEM'
    }]);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading, loadingPhase]);

  const fetchData = async () => {
    setIsRefreshing(true);
    try {
      const { data: taskData, error: taskError } = await supabase
        .from('tasks')
        .select('*')
        .order('due_date', { ascending: true });
      
      const { data: kbData, error: kbError } = await supabase
        .from('knowledge_base')
        .select('*')
        .order('created_at', { ascending: false });

      if (taskError) console.error("Task Fetch Error:", taskError);
      if (kbError) console.error("KB Fetch Error:", kbError);

      setTasks(taskData || []);
      setKnowledge(kbData || []);
    } catch (error) {
      console.error('Core Logic Failure during data fetch:', error);
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
    setLoadingPhase(0);
    setCurrentIntent(null);

    // Simulate Thinking Progression
    const phaseInterval = setInterval(() => {
      setLoadingPhase(prev => (prev < 2 ? prev + 1 : prev));
    }, 1200);

    try {
      const response = await axios.post(`${API_URL}/chat`, { message: userMessage });
      const data = response.data;
      
      // Update intent mid-thinking if response arrives fast
      setCurrentIntent(data.intent);

      // Force high-end completion feel
      setTimeout(() => {
        clearInterval(phaseInterval);
        setMessages(prev => [...prev, { 
          role: 'ai', 
          text: data.response || data.message || (data.status === 'Error' ? `System Error: ${data.error}` : "Command executed successfully."),
          intent: data.intent
        }]);
        setIsLoading(false);
        
        // REFRESH CHECK: Immediate sync after STORE/CREATE actions
        if (data.intent === 'ORGANIZER' || data.intent === 'ARCHIVIST') {
          fetchData(); 
        }
      }, 800);

    } catch (error) {
      clearInterval(phaseInterval);
      setMessages(prev => [...prev, { 
        role: 'ai', 
        text: "Neural break detected. Response synthesis failed. Check connection to Core.",
        intent: 'ERROR'
      }]);
      setIsLoading(false);
    }
  };

  const currentSteps = STEP_SEQUENCES[currentIntent || 'DEFAULT'] || STEP_SEQUENCES.DEFAULT;

  return (
    <div className="flex h-screen w-full bg-[#050505] text-[#E0E0E0] overflow-hidden font-outfit selection:bg-cyan-500/30">
      <div className="neural-mesh opacity-40" />
      
      {/* LEFT MODULE: KNOWLEDGE (MONOLITH SIDEBAR) */}
      <motion.aside 
        initial={{ x: -100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "circOut" }}
        className="w-[320px] bg-[#0A0A0A]/80 backdrop-blur-xl border-r border-white/5 flex flex-col z-20"
      >
        <div className="p-10 pb-6 flex items-center justify-between">
          <div className="flex flex-col">
            <h2 className="text-[#00F5FF] text-[10px] font-bold uppercase tracking-[4px] mb-2">Memory Bank</h2>
            <div className="h-[1px] w-8 bg-[#00F5FF]/50" />
          </div>
          <button 
            onClick={fetchData} 
            disabled={isRefreshing}
            className={cn(
              "p-2 rounded-none border border-white/10 hover:border-[#00F5FF]/50 transition-all text-white/40 hover:text-[#00F5FF]",
              isRefreshing && "animate-spin"
            )}
          >
            <RefreshCw className="w-3 h-3" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-8 py-4 space-y-6 custom-scrollbar">
          {knowledge.length === 0 ? (
            <div className="text-[11px] text-white/10 italic py-10 text-center border border-dashed border-white/5 mx-2">
              Neural Memory Empty
            </div>
          ) : (
            knowledge.map((item, i) => (
              <motion.div 
                initial={{ x: -10, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                key={item.id} 
                className="group p-5 bg-white/[0.01] border border-white/5 hover:bg-[#00F5FF]/5 hover:border-[#00F5FF]/20 transition-all relative overflow-hidden"
              >
                <div className="absolute top-0 right-0 p-1">
                  <ShieldCheck className="w-2.5 h-2.5 text-white/10 group-hover:text-[#00F5FF]/40" />
                </div>
                <p className="text-[12px] leading-relaxed text-white/60 group-hover:text-white/90 transition-colors mb-3">{item.content}</p>
                <div className="flex items-center justify-between text-[9px] font-mono text-white/20">
                  <span className="bg-white/5 px-1.5 py-0.5">{item.category?.toUpperCase() || 'DATA'}</span>
                  <span>{new Date(item.created_at).toLocaleDateString()}</span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </motion.aside>

      {/* CENTER: CHAT HUB (THE MONOLITH) */}
      <main className="flex-1 flex flex-col relative z-10">
        <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-[#050505] to-transparent z-0" />
        
        <motion.header 
          initial={{ y: -50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="px-12 py-10 flex items-center justify-between relative z-10"
        >
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 border border-[#00F5FF]/30 flex items-center justify-center bg-[#00F5FF]/5 shadow-[0_0_20px_rgba(0,245,255,0.1)]">
              <BrainCircuit className="w-5 h-5 text-[#00F5FF]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-[-0.05em] text-white font-syne">
                OMNI<span className="text-[#00F5FF]">AGENT</span>
              </h1>
              <div className="flex items-center gap-4 mt-1">
                <span className="text-[9px] font-bold text-[#FFCC00]/60 uppercase tracking-[2px]">Core Version: 1.0.4</span>
                <div className="w-1 h-1 rounded-full bg-white/10" />
                <span className="text-[9px] font-bold text-white/20 uppercase tracking-[2px]">Latency: 18ms</span>
              </div>
            </div>
          </div>
          
          <div className="flex gap-2">
            <div className="px-3 py-1.5 border border-white/5 bg-white/[0.02] text-[9px] font-mono text-white/30 uppercase tracking-widest">
              Secured_Channel_Alpha
            </div>
          </div>
        </motion.header>

        {/* Message Terminal Area */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-10 px-12 py-10 hide-scrollbar"
        >
          <AnimatePresence mode="popLayout">
            {messages.map((msg, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex flex-col max-w-[80%] gap-3",
                  msg.role === 'user' ? "ml-auto items-end" : "items-start"
                )}
              >
                <div className={cn(
                  "flex items-center gap-2",
                  msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                )}>
                   <div className={cn(
                     "w-1 h-1 rounded-full",
                     msg.role === 'user' ? "bg-white/20" : "bg-[#00F5FF]"
                   )} />
                   <span className="text-[9px] font-bold uppercase tracking-[2px] text-white/30">
                     {msg.role === 'user' ? 'Local System' : 'Neural Dispatch'}
                   </span>
                </div>
                
                <div className={cn(
                  "p-6 border relative",
                  msg.role === 'user' 
                    ? "bg-[#111] border-white/5 text-white/90" 
                    : "bg-[#0A0A0A] border-[#00F5FF]/10 text-white shadow-[inset_0_0_20px_rgba(0,245,255,0.02)]"
                )}>
                  {msg.role === 'ai' && (
                    <div className="absolute top-0 left-0 w-[1px] h-full bg-[#00F5FF]/30" />
                  )}
                  
                  {msg.role === 'ai' ? (
                    <div className="prose prose-invert prose-sm max-w-none">
                      <ReactMarkdown
                        components={{
                          p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed opacity-80">{children}</p>,
                          h1: ({ children }) => <h1 className="text-lg font-syne text-[#00F5FF] mt-6 mb-3 uppercase tracking-tighter">{children}</h1>,
                          strong: ({ children }) => <strong className="text-[#00F5FF] font-bold">{children}</strong>,
                          ul: ({ children }) => <ul className="space-y-3 my-4 border-l border-white/5 pl-5">{children}</ul>,
                          li: ({ children }) => <li className="flex gap-2 before:content-['•'] before:text-[#00F5FF]/60">{children}</li>
                        }}
                      >
                        {msg.text}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm opacity-90">{msg.text}</p>
                  )}
                </div>
                {msg.intent && msg.intent !== 'SYSTEM' && (
                  <div className="flex items-center gap-2 border-t border-white/5 pt-2 w-full">
                    <span className="text-[8px] font-mono text-[#00F5FF]/40 uppercase tracking-[3px]">Silo: {msg.intent}</span>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4 border-l border-[#00F5FF]/10 pl-8 py-4 bg-white/[0.01]"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 rounded-full bg-[#00F5FF] animate-pulse shadow-[0_0_10px_#00F5FF]" />
                <span className="text-[10px] font-bold text-[#00F5FF] uppercase tracking-[3px]">Neural Orchestration In Progress</span>
              </div>
              {currentSteps.map((step, idx) => (
                <motion.div 
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ 
                    opacity: loadingPhase >= idx ? 1 : 0.1, 
                    x: loadingPhase >= idx ? 0 : -5 
                  }}
                  className="flex items-center gap-4 transition-all duration-700"
                >
                  <div className={cn(
                    "w-1 h-[10px] bg-white/10",
                    loadingPhase === idx && "bg-[#00F5FF] shadow-[0_0_5px_#00F5FF]"
                  )} />
                  <span className={cn(
                    "text-[10px] uppercase font-mono tracking-[4px]",
                    loadingPhase === idx ? "text-[#00F5FF] translate-x-1" : "text-white/10"
                  )}>
                    {step}
                  </span>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>

        {/* Neural Input Module */}
        <div className="p-12 pt-0 mt-auto relative z-10">
          <form 
            onSubmit={sendMessage}
            className="relative group"
          >
            <div className="absolute -inset-0.5 bg-[#00F5FF]/10 opacity-0 group-focus-within:opacity-100 transition duration-1000 blur-xl" />
            <div className="relative bg-[#0A0A0A] border border-white/10 group-focus-within:border-[#00F5FF]/40 transition-all flex items-center p-1">
              <div className="px-5 text-white/20">
                <Command className="w-4 h-4" />
              </div>
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="AWAITING NEURAL COMMAND..."
                className="flex-1 bg-transparent px-4 py-6 outline-none text-xs font-mono tracking-[0.2em] placeholder:text-white/5 text-white/90 uppercase"
                autoFocus
              />
              <button 
                type="submit"
                disabled={isLoading}
                className="w-20 h-16 flex items-center justify-center bg-white/5 hover:bg-[#00F5FF] hover:text-black transition-all group-disabled:opacity-10"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </form>
          <div className="mt-4 flex justify-between text-[8px] font-mono text-white/10 uppercase tracking-[3px]">
            <span>Channel_01: ACTIVE</span>
            <span>Encryption_Type: QUANTUM_AES</span>
          </div>
        </div>
      </main>

      {/* RIGHT MODULE: TASKS (THE QUEUE) */}
      <motion.aside 
        initial={{ x: 100, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "circOut" }}
        className="w-[360px] bg-[#0A0A0A]/80 backdrop-blur-xl border-l border-white/5 flex flex-col z-20"
      >
        <div className="p-10 pb-6">
          <h2 className="text-[#00F5FF] text-[10px] font-bold uppercase tracking-[4px] mb-2">Task Pipeline</h2>
          <div className="h-[1px] w-8 bg-[#00F5FF]/50" />
        </div>

        <div className="flex-1 overflow-y-auto px-8 py-4 space-y-4 custom-scrollbar">
          {tasks.length === 0 ? (
            <div className="text-[11px] text-white/10 italic py-10 text-center border border-dashed border-white/5 mx-2">
              Queue Standby
            </div>
          ) : (
            tasks.map((task, i) => (
              <motion.div 
                initial={{ x: 10, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                key={task.id} 
                className={cn(
                  "p-5 border relative group transition-all",
                  task.status === 'completed' 
                    ? "bg-transparent border-white/5 opacity-30 grayscale" 
                    : "bg-white/[0.01] border-white/10 hover:border-[#00F5FF]/40"
                )}
              >
                {task.status === 'pending' && (
                  <div className="absolute top-0 left-0 w-1 h-1 bg-[#00F5FF]/60" />
                )}
                
                <div className="flex items-start justify-between gap-4 mb-4">
                  <p className={cn(
                    "text-[12px] font-bold tracking-tight text-white/80",
                    task.status === 'completed' && "line-through"
                  )}>{task.task_name}</p>
                  <div className="mt-1">
                    {task.status === 'completed' ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#00F5FF]" />
                    ) : (
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        task.priority === 'high' ? "bg-red-500 animate-pulse shadow-[0_0_8px_red]" : "bg-white/10"
                      )} />
                    )}
                  </div>
                </div>
                
                <div className="flex items-center justify-between text-[8px] font-mono tracking-widest text-white/30">
                  <span className="border-l border-white/10 pl-2 uppercase">{task.priority || 'NORMAL'}</span>
                  <span>{task.due_date ? new Date(task.due_date).toLocaleDateString() : 'NO_DEADLINE'}</span>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </motion.aside>
    </div>
  );
}
