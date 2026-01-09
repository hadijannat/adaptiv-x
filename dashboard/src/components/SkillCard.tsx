import { Box, Typography, Chip, LinearProgress, Tooltip } from '@mui/material';
import {
    CheckCircle,
    Warning,
    Error as ErrorIcon,
    Speed,
    Straighten,
    BatteryChargingFull
} from '@mui/icons-material';
import { AssetCapability } from '../store/assetsSlice';

interface SkillCardProps {
    capability: AssetCapability;
}

const assuranceColors = {
    assured: '#4CAF50',
    offered: '#FF9800',
    notAvailable: '#f44336',
};

const assuranceIcons = {
    assured: CheckCircle,
    offered: Warning,
    notAvailable: ErrorIcon,
};

export function SkillCard({ capability }: SkillCardProps) {
    const AssuranceIcon = assuranceIcons[capability.assuranceState];
    const assuranceColor = assuranceColors[capability.assuranceState];

    return (
        <Box
            sx={{
                p: 2,
                borderRadius: 2,
                bgcolor: 'background.paper',
                border: `1px solid ${assuranceColor}40`,
                boxShadow: `0 0 20px ${assuranceColor}20`,
                transition: 'all 0.3s ease',
                '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: `0 8px 30px ${assuranceColor}30`,
                },
            }}
        >
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                <Typography variant="subtitle1" fontWeight={600} color="text.primary">
                    Milling Capability
                </Typography>
                <Tooltip title={`Assurance: ${capability.assuranceState}`}>
                    <Chip
                        icon={<AssuranceIcon sx={{ fontSize: 18, color: assuranceColor }} />}
                        label={capability.assuranceState.toUpperCase()}
                        size="small"
                        sx={{
                            bgcolor: `${assuranceColor}20`,
                            color: assuranceColor,
                            fontWeight: 600,
                            borderRadius: 2,
                        }}
                    />
                </Tooltip>
            </Box>

            <Box display="flex" flexDirection="column" gap={1.5}>
                <Box display="flex" alignItems="center" gap={1}>
                    <Speed sx={{ fontSize: 20, color: 'primary.main' }} />
                    <Typography variant="body2" color="text.secondary">
                        Surface Finish:
                    </Typography>
                    <Chip
                        label={`Grade ${capability.surfaceFinishGrade}`}
                        size="small"
                        color={capability.surfaceFinishGrade === 'A' ? 'success' :
                            capability.surfaceFinishGrade === 'B' ? 'warning' : 'error'}
                        sx={{ fontWeight: 600 }}
                    />
                </Box>

                <Box display="flex" alignItems="center" gap={1}>
                    <Straighten sx={{ fontSize: 20, color: 'primary.main' }} />
                    <Typography variant="body2" color="text.secondary">
                        Tolerance:
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                        {capability.toleranceClass}
                    </Typography>
                </Box>

                <Box display="flex" alignItems="center" gap={1}>
                    <BatteryChargingFull sx={{ fontSize: 20, color: 'primary.main' }} />
                    <Typography variant="body2" color="text.secondary">
                        Energy Cost:
                    </Typography>
                    <Typography variant="body2" fontWeight={500}>
                        {capability.energyCostPerPart} kWh/part
                    </Typography>
                </Box>
            </Box>

            {/* Assurance State Progress */}
            <Box mt={2}>
                <LinearProgress
                    variant="determinate"
                    value={capability.assuranceState === 'assured' ? 100 :
                        capability.assuranceState === 'offered' ? 50 : 10}
                    sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: 'rgba(255,255,255,0.1)',
                        '& .MuiLinearProgress-bar': {
                            bgcolor: assuranceColor,
                            borderRadius: 3,
                        },
                    }}
                />
            </Box>
        </Box>
    );
}
