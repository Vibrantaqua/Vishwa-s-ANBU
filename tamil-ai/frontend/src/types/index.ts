export type ConversationState = 'idle' | 'listening' | 'thinking' | 'speaking';

export type Emotion = 'happy' | 'sad' | 'excited' | 'calm' | 'confused' | 'empathetic' | 'neutral';

export interface ConversationTurn {
  id: string;
  userInput: string;
  botResponse: string;
  emotion: Emotion;
  fillerIntensity: number;
  timestamp: Date;
}

export interface ConversationResponse {
  response: string;
  emotion: Emotion;
  filler_intensity: number;
  audio_base64: string | null;
  session_id: string;
  new_summary: string | null;
  transcription?: string;
}

export interface SystemStatus {
  status: string;
  vram_usage_gb: number;
  models_loaded: boolean;
  session_id?: string;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'bot';
  content: string;
  emotion?: Emotion;
  timestamp: Date;
}
