import React, { useState } from 'react';
import {
  Box,
  Button,
  Textarea,
  SpaceBetween,
} from '@cloudscape-design/components';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  disabled = false, 
  placeholder = "Enter your question here" 
}) => {
  const [inputValue, setInputValue] = useState<string>('');

  const handleSend = () => {
    const trimmedMessage = inputValue.trim();
    if (trimmedMessage && !disabled) {
      onSendMessage(trimmedMessage);
      setInputValue('');
    }
  };

  const handleKeyDown = (event: any) => {
    // Try different ways to access the key
    const key = event.key || event.detail?.key || event.detail?.originalEvent?.key;
    const shiftKey = event.shiftKey || event.detail?.shiftKey || event.detail?.originalEvent?.shiftKey;
    
    if (key === 'Enter' && !shiftKey) {
      event.preventDefault?.();
      event.detail?.originalEvent?.preventDefault?.();
      handleSend();
    }
    // Shift+Enter will allow newline (default behavior)
  };

  // Calculate rows based on content length (simple heuristic)
  const calculateRows = (text: string) => {
    if (!text) return 1;
    const lines = text.split('\n').length;
    const estimatedLines = Math.ceil(text.length / 80); // Rough estimate based on character count
    return Math.min(Math.max(lines, estimatedLines, 1), 4); // Min 1, max 4 rows
  };

  return (
    <Box>
      <SpaceBetween direction="vertical" size="s">
        <Textarea
          value={inputValue}
          onChange={({ detail }) => setInputValue(detail.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={calculateRows(inputValue)}
        />
        <Box float="right">
          <Button
            variant="primary"
            onClick={handleSend}
            disabled={disabled || !inputValue.trim()}
          >
            Send
          </Button>
        </Box>
      </SpaceBetween>
    </Box>
  );
};

export default ChatInput;
