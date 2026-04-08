import { useState, useRef, KeyboardEvent } from 'react';
import { 
  Box, 
  TextField, 
  IconButton, 
  InputAdornment,
  Tooltip,
  Fab
} from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import SendIcon from '@mui/icons-material/Send';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  onToggleRecording: () => void;
  onClear: () => void;
  isListening: boolean;
  disabled: boolean;
}

export function ChatInput({ 
  onSendMessage, 
  onToggleRecording, 
  onClear, 
  isListening, 
  disabled 
}: ChatInputProps) {
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSendMessage(text.trim());
      setText('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box
      sx={{
        p: 2,
        backgroundColor: 'rgba(0,0,0,0.3)',
        backdropFilter: 'blur(10px)',
        borderTop: '1px solid rgba(255,255,255,0.1)'
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          maxWidth: 800,
          mx: 'auto'
        }}
      >
        <Tooltip title="Clear chat">
          <IconButton
            onClick={onClear}
            sx={{ 
              color: 'rgba(255,255,255,0.6)',
              '&:hover': { color: '#f87171' }
            }}
          >
            <DeleteOutlineIcon />
          </IconButton>
        </Tooltip>

        <TextField
          inputRef={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="தமிழில் எழுதுக... (Type in Tamil or Tanglish)"
          disabled={disabled}
          fullWidth
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              borderRadius: 4,
              backgroundColor: 'rgba(255,255,255,0.05)',
              '& fieldset': {
                borderColor: 'rgba(255,255,255,0.1)'
              },
              '&:hover fieldset': {
                borderColor: 'rgba(255,255,255,0.2)'
              },
              '&.Mui-focused fieldset': {
                borderColor: '#a78bfa'
              }
            },
            '& .MuiInputBase-input': {
              color: 'white',
              '&::placeholder': {
                color: 'rgba(255,255,255,0.4)',
                opacity: 1
              }
            }
          }}
          InputProps={{
            endAdornment: text.trim() && (
              <InputAdornment position="end">
                <IconButton
                  onClick={handleSend}
                  disabled={disabled}
                  sx={{ 
                    color: '#a78bfa',
                    '&:hover': { color: '#c4b5fd' }
                  }}
                >
                  <SendIcon />
                </IconButton>
              </InputAdornment>
            )
          }}
        />

        <Tooltip title={isListening ? 'Stop recording' : 'Start voice chat'}>
          <Fab
            onClick={onToggleRecording}
            disabled={disabled}
            sx={{
              backgroundColor: isListening ? '#ef4444' : '#a78bfa',
              color: 'white',
              '&:hover': {
                backgroundColor: isListening ? '#dc2626' : '#8b5cf6'
              },
              transition: 'all 0.3s ease',
              transform: isListening ? 'scale(1.1)' : 'scale(1)'
            }}
          >
            <MicIcon />
          </Fab>
        </Tooltip>
      </Box>
    </Box>
  );
}
