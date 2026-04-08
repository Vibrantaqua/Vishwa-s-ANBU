import { useState, useCallback, useRef, useEffect } from 'react';
import { ConversationState, ConversationResponse, ChatMessage, Emotion } from '../types';

const API_BASE = 'http://localhost:8000';

export function useConversation() {
  const [state, setState] = useState<ConversationState>('idle');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const [vramUsage, setVramUsage] = useState<number>(0);
  const [isConnected, setIsConnected] = useState(false);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const storedSessionId = sessionStorage.getItem('tamil_ai_session');
    if (storedSessionId) {
      setSessionId(storedSessionId);
    } else {
      const newSessionId = crypto.randomUUID();
      setSessionId(newSessionId);
      sessionStorage.setItem('tamil_ai_session', newSessionId);
    }

    const statusInterval = setInterval(fetchStatus, 5000);
    return () => clearInterval(statusInterval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/status`);
      const data = await res.json();
      setVramUsage(data.vram_usage_gb);
      setIsConnected(data.status === 'ready');
    } catch {
      setIsConnected(false);
    }
  };

  const startListening = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        } 
      });

      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);

      mediaRecorderRef.current = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.start(100);
      setState('listening');
    } catch (error) {
      console.error('Failed to start recording:', error);
      setState('idle');
    }
  }, []);

  const stopListening = useCallback(async () => {
    return new Promise<{ transcription: string | null; response: string; emotion: string } | null>((resolve) => {
      if (!mediaRecorderRef.current) {
        resolve(null);
        return;
      }

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        if (audioContextRef.current) {
          await audioContextRef.current.close();
          audioContextRef.current = null;
        }

        const arrayBuffer = await audioBlob.arrayBuffer();
        
        try {
          const base64Audio = btoa(
            new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
          );

          setState('thinking');

          const response = await fetch(`${API_BASE}/conversation/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              audio_data: base64Audio,
              session_id: sessionId
            })
          });

          const data: ConversationResponse = await response.json();
          
          resolve({
            transcription: data.transcription || null,
            response: data.response,
            emotion: data.emotion
          });
        } catch (error) {
          console.error('Audio conversation failed:', error);
          resolve(null);
        }
      };

      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    });
  }, [sessionId]);

  const sendTextMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      content: text,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setState('thinking');

    try {
      const response = await fetch(`${API_BASE}/conversation/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          session_id: sessionId
        })
      });

      const data: ConversationResponse = await response.json();

      const botMessage: ChatMessage = {
        id: crypto.randomUUID(),
        type: 'bot',
        content: data.response,
        emotion: data.emotion as Emotion,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);

      if (data.audio_base64) {
        setState('speaking');
        playAudio(data.audio_base64);
      } else {
        setState('idle');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      setState('idle');
    }
  }, [sessionId]);

  const playAudio = useCallback((base64Audio: string) => {
    try {
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], { type: 'audio/wav' });
      const url = URL.createObjectURL(blob);
      
      if (audioRef.current) {
        audioRef.current.pause();
      }
      audioRef.current = new Audio(url);
      audioRef.current.onended = () => {
        setState('idle');
        URL.revokeObjectURL(url);
      };
      audioRef.current.play();
    } catch (error) {
      console.error('Failed to play audio:', error);
      setState('idle');
    }
  }, []);

  const handleConversationTurn = useCallback(async () => {
    if (state !== 'listening') {
      await startListening();
    } else {
      const result = await stopListening();
      
      if (result) {
        setState('speaking');
        
        // Show transcription as user message
        if (result.transcription) {
          const userMessage: ChatMessage = {
            id: crypto.randomUUID(),
            type: 'user',
            content: result.transcription,
            timestamp: new Date()
          };
          setMessages(prev => [...prev, userMessage]);
        }
        
        const botMessage: ChatMessage = {
          id: crypto.randomUUID(),
          type: 'bot',
          content: result.response,
          emotion: result.emotion as Emotion,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, botMessage]);
        
        setTimeout(() => setState('idle'), 2000);
      } else {
        setState('idle');
      }
    }
  }, [state, startListening, stopListening]);

  const clearConversation = useCallback(async () => {
    setMessages([]);
    try {
      await fetch(`${API_BASE}/conversation/history/${sessionId}`, {
        method: 'DELETE'
      });
    } catch (error) {
      console.error('Failed to clear conversation:', error);
    }
  }, [sessionId]);

  const getAudioLevel = useCallback((): number => {
    if (!analyserRef.current || state !== 'listening') return 0;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    return average / 255;
  }, [state]);

  return {
    state,
    messages,
    sessionId,
    vramUsage,
    isConnected,
    sendTextMessage,
    handleConversationTurn,
    clearConversation,
    getAudioLevel,
    startListening,
    stopListening
  };
}
