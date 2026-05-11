import { useState, useCallback } from 'react';
import axios from 'axios';

export type Message = { role: 'user' | 'ai'; text: string; intent?: string };
export type ProcessLog = { message: string; timestamp: number };

interface UseChatStreamOptions {
  apiUrl: string;
  onRefreshData?: () => void;
}

export function useChatStream({ apiUrl, onRefreshData }: UseChatStreamOptions) {
  const [isLoading, setIsLoading] = useState(false);
  const [currentIntent, setCurrentIntent] = useState<string | null>(null);
  const [ttfb, setTtfb] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [processLogs, setProcessLogs] = useState<ProcessLog[]>([]);
  const [startTime, setStartTime] = useState<number | null>(null);

  const startStream = useCallback((message: string) => {
    setIsLoading(true);
    setCurrentIntent(null);
    setTtfb(null);
    setStartTime(Date.now());
    setMessages((prev) => [...prev, { role: 'user', text: message }]);
    setProcessLogs([{ message: 'Initiating neural uplink...', timestamp: Date.now() }]);
  }, []);

  const handleStreamEvent = useCallback((event: any) => {
    if (event.type === 'ROUTER') {
      setCurrentIntent(event.intent);
      setProcessLogs((prev) => [...prev, { message: `Intent identified: ${event.intent}`, timestamp: Date.now() }]);
    } else if (event.type === 'AGENT') {
      setProcessLogs((prev) => [...prev, { message: `Dispatching to specialized agent: ${event.name}`, timestamp: Date.now() }]);
    } else if (event.type === 'TEXT') {
      setIsLoading(false);
      
      setTtfb((prev) => {
        if (prev === null) {
          setStartTime((st) => {
            const delay = Date.now() - (st || Date.now());
            setProcessLogs((logs) => [...logs, { message: `Response stream established (TTFB: ${delay}ms)`, timestamp: Date.now() }]);
            return st;
          });
          return Date.now() - (startTime || Date.now());
        }
        return prev;
      });
      
      setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        if (lastMsg && lastMsg.role === 'ai') {
          return [
            ...prev.slice(0, -1),
            { ...lastMsg, text: lastMsg.text + (event.content || '') }
          ];
        } else {
          return [
            ...prev,
            { role: 'ai', text: event.content || '', intent: currentIntent || undefined }
          ];
        }
      });
    } else if (event.type === 'ERROR') {
      setIsLoading(false);
      setProcessLogs((prev) => [...prev, { message: `Stream error: ${event.message}`, timestamp: Date.now() }]);
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: event.message || 'Stream error.', intent: 'ERROR' }
      ]);
    }
  }, [currentIntent, startTime]);

  const sendMessage = useCallback(async (userMessage: string) => {
    startStream(userMessage);

    let detectedIntent: string | null = null;
    let messageAdded = false;

    try {
      let response: Response | null = null;
      // Retry up to 12 times (max ~60s total wait) for cold starts
      for (let attempt = 0; attempt < 12; attempt++) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 120000);
        try {
          response = await fetch(`${apiUrl}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userMessage }),
            signal: controller.signal,
          });
          clearTimeout(timeout);
          if (response.ok) break;
          
          if (response.status === 502 || response.status === 503) {
            setProcessLogs((prev) => [...prev, { message: `Server cold start detected. Waking up instance (Attempt ${attempt + 1}/12)...`, timestamp: Date.now() }]);
            await new Promise((r) => setTimeout(r, 5000));
            continue;
          }
          break; // If it's a 4xx or other 5xx, break out
        } catch (fetchErr) {
          clearTimeout(timeout);
          // If fetch throws, it's likely a CORS error caused by the 502 response not having CORS headers
          setProcessLogs((prev) => [...prev, { message: `Network request failed. Waking up instance (Attempt ${attempt + 1}/12)...`, timestamp: Date.now() }]);
          await new Promise((r) => setTimeout(r, 5000));
        }
      }

      if (!response || !response.ok || !response.body) {
        throw new Error(`Stream failed: ${response?.status || 'no response'}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const payload = line.slice(6);
          if (payload === '[DONE]') continue;

          try {
            const event = JSON.parse(payload);
            
            if (event.type === 'ROUTER') {
              detectedIntent = event.intent;
              setCurrentIntent(event.intent);
            } else if (event.type === 'TEXT') {
              messageAdded = true;
            }
            
            handleStreamEvent(event);
            
            if (event.type === 'ERROR') {
              return;
            }
          } catch {
            // Skip malformed JSON
          }
        }
      }

      if (!messageAdded) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'ai',
            text: 'No response generated.',
            intent: detectedIntent || undefined,
          },
        ]);
        setIsLoading(false);
      }

      if (detectedIntent === 'ORGANIZER' || detectedIntent === 'ARCHIVIST') {
        onRefreshData?.();
      }

    } catch (error) {
      setProcessLogs((prev) => [...prev, { message: `Streaming failed, falling back to standard request...`, timestamp: Date.now() }]);
      try {
        const fallbackRes = await axios.post(`${apiUrl}/chat`, { message: userMessage });
        const data = fallbackRes.data;
        setMessages((prev) => [
          ...prev,
          {
            role: 'ai',
            text: data.response || data.message || 'Executed.',
            intent: data.intent,
          },
        ]);
        if (data.intent === 'ORGANIZER' || data.intent === 'ARCHIVIST') {
          onRefreshData?.();
        }
      } catch {
        setProcessLogs((prev) => [...prev, { message: `Neural break detected. Response synthesis failed. Check connection to Core.`, timestamp: Date.now() }]);
        setMessages((prev) => [
          ...prev,
          {
            role: 'ai',
            text: 'Neural break detected. Response synthesis failed. Check connection to Core.',
            intent: 'ERROR',
          },
        ]);
      }
      setIsLoading(false);
    }
  }, [apiUrl, startStream, handleStreamEvent, onRefreshData]);

  return {
    isLoading,
    currentIntent,
    ttfb,
    messages,
    processLogs,
    startStream,
    handleStreamEvent,
    sendMessage,
    setMessages,
    setIsLoading
  };
}

