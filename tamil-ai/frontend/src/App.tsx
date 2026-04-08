import { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import { StateVisualizer, ChatBubble, ChatInput, StatusBar } from './components';
import { useConversation } from './hooks/useConversation';

function App() {
  const {
    state,
    messages,
    sessionId,
    vramUsage,
    isConnected,
    sendTextMessage,
    handleConversationTurn,
    clearConversation,
    getAudioLevel
  } = useConversation();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioLevelRef = useRef(0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (state === 'listening') {
      const interval = setInterval(() => {
        audioLevelRef.current = getAudioLevel();
      }, 50);
      return () => clearInterval(interval);
    }
  }, [state, getAudioLevel]);

  const isDisabled = state === 'thinking' || state === 'speaking';

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden'
      }}
    >
      <StatusBar
        vramUsage={vramUsage}
        isConnected={isConnected}
        sessionId={sessionId}
      />

      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        <Box
          sx={{
            flex: state !== 'idle' ? 0 : 'none',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            py: 3,
            transition: 'all 0.3s ease',
            minHeight: state !== 'idle' ? 280 : 'auto'
          }}
        >
          <StateVisualizer 
            state={state} 
            audioLevel={audioLevelRef.current}
          />
        </Box>

        <Box
          sx={{
            flex: 1,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          {messages.length === 0 && state === 'idle' && (
            <Box
              sx={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 2,
                opacity: 0.6
              }}
            >
              <Box component="span" sx={{ fontSize: 48 }}>🤖</Box>
              <Typography
                sx={{
                  fontSize: 18,
                  color: 'rgba(255,255,255,0.8)',
                  textAlign: 'center'
                }}
              >
                வணக்கம்! நான் அன்பு
              </Typography>
              <Typography
                sx={{
                  fontSize: 14,
                  color: 'rgba(255,255,255,0.5)',
                  textAlign: 'center'
                }}
              >
                Hello! I'm Anbu. How can I help you today?
              </Typography>
              <Typography
                sx={{
                  fontSize: 12,
                  color: 'rgba(255,255,255,0.3)',
                  textAlign: 'center',
                  mt: 1
                }}
              >
                Type a message or tap the mic button to start a voice conversation
              </Typography>
            </Box>
          )}

          {messages.map((message) => (
            <ChatBubble key={message.id} message={message} />
          ))}
          
          <div ref={messagesEndRef} />
        </Box>

        <ChatInput
          onSendMessage={sendTextMessage}
          onToggleRecording={handleConversationTurn}
          onClear={clearConversation}
          isListening={state === 'listening'}
          disabled={isDisabled}
        />
      </Box>
    </Box>
  );
}

export default App;
