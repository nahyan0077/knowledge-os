'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Message, MessageStatus, MessageRole, LlmUsage } from '@/shared/types';
import { useParams, useRouter } from 'next/navigation';
import {
  Send,
  AlertCircle,
  HelpCircle,
  Clock,
  Coins,
  Bot,
  User as UserIcon,
  RefreshCw,
  StopCircle,
  CornerDownLeft,
} from 'lucide-react';

interface ModelOption {
  provider: string;
  name: string;
  label: string;
}

const MODEL_OPTIONS: ModelOption[] = [
  { provider: 'openai', name: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { provider: 'openai', name: 'gpt-4o', label: 'GPT-4o' },
  { provider: 'google', name: 'gemini-1.5-flash', label: 'Gemini Flash' },
  { provider: 'google', name: 'gemini-1.5-pro', label: 'Gemini Pro' },
  { provider: 'anthropic', name: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
  { provider: 'test', name: 'test', label: 'Test Model' },
];

export default function ChatWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const conversationId = params?.conversationId as string;
  const projectId = params?.projectId as string;
  const { accessToken, organization } = useAuthStore();

  const [input, setInput] = useState('');
  const [selectedModel, setSelectedModel] = useState<ModelOption>(MODEL_OPTIONS[0]);
  const [temperature, setTemperature] = useState<number>(0.7);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  // Fetch available models from config
  const { data: modelsData } = useQuery<{
    models: ModelOption[];
    default_model: ModelOption;
  }>({
    queryKey: ['available-models'],
    queryFn: () =>
      apiClient<{ models: ModelOption[]; default_model: ModelOption }>('/config/models'),
  });

  const availableModels = modelsData?.models || MODEL_OPTIONS;

  // Set the default model once available models are loaded
  useEffect(() => {
    if (modelsData?.default_model) {
      setSelectedModel((prev) => {
        if (prev && modelsData.models.some((m) => m.name === prev.name)) {
          return prev;
        }
        return modelsData.default_model;
      });
    }
  }, [modelsData]);

  // Fetch Project Documents for selection
  const { data: documentsData } = useQuery<{ items: any[] }>({
    queryKey: ['documents', projectId, organization?.id],
    queryFn: () => apiClient<{ items: any[] }>(`/projects/${projectId}/documents`, {
      params: { organization_id: organization?.id },
    }),
    enabled: !!projectId && !!organization?.id,
  });
  const documents = documentsData?.items || [];
  
  // Streaming UI State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState('');
  const [streamUsage, setStreamUsage] = useState<LlmUsage | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Fetch Message History
  const { data: historyData, isLoading, error } = useQuery<{ items: Message[] }>({
    queryKey: ['messages', conversationKey(conversationId)],
    queryFn: () => apiClient<{ items: Message[] }>(`/conversations/${conversationId}/messages`),
    enabled: !!conversationId,
  });

  const messages = historyData?.items || [];

  function conversationKey(id: string) {
    return id;
  }

  // Scroll to bottom helper
  const scrollToBottom = (force = false) => {
    if (!containerRef.current || !messagesEndRef.current) return;
    
    const container = containerRef.current;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 200;
    
    if (force || isAtBottom) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  useEffect(() => {
    scrollToBottom(true);
  }, [messages, streamContent]);

  // Clean up streaming on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const handleSendMessage = async (textToSend: string) => {
    const trimmedText = textToSend.trim();
    if (!trimmedText || isStreaming) return;

    setInput('');
    setIsStreaming(true);
    setStreamContent('');
    setStreamUsage(null);
    setStreamError(null);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Optimistically invalidate cache so we fetch history after streaming finishes
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/conversations/${conversationId}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          content: trimmedText,
          provider: selectedModel.provider,
          model: selectedModel.name,
          temperature: temperature,
          selected_document_ids: selectedDocIds.length > 0 ? selectedDocIds : null,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('Readable stream not supported');

      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\r\n'); // SSE starlette uses \r\n or \n\n
        
        // Save the last incomplete line back into the buffer
        buffer = lines.pop() || '';

        let currentEvent = '';

        for (const line of lines) {
          const cleanLine = line.trim();
          if (!cleanLine) continue;

          if (cleanLine.startsWith('event:')) {
            currentEvent = cleanLine.substring(6).trim();
          } else if (cleanLine.startsWith('data:')) {
            const dataStr = cleanLine.substring(5).trim();
            
            if (currentEvent === 'user_message') {
              try {
                const userMsgObj = JSON.parse(dataStr) as Message;
                queryClient.setQueryData<{ items: Message[] }>(
                  ['messages', conversationKey(conversationId)],
                  (old) => {
                    if (!old) return { items: [userMsgObj] };
                    if (old.items.some((m) => m.id === userMsgObj.id)) return old;
                    return { items: [...old.items, userMsgObj] };
                  }
                );
              } catch (e) {
                console.error('Failed to parse user message event:', e);
              }
            } else if (currentEvent === 'assistant_message') {
              try {
                const assistantMsgObj = JSON.parse(dataStr) as Message;
                queryClient.setQueryData<{ items: Message[] }>(
                  ['messages', conversationKey(conversationId)],
                  (old) => {
                    if (!old) return { items: [assistantMsgObj] };
                    if (old.items.some((m) => m.id === assistantMsgObj.id)) return old;
                    return { items: [...old.items, assistantMsgObj] };
                  }
                );
              } catch (e) {
                console.error('Failed to parse assistant message event:', e);
              }
            } else if (currentEvent === 'chunk') {
              try {
                const chunkObj = JSON.parse(dataStr);
                setStreamContent((prev) => prev + chunkObj.content);
              } catch {
                // Fail-safe: if parse fails, append raw data
                setStreamContent((prev) => prev + dataStr);
              }
            } else if (currentEvent === 'usage') {
              try {
                const usageObj = JSON.parse(dataStr);
                setStreamUsage(usageObj);
              } catch {}
            } else if (currentEvent === 'error') {
              setStreamError(dataStr);
            }
          }
        }
      }

      // Re-fetch clean list of messages now that streaming is complete
      queryClient.invalidateQueries({ queryKey: ['messages', conversationKey(conversationId)] });
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setStreamError('Generation aborted by user.');
      } else {
        setStreamError(err.message || 'Connection lost.');
      }
      queryClient.invalidateQueries({ queryKey: ['messages', conversationKey(conversationId)] });
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const handleRetryMessage = (failedMessage: Message) => {
    // Locate the user message preceding this failed message
    const failedIndex = messages.findIndex((m) => m.id === failedMessage.id);
    if (failedIndex === -1) return;

    // Find the closest preceding user message
    let userPrompt = '';
    for (let i = failedIndex - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        userPrompt = messages[i].content;
        break;
      }
    }

    if (userPrompt) {
      handleSendMessage(userPrompt);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(input);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-zinc-950">
      
      {/* Top Header Controls */}
      <header className="border-b border-zinc-900 px-6 py-3 shrink-0 flex flex-wrap items-center justify-between gap-4 bg-zinc-950/40 backdrop-blur-md sticky top-0 z-20 min-h-[65px]">
        <div>
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">AI Assistant</h2>
          <p className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">Grounded Chat Pane</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Model Selector */}
          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1 pl-1">Language Model</span>
            <select
              value={selectedModel.name}
              onChange={(e) => {
                const opt = availableModels.find((o) => o.name === e.target.value);
                if (opt) setSelectedModel(opt);
              }}
              className="bg-zinc-900 text-zinc-100 text-xs px-3 py-1.5 rounded-xl border border-zinc-800 focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer"
            >
              {availableModels.map((opt) => (
                <option key={opt.name} value={opt.name}>
                  {opt.label} ({opt.provider})
                </option>
              ))}
            </select>
          </div>

          {/* Temperature Input */}
          <div className="flex flex-col w-20">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-1 pl-1">Temp</span>
            <input
              type="number"
              min={0}
              max={2}
              step={0.1}
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value) || 0.7)}
              className="bg-zinc-900 text-zinc-100 text-xs px-3 py-1.5 rounded-xl border border-zinc-800 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-center"
            />
          </div>
        </div>
      </header>

      {/* Message Timeline */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto px-6 py-6 space-y-6 min-h-0"
      >
        {isLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="flex flex-col items-center gap-3">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent"></div>
              <span className="text-xs text-zinc-500">Loading conversation history...</span>
            </div>
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center">
            <div className="max-w-xs text-center p-6 rounded-xl bg-zinc-900 border border-zinc-850">
              <AlertCircle className="h-6 w-6 text-red-400 mx-auto mb-2" />
              <p className="text-red-400 text-xs font-semibold">Failed to fetch messages</p>
            </div>
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="h-12 w-12 rounded-2xl bg-zinc-900 border border-zinc-850 flex items-center justify-center mb-4 text-zinc-650">
              <Bot className="h-6 w-6 text-indigo-400" />
            </div>
            <h3 className="text-sm font-semibold text-zinc-350">New Workspace Conversation</h3>
            <p className="text-zinc-500 text-xs mt-1 max-w-xs leading-relaxed">
              Type a prompt in the message box below. The system will retrieve documents uploaded to this project to contextualize its response.
            </p>
          </div>
        ) : (
          <div className="space-y-6 max-w-4xl mx-auto">
            {messages
              .filter((msg) => msg.status !== 'STREAMING')
              .map((msg) => {
              const isUser = msg.role === 'user';
              
              return (
                <div
                  key={msg.id}
                  className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  {/* Left Bot Icon */}
                  {!isUser && (
                    <div className="h-8 w-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-indigo-400 shrink-0 shadow-md">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}

                  <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
                    <div
                      className={`p-4 rounded-2xl text-sm leading-relaxed ${
                        isUser
                          ? 'bg-zinc-900 border border-zinc-800 text-zinc-100 rounded-tr-none'
                          : 'bg-zinc-900/40 border border-zinc-900 text-zinc-200 rounded-tl-none'
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.content}</p>

                      {/* Display warning/retry for failed message */}
                      {!isUser && msg.status === 'FAILED' && (
                        <div className="mt-3 flex items-center gap-2 text-xs text-red-400 p-2 rounded-lg bg-red-950/20 border border-red-950/50">
                          <AlertCircle className="h-4 w-4 shrink-0" />
                          <span>Generation failed.</span>
                          <button
                            onClick={() => handleRetryMessage(msg)}
                            className="flex items-center gap-1 ml-auto text-[10px] font-bold text-red-300 hover:text-red-200 uppercase tracking-wider transition-colors cursor-pointer"
                          >
                            <RefreshCw className="h-3 w-3" />
                            <span>Retry</span>
                          </button>
                        </div>
                      )}

                      {/* Display warning for interrupted message */}
                      {!isUser && msg.status === 'INTERRUPTED' && (
                        <div className="mt-3 flex items-center gap-2 text-xs text-zinc-400 p-2 rounded-lg bg-zinc-950 border border-zinc-850">
                          <AlertCircle className="h-4 w-4 text-zinc-500 shrink-0" />
                          <span>Generation interrupted by user.</span>
                        </div>
                      )}
                    </div>

                    {/* Meta info / Status labels */}
                    <div className="mt-1.5 flex items-center gap-2.5 text-[10px] text-zinc-500 pl-1">
                      {isUser ? (
                        <span>User</span>
                      ) : (
                        <>
                          <span className="font-semibold text-zinc-500 uppercase tracking-wider">{msg.status}</span>
                          {msg.metadata?.usage && (
                            <div className="flex items-center gap-2 text-[9px] text-zinc-650 font-medium">
                              <span className="flex items-center gap-0.5">
                                <Clock className="h-3 w-3" />
                                {msg.metadata.usage.latency_ms}ms
                              </span>
                              <span className="flex items-center gap-0.5">
                                <Coins className="h-3 w-3" />
                                ${(msg.metadata.usage.cost * 1000).toFixed(4)}k
                              </span>
                            </div>
                          )}
                        </>
                      )}
                      <span>•</span>
                      <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>

                  {/* Right User Icon */}
                  {isUser && (
                    <div className="h-8 w-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 shrink-0 shadow-md">
                      <UserIcon className="h-4 w-4" />
                    </div>
                  )}
                </div>
              );
            })}

            {/* Streaming Message Indicator */}
            {isStreaming && (
              <div className="flex gap-4 justify-start">
                <div className="h-8 w-8 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-indigo-400 shrink-0 shadow-md">
                  <Bot className="h-4 w-4" />
                </div>

                <div className="flex flex-col max-w-[80%] items-start">
                  <div className="p-4 rounded-2xl text-sm leading-relaxed bg-zinc-900/40 border border-zinc-900 text-zinc-200 rounded-tl-none">
                    {streamContent ? (
                      <p className="whitespace-pre-wrap">{streamContent}</p>
                    ) : (
                      <div className="flex gap-1 py-1">
                        <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce"></span>
                        <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                        <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                      </div>
                    )}

                    {streamError && (
                      <div className="mt-3 flex items-center gap-2 text-xs text-red-400 p-2 rounded-lg bg-red-950/20 border border-red-950/50">
                        <AlertCircle className="h-4 w-4 shrink-0" />
                        <span>{streamError}</span>
                      </div>
                    )}
                  </div>
                  
                  <div className="mt-1.5 flex items-center gap-2.5 text-[10px] text-zinc-550 pl-1">
                    <span className="font-extrabold text-indigo-400 uppercase tracking-widest animate-pulse">STREAMING</span>
                    {streamUsage && (
                      <div className="flex items-center gap-2 text-[9px] font-medium">
                        <span className="flex items-center gap-0.5">
                          <Clock className="h-3 w-3" />
                          {streamUsage.latency_ms}ms
                        </span>
                        <span className="flex items-center gap-0.5">
                          <Coins className="h-3 w-3" />
                          ${(streamUsage.cost * 1000).toFixed(4)}k
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Composer Input Area */}
      <footer className="p-4 border-t border-zinc-900 bg-zinc-950/50 backdrop-blur-md shrink-0">
        {/* Document Selection Row */}
        {documents.length > 0 && (
          <div className="max-w-4xl mx-auto mb-3 flex flex-col gap-1.5">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest pl-1">
              Source Scope: {selectedDocIds.length === 0 ? "Project-wide (All Documents)" : `${selectedDocIds.length} Selected`}
            </span>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto py-1">
              {documents.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <button
                    key={doc.id}
                    onClick={() => {
                      setSelectedDocIds((prev) =>
                        isSelected ? prev.filter((id) => id !== doc.id) : [...prev, doc.id]
                      );
                    }}
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer select-none ${
                      isSelected
                        ? 'bg-indigo-600/20 border-indigo-500 text-indigo-200 shadow-[0_0_10px_rgba(99,102,241,0.15)]'
                        : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:text-zinc-300'
                    }`}
                  >
                    {doc.name}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="max-w-4xl mx-auto relative flex items-end bg-zinc-900 border border-zinc-800 rounded-2xl focus-within:ring-1 focus-within:ring-indigo-500/50 focus-within:border-indigo-500 transition-all p-2 gap-2">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a prompt..."
            className="flex-1 max-h-48 py-2 px-3 bg-transparent text-zinc-100 placeholder-zinc-500 border-0 focus:outline-none focus:ring-0 text-sm resize-none"
            disabled={isLoading}
          />
          <div className="flex items-center gap-2 shrink-0">
            {isStreaming ? (
              <button
                onClick={handleStopGeneration}
                className="flex items-center justify-center h-8 w-8 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 transition-all cursor-pointer"
                title="Cancel stream"
              >
                <StopCircle className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={() => handleSendMessage(input)}
                disabled={!input.trim() || isLoading}
                className="flex items-center justify-center h-8 w-8 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-all cursor-pointer disabled:opacity-50 disabled:pointer-events-none active:scale-95"
              >
                <Send className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
        <div className="max-w-4xl mx-auto flex items-center justify-between text-[9px] text-zinc-650 font-bold uppercase tracking-wider mt-2 px-1">
          <span>Shift+Enter for new line</span>
          <span>Knowledge-grounded response</span>
        </div>
      </footer>
    </div>
  );
}
