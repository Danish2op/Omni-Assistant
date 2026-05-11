"use client";

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
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
import { useChatStream } from '../hooks/useChatStream';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function Dashboard() {
  const [input, setInput] = useState('');
  const [tasks, setTasks] = useState<any[]>([]);
  const [knowledge, setKnowledge] = useState<any[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [mounted, setMounted] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const fetchData = async () => {
    setIsRefreshing(true);
    console.log("Neural Core: Fetching sidebar data via backend API...");
    try {
      const [tasksRes, knowledgeRes] = await Promise.all([
        axios.get(`${API_URL}/tasks`),
        axios.get(`${API_URL}/knowledge`)
      ]);

      const taskData = tasksRes.data?.tasks || [];
      const kbData = knowledgeRes.data?.knowledge || [];

      console.log(`Neural Core: Sync complete. Tasks=${taskData.length}, KB=${kbData.length}`);
      setTasks(taskData);
      setKnowledge(kbData);
    } catch (error) {
      console.error('Core Logic Failure during data fetch:', error);
    } finally {
      setIsRefreshing(false);
    }
  };

  const {
    isLoading,
    currentIntent,
    ttfb,
    messages,
    processLogs,
    sendMessage,
    setMessages
  } = useChatStream({
    apiUrl: API_URL,
    onRefreshData: fetchData
  });

  // Wake up Render free tier + initial data fetch
  useEffect(() => {
    setMounted(true);
    // Pre-warm: fire-and-forget health ping (wakes cold Render instance)
    fetch(`${API_URL}/health`).catch(() => {});
    fetchData();
    console.log("Neural Core: Verifying Database Connection...");
    setMessages([{ 
      role: 'ai', 
      text: 'Neural Core Online. All monolith modules synchronized. Command line ready for neural orchestration.',
      intent: 'SYSTEM'
    }]);
  }, [setMessages]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading, processLogs]);

  // Background Sync Interval (30s)
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isLoading && !isRefreshing) {
        console.log("Neural Core: Background sync initiated...");
        fetchData();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [isLoading, isRefreshing]);


  const toggleTaskStatus = async (taskId: string, currentStatus: string) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';
    try {
      await axios.patch(`${API_URL}/tasks/update`, { task_id: taskId, status: newStatus });
      fetchData(); // Refresh UI
    } catch (error) {
      console.error("Failed to update task status:", error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    await sendMessage(userMessage);
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden font-inter selection:bg-accent/30 selection:text-white">
      <div className="grid-bg" />
      
      {/* LEFT MODULE: KNOWLEDGE (SYSTEM INDEX) */}
      <motion.aside 
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "circOut" }}
        className="w-[300px] glass-panel backdrop-blur-xl bg-surface/40 border-r border-border m-4 flex flex-col z-20 rounded-sm"
      >
        <div className="p-6 border-b border-border flex items-center justify-between">
          <div className="flex flex-col">
            <h2 className="text-accent text-[10px] font-bold uppercase tracking-[3px] mb-1 font-syne">System Index</h2>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-foreground/30 font-mono">NODE: MEMORY_BANK</span>
              {isRefreshing && (
                <span className="text-[8px] text-accent font-mono animate-pulse uppercase tracking-[0.2em]">[SYNCING]</span>
              )}
            </div>
          </div>
          <button 
            onClick={fetchData} 
            disabled={isRefreshing}
            className={cn(
              "p-2 rounded-sm border border-border hover:bg-accent/5 transition-all text-foreground/40 hover:text-accent",
              isRefreshing && "animate-spin"
            )}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 custom-scrollbar">
          {knowledge.length === 0 && isRefreshing ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="p-4 border border-border/50 bg-surface/50 rounded-sm overflow-hidden relative">
                <div className="h-3 w-3/4 bg-foreground/5 rounded-sm mb-3 animate-pulse" />
                <div className="h-3 w-1/2 bg-foreground/5 rounded-sm animate-pulse" />
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/5 to-transparent -translate-x-full animate-shimmer" />
              </div>
            ))
          ) : knowledge.length === 0 ? (
            <div className="text-[10px] text-foreground/20 font-mono py-10 text-center border border-dashed border-border rounded-sm">
              [EMPTY_SET]
            </div>
          ) : (
            knowledge.map((item, i) => (
              <motion.div 
                initial={{ y: 10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                key={item.id} 
                className="group p-4 bg-surface border border-border hover:border-accent/40 transition-all relative rounded-sm"
              >
                <div className="absolute top-2 right-2 flex gap-1">
                  <div className="w-1 h-1 rounded-full bg-accent/20 group-hover:bg-accent" />
                </div>
                <p className="text-[11px] leading-relaxed text-foreground/70 group-hover:text-foreground transition-colors mb-3 font-inter">{item.content}</p>
                <div className="flex items-center justify-between text-[8px] font-mono text-foreground/30 uppercase">
                  <span className="bg-white/5 px-1.5 py-0.5 rounded-sm">{item.category || 'DATA'}</span>
                  <span>{mounted ? new Date(item.created_at).toLocaleDateString() : 'LOADING...'}</span>
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
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="px-12 py-8 flex items-center justify-between relative z-10 border-b border-border/50 backdrop-blur-md bg-background/60"
        >
          <div className="flex items-center gap-5">
            <div className="p-2 border border-accent/20 bg-accent/5 rounded-sm">
              <BrainCircuit className="w-6 h-6 text-accent" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-[-0.03em] text-foreground font-syne">
                  OMNI<span className="text-accent/80">CORE</span>
                </h1>
                <span className="text-[8px] px-2 py-0.5 border border-accent/20 text-accent font-mono tracking-tighter rounded-full bg-accent/5">{process.env.NODE_ENV === 'development' ? 'DEV_ENV' : 'PROD_ENV'}</span>
              </div>
              <div className="flex items-center gap-3 mt-1.5 font-mono">
                <div className="flex items-center gap-1.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-success/80 shadow-[0_0_8px_var(--success)]" />
                  <span className="text-[8px] text-foreground/40 uppercase tracking-widest">Network Link: {ttfb !== null ? 'ACTIVE' : 'CONNECTING...'}</span>
                </div>
                <div className="w-[1px] h-2 bg-border" />
                <span className="text-[8px] text-foreground/40 uppercase tracking-widest">LATENCY: {ttfb !== null ? `${ttfb}MS` : 'CALCULATING...'}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 border border-border bg-surface text-[8px] font-mono text-foreground/30 uppercase tracking-[0.2em] rounded-sm">
              WORKSPACE
            </div>
          </div>
        </motion.header>

        {/* Message Terminal Area */}
        <div 
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-8 px-12 py-10 hide-scrollbar"
        >
          <AnimatePresence mode="popLayout">
            {messages.map((msg, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex flex-col gap-2.5",
                  msg.role === 'user' ? "items-end" : "items-start"
                )}
              >
                <div className={cn(
                  "flex items-center gap-2 px-1",
                  msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                )}>
                   <div className={cn(
                     "w-1.5 h-1.5 rounded-full",
                     msg.role === 'user' ? "bg-foreground/20" : "bg-accent shadow-[0_0_8px_var(--accent)]"
                   )} />
                   <span className="text-[8px] font-bold uppercase tracking-[0.2em] text-foreground/30 font-mono">
                     {msg.role === 'user' ? 'LOCAL_UPLINK' : 'NEURAL_DISPATCH'}
                   </span>
                </div>
                
                <div className={cn(
                  "max-w-[85%] p-5 border relative group transition-all",
                  msg.role === 'user' 
                    ? "bg-surface-alt border-border text-foreground/90 rounded-sm rounded-tr-none" 
                    : "bg-surface border-accent/10 text-foreground rounded-sm rounded-tl-none border-l-2 border-l-accent"
                )}>
                  {msg.role === 'ai' ? (
                    <div className="prose prose-invert prose-xs max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({ children }) => <p className="mb-4 last:mb-0 leading-relaxed font-inter text-[13px] text-foreground/80">{children}</p>,
                          h1: ({ children }) => <h1 className="text-sm font-syne text-accent mt-6 mb-3 uppercase tracking-tighter border-b border-accent/20 pb-1">{children}</h1>,
                          h2: ({ children }) => <h2 className="text-[13px] font-syne text-foreground mt-5 mb-2 font-bold uppercase">{children}</h2>,
                          h3: ({ children }) => <h3 className="text-[12px] font-syne text-foreground/90 mt-4 mb-2 font-semibold uppercase">{children}</h3>,
                          strong: ({ children }) => <strong className="text-accent font-bold">{children}</strong>,
                          ul: ({ children }) => <ul className="space-y-2 my-4 pl-4 list-disc marker:text-accent/50">{children}</ul>,
                          ol: ({ children }) => <ol className="space-y-2 my-4 pl-4 list-decimal marker:text-accent/50 text-[12px] text-foreground/70">{children}</ol>,
                          li: ({ children }) => <li className="text-[12px] text-foreground/70 pl-1">{children}</li>,
                          a: ({ children, href }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">{children}</a>,
                          blockquote: ({ children }) => <blockquote className="border-l-2 border-accent/50 pl-3 italic text-foreground/60 my-3">{children}</blockquote>,
                          code: ({ inline, className, children, ...props }: any) => {
                            const match = /language-(\w+)/.exec(className || '')
                            return !inline ? (
                              <pre className="bg-surface-alt p-3 rounded-sm overflow-x-auto text-[11px] font-mono text-foreground/80 my-3 border border-border">
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              </pre>
                            ) : (
                              <code className="bg-surface-alt px-1 py-0.5 rounded-sm text-[11px] font-mono text-accent/90" {...props}>
                                {children}
                              </code>
                            )
                          }
                        }}
                      >
                        {msg.text}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <p className="text-sm font-inter text-foreground/90">{msg.text}</p>
                  )}
                </div>
                {msg.intent && msg.intent !== 'SYSTEM' && (
                  <div className="flex items-center gap-2 px-1">
                    <span className="text-[7px] font-mono text-accent/40 uppercase tracking-[0.3em]">RECV_INTENT: {msg.intent}</span>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-4 border-l border-accent/20 pl-8 py-6 bg-surface/30 rounded-r-sm"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-2 h-2 rounded-full bg-accent animate-pulse shadow-[0_0_12px_var(--accent)]" />
                <span className="text-[10px] font-bold text-accent uppercase tracking-[0.3em] font-syne">Async Process Active</span>
              </div>
              <div className="space-y-3">
                {processLogs.map((log, idx) => (
                  <motion.div 
                    key={idx}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-4 transition-all duration-500"
                  >
                    <div className="w-4 h-[1px] bg-accent shadow-[0_0_8px_var(--accent)]" />
                    <span className="text-[9px] uppercase font-mono tracking-[0.2em] text-accent">
                      {log.message}
                    </span>
                  </motion.div>
                ))}
              </div>
              <div className="thought-chain-line w-1/2 opacity-20" />
            </motion.div>
          )}
        </div>

        {/* Neural Input Module */}
        <div className="px-12 py-10 pt-0 mt-auto relative z-10">
          <form 
            onSubmit={handleSendMessage}
            className="relative"
          >
            <div className="absolute -inset-1 bg-accent/5 blur-2xl opacity-0 group-focus-within:opacity-100 transition-opacity pointer-events-none" />
            <div className="relative glass-panel bg-surface border-border group-focus-within:border-accent/30 transition-all flex items-center p-1.5 rounded-sm">
              <div className="px-5 text-foreground/20">
                <Terminal className="w-4 h-4" />
              </div>
              <input 
                type="text" 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="AWAITING_INPUT_COMMAND..."
                className="flex-1 bg-transparent px-4 py-5 outline-none text-[13px] font-mono tracking-[0.1em] placeholder:text-foreground/10 text-foreground w-full"
                autoFocus
              />
              <button 
                type="submit"
                disabled={isLoading}
                className="px-8 py-5 flex items-center justify-center bg-foreground/5 hover:bg-accent hover:text-background transition-all rounded-sm disabled:opacity-20 font-syne font-bold text-[10px] tracking-widest uppercase"
              >
                Execute
              </button>
            </div>
          </form>
          <div className="mt-4 flex justify-between text-[7px] font-mono text-foreground/20 uppercase tracking-[0.4em]">
            <div className="flex gap-4">
              <span>UPLINK: {API_URL}</span>
              <span>AUTH: SESSION_ACTIVE</span>
            </div>
            <span>[SYS_CLK: {mounted ? new Date().toLocaleTimeString() : '--:--:--'}]</span>
          </div>
        </div>
      </main>

      {/* RIGHT MODULE: TASKS (THE PIPELINE) */}
      <motion.aside 
        initial={{ x: 20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.8, ease: "circOut" }}
        className="w-[340px] glass-panel backdrop-blur-xl bg-surface/40 border-l border-border m-4 flex flex-col z-20 rounded-sm"
      >
        <div className="p-6 border-b border-border">
          <h2 className="text-accent text-[10px] font-bold uppercase tracking-[3px] mb-1 font-syne">Operation Pipeline</h2>
          <div className="flex items-center gap-2">
            <span className="text-[9px] text-foreground/30 font-mono">NODE: TASK_ORCHESTRATOR</span>
            {isRefreshing && (
              <span className="text-[8px] text-accent font-mono animate-pulse uppercase tracking-[0.2em]">[POLLING]</span>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-3 custom-scrollbar">
          {tasks.length === 0 && isRefreshing ? (
             Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="p-4 border border-border/50 bg-surface/50 rounded-sm overflow-hidden relative">
                <div className="h-4 w-full bg-foreground/5 rounded-sm mb-4 animate-pulse" />
                <div className="flex justify-between">
                  <div className="h-2 w-1/4 bg-foreground/5 rounded-sm animate-pulse" />
                  <div className="h-2 w-1/4 bg-foreground/5 rounded-sm animate-pulse" />
                </div>
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-accent/5 to-transparent -translate-x-full animate-shimmer" />
              </div>
            ))
          ) : tasks.length === 0 ? (
            <div className="text-[10px] text-foreground/20 font-mono py-10 text-center border border-dashed border-border rounded-sm">
              [STANDBY_MODE]
            </div>
          ) : (
            tasks.map((task, i) => (
              <motion.div 
                initial={{ y: 10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                key={task.id} 
                className={cn(
                  "p-4 border relative group transition-all rounded-sm",
                  task.status === 'completed' 
                    ? "bg-transparent border-border/30 opacity-40 grayscale" 
                    : "bg-surface border-border hover:border-accent/40",
                  task.priority === 'high' && !task.status?.includes('completed') && "priority-high",
                  task.priority === 'medium' && !task.status?.includes('completed') && "priority-medium",
                  (task.priority === 'low' || !task.priority) && !task.status?.includes('completed') && "priority-low"
                )}
              >
                <div className="flex items-start justify-between gap-3 mb-4">
                  <p className={cn(
                    "text-[11px] font-semibold tracking-tight text-foreground/90 leading-snug",
                    task.status === 'completed' && "line-through text-foreground/40"
                  )}>{task.task_name}</p>
                  <div className="mt-0.5">
                    <button 
                      onClick={() => toggleTaskStatus(task.id, task.status)}
                      className={cn(
                        "p-1 rounded-sm border transition-all",
                        task.status === 'completed' 
                          ? "border-accent bg-accent/20 text-accent" 
                          : "border-border hover:border-accent/50 text-foreground/20 hover:text-accent/50"
                      )}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
                
                <div className="flex items-center justify-between text-[8px] font-mono tracking-wider text-foreground/30 uppercase">
                  <span className="px-1 py-0.5 bg-foreground/5 rounded-sm">{task.priority || 'NORMAL'}</span>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-2.5 h-2.5" />
                    <span>
                      {mounted && task.due_date 
                        ? `${new Date(task.due_date).toLocaleDateString()} | ${new Date(task.due_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` 
                        : (task.due_date ? 'SYNCING' : 'OPEN_THREAD')
                      }
                    </span>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </motion.aside>
    </div>
  );
}
