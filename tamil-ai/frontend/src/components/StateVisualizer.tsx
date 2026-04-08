import { Box, CircularProgress, keyframes } from '@mui/material';
import { ConversationState } from '../types';

interface StateVisualizerProps {
  state: ConversationState;
  audioLevel?: number;
}

const pulse = keyframes`
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
`;

const breathe = keyframes`
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
`;

const wave = keyframes`
  0%, 100% { transform: scaleY(0.4); }
  50% { transform: scaleY(1); }
`;

export function StateVisualizer({ state, audioLevel = 0 }: StateVisualizerProps) {
  const getStateConfig = () => {
    switch (state) {
      case 'listening':
        return {
          color: '#4ade80',
          label: 'கவனிக்கிறேன்...',
          sublabel: 'Listening...',
          animation: breathe
        };
      case 'thinking':
        return {
          color: '#facc15',
          label: 'நினைக்கிறேன்...',
          sublabel: 'Thinking...',
          animation: pulse
        };
      case 'speaking':
        return {
          color: '#60a5fa',
          label: 'பேசுகிறேன்...',
          sublabel: 'Speaking...',
          animation: pulse
        };
      default:
        return {
          color: '#a78bfa',
          label: 'தயார்',
          sublabel: 'Ready',
          animation: 'none'
        };
    }
  };

  const config = getStateConfig();

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 2
      }}
    >
      <Box
        sx={{
          position: 'relative',
          width: 200,
          height: 200,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            background: `radial-gradient(circle, ${config.color}22 0%, transparent 70%)`,
            animation: state !== 'idle' ? `${config.animation} 2s ease-in-out infinite` : 'none'
          }}
        />

        {state === 'listening' && (
          <>
            {[...Array(5)].map((_, i) => (
              <Box
                key={i}
                sx={{
                  position: 'absolute',
                  width: 8,
                  height: state === 'listening' ? 40 + audioLevel * 60 : 40,
                  backgroundColor: config.color,
                  borderRadius: 4,
                  animation: `${wave} 0.5s ease-in-out infinite`,
                  animationDelay: `${i * 0.1}s`,
                  opacity: 0.6 + i * 0.1,
                  transformOrigin: 'center bottom'
                }}
              />
            ))}
          </>
        )}

        {state === 'thinking' && (
          <CircularProgress
            size={80}
            sx={{ color: config.color }}
            thickness={2}
          />
        )}

        {state === 'speaking' && (
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              backgroundColor: config.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              animation: `${breathe} 0.5s ease-in-out infinite`
            }}
          >
            <Box
              component="span"
              sx={{
                fontSize: 40,
                color: 'white'
              }}
            >
              🤖
            </Box>
          </Box>
        )}

        {state === 'idle' && (
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              backgroundColor: 'rgba(167, 139, 250, 0.2)',
              border: '3px solid',
              borderColor: config.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Box
              component="span"
              sx={{ fontSize: 36 }}
            >
              🤖
            </Box>
          </Box>
        )}
      </Box>

      <Box sx={{ textAlign: 'center' }}>
        <Box
          sx={{
            fontSize: 24,
            fontWeight: 700,
            color: config.color,
            mb: 0.5
          }}
        >
          {config.label}
        </Box>
        <Box
          sx={{
            fontSize: 14,
            color: 'rgba(255,255,255,0.6)'
          }}
        >
          {config.sublabel}
        </Box>
      </Box>
    </Box>
  );
}
