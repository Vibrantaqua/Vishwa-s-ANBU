import { Box, Typography, LinearProgress, Chip } from '@mui/material';
import { alpha } from '@mui/material/styles';

interface StatusBarProps {
  vramUsage: number;
  isConnected: boolean;
  sessionId: string;
}

export function StatusBar({ vramUsage, isConnected, sessionId }: StatusBarProps) {
  const vramPercentage = (vramUsage / 4) * 100;

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3,
        py: 1.5,
        backgroundColor: 'rgba(0,0,0,0.4)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(255,255,255,0.1)'
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Box
          component="span"
          sx={{
            fontSize: 24,
            fontWeight: 700,
            background: 'linear-gradient(135deg, #a78bfa 0%, #60a5fa 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}
        >
          அன்பு
        </Box>
        
        <Chip
          label={isConnected ? 'Connected' : 'Connecting...'}
          size="small"
          sx={{
            backgroundColor: isConnected 
              ? alpha('#4ade80', 0.2) 
              : alpha('#facc15', 0.2),
            color: isConnected ? '#4ade80' : '#facc15',
            fontWeight: 500,
            fontSize: 11
          }}
        />
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography sx={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>
            VRAM:
          </Typography>
          <Box sx={{ width: 100 }}>
            <LinearProgress
              variant="determinate"
              value={vramPercentage}
              sx={{
                height: 6,
                borderRadius: 3,
                backgroundColor: 'rgba(255,255,255,0.1)',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 3,
                  backgroundColor: vramUsage > 3.5 
                    ? '#ef4444' 
                    : vramUsage > 3.0 
                      ? '#facc15' 
                      : '#4ade80'
                }
              }}
            />
          </Box>
          <Typography sx={{ fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
            {vramUsage.toFixed(1)}GB
          </Typography>
        </Box>

        <Typography 
          sx={{ 
            fontSize: 10, 
            color: 'rgba(255,255,255,0.3)',
            fontFamily: 'monospace'
          }}
        >
          {sessionId.slice(0, 8)}...
        </Typography>
      </Box>
    </Box>
  );
}
