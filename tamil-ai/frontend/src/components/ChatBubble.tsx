import { Box, Typography, alpha } from '@mui/material';
import { ChatMessage, Emotion } from '../types';

interface ChatBubbleProps {
  message: ChatMessage;
}

const emotionColors: Record<Emotion, string> = {
  happy: '#4ade80',
  sad: '#60a5fa',
  excited: '#fb923c',
  calm: '#a78bfa',
  confused: '#facc15',
  empathetic: '#f472b6',
  neutral: '#94a3b8'
};

const emotionEmojis: Record<Emotion, string> = {
  happy: '😊',
  sad: '😢',
  excited: '🎉',
  calm: '😌',
  confused: '🤔',
  empathetic: '❤️',
  neutral: '🤖'
};

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.type === 'user';
  const emotionColor = message.emotion ? emotionColors[message.emotion] : '#94a3b8';
  const emoji = message.emotion ? emotionEmojis[message.emotion] : '🤖';

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: isUser ? 'flex-end' : 'flex-start',
        mb: 2,
        px: 2
      }}
    >
      <Box
        sx={{
          maxWidth: '70%',
          display: 'flex',
          flexDirection: isUser ? 'row-reverse' : 'row',
          alignItems: 'flex-end',
          gap: 1
        }}
      >
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            backgroundColor: isUser ? '#6366f1' : alpha(emotionColor, 0.2),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18
          }}
        >
          {isUser ? '👤' : emoji}
        </Box>

        <Box
          sx={{
            backgroundColor: isUser 
              ? 'rgba(99, 102, 241, 0.9)' 
              : alpha(emotionColor, 0.15),
            borderRadius: 3,
            borderTopRightRadius: isUser ? 8 : 24,
            borderTopLeftRadius: isUser ? 24 : 8,
            px: 2.5,
            py: 1.5,
            backdropFilter: 'blur(10px)'
          }}
        >
          <Typography
            sx={{
              fontSize: 16,
              lineHeight: 1.5,
              color: isUser ? 'white' : '#e4e4e7'
            }}
          >
            {message.content}
          </Typography>
          
          {!isUser && message.emotion && (
            <Box
              sx={{
                mt: 0.5,
                display: 'flex',
                alignItems: 'center',
                gap: 0.5
              }}
            >
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  backgroundColor: emotionColor
                }}
              />
              <Typography
                sx={{
                  fontSize: 11,
                  color: alpha(emotionColor, 0.8),
                  textTransform: 'capitalize'
                }}
              >
                {message.emotion}
              </Typography>
            </Box>
          )}

          <Typography
            sx={{
              fontSize: 10,
              color: 'rgba(255,255,255,0.5)',
              mt: 0.5,
              textAlign: 'right'
            }}
          >
            {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
