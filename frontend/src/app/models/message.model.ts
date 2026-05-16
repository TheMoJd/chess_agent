import { ToolCallTrace } from './chat.model';

export interface Message {
  id: string; // crypto.randomUUID() local — utilisé comme @for track key
  role: 'user' | 'assistant' | 'system';
  text: string;
  toolCalls?: ToolCallTrace[]; // seulement sur les messages assistant
  timestamp: number;
  isError?: boolean;
}
