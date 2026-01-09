import { Box, Typography, CircularProgress, Paper, Tooltip } from '@mui/material';
import { AssetHealth } from '../store/assetsSlice';

interface HealthPanelProps {
    health: AssetHealth;
    assetName: string;
}

function getHealthColor(index: number): string {
    if (index >= 90) return '#4CAF50';
    if (index >= 80) return '#FF9800';
    return '#f44336';
}

export function HealthPanel({ health, assetName }: HealthPanelProps) {
    const healthColor = getHealthColor(health.healthIndex);

    return (
        <Paper
            sx={{
                p: 3,
                borderRadius: 4,
                background: `linear-gradient(135deg, ${healthColor}10 0%, ${healthColor}05 100%)`,
                border: `1px solid ${healthColor}30`,
                position: 'relative',
                overflow: 'hidden',
            }}
        >
            {/* Animated background glow */}
            <Box
                sx={{
                    position: 'absolute',
                    top: -50,
                    right: -50,
                    width: 150,
                    height: 150,
                    borderRadius: '50%',
                    background: `radial-gradient(circle, ${healthColor}30 0%, transparent 70%)`,
                    animation: 'pulse 3s ease-in-out infinite',
                    '@keyframes pulse': {
                        '0%, 100%': { opacity: 0.5, transform: 'scale(1)' },
                        '50%': { opacity: 1, transform: 'scale(1.1)' },
                    },
                }}
            />

            <Typography variant="h6" gutterBottom fontWeight={600}>
                {assetName}
            </Typography>

            <Box display="flex" alignItems="center" gap={4}>
                {/* Main Health Gauge */}
                <Box position="relative" display="inline-flex">
                    <CircularProgress
                        variant="determinate"
                        value={health.healthIndex}
                        size={120}
                        thickness={6}
                        sx={{
                            color: healthColor,
                            '& .MuiCircularProgress-circle': {
                                strokeLinecap: 'round',
                            },
                        }}
                    />
                    <CircularProgress
                        variant="determinate"
                        value={100}
                        size={120}
                        thickness={6}
                        sx={{
                            color: 'rgba(255,255,255,0.08)',
                            position: 'absolute',
                            left: 0,
                        }}
                    />
                    <Box
                        sx={{
                            top: 0,
                            left: 0,
                            bottom: 0,
                            right: 0,
                            position: 'absolute',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexDirection: 'column',
                        }}
                    >
                        <Typography variant="h3" fontWeight={700} color={healthColor}>
                            {health.healthIndex}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Health Index
                        </Typography>
                    </Box>
                </Box>

                {/* Metrics Grid */}
                <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2} flex={1}>
                    <Tooltip title="Model confidence in the health assessment">
                        <Box>
                            <Typography variant="caption" color="text.secondary">
                                Confidence
                            </Typography>
                            <Typography variant="h6" fontWeight={600}>
                                {(health.healthConfidence * 100).toFixed(0)}%
                            </Typography>
                        </Box>
                    </Tooltip>

                    <Tooltip title="ML-detected deviation from normal patterns">
                        <Box>
                            <Typography variant="caption" color="text.secondary">
                                Anomaly Score
                            </Typography>
                            <Typography
                                variant="h6"
                                fontWeight={600}
                                color={health.anomalyScore > 0.5 ? 'error.main' : 'text.primary'}
                            >
                                {(health.anomalyScore * 100).toFixed(0)}%
                            </Typography>
                        </Box>
                    </Tooltip>

                    <Tooltip title="Deviation between measured and physics-predicted values">
                        <Box>
                            <Typography variant="caption" color="text.secondary">
                                Physics Residual
                            </Typography>
                            <Typography
                                variant="h6"
                                fontWeight={600}
                                color={health.physicsResidual > 0.5 ? 'warning.main' : 'text.primary'}
                            >
                                {(health.physicsResidual * 100).toFixed(0)}%
                            </Typography>
                        </Box>
                    </Tooltip>

                    <Box>
                        <Typography variant="caption" color="text.secondary">
                            Last Update
                        </Typography>
                        <Typography variant="body2" fontWeight={500}>
                            {new Date(health.lastUpdate).toLocaleTimeString()}
                        </Typography>
                    </Box>
                </Box>
            </Box>
        </Paper>
    );
}
