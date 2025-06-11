import React, { useState, KeyboardEvent } from 'react';
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

  const handleKeyPress = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <Box>
      <SpaceBetween direction="vertical" size="s">
        <Textarea
          value={inputValue}
          onChange={({ detail }) => setInputValue(detail.value)}
          onKeyDown={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled}
          rows={3}
          resize="vertical"
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
