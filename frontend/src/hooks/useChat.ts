import { useContext } from 'react';
import { ChatContext, type ChatState } from '../context/chatContext';

export function useChat(): ChatState {
  const chat = useContext(ChatContext);
  if (!chat) throw new Error('useChat must be used inside <ChatProvider>');
  return chat;
}
