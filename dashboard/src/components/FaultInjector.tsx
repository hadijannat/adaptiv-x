import { useState } from 'react';
import {
    Box,
    Button,
    Paper,
    Typography,
    Slider,
    CircularProgress,
    Alert,
} from '@mui/material';
import { BugReport } from '@mui/icons-material';
import { useDispatch } from 'react-redux';
import { updateHealth, updateCapability } from '../store/assetsSlice';
import { fetchAssetState } from '../api/aas';

interface FaultInjectorProps {
    assetId: string;
}

export function FaultInjector({ assetId }: FaultInjectorProps) {
    const dispatch = useDispatch();
    const [vibration, setVibration] = useState(1.0);
    const [wear, setWear] = useState(0.0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleInjectFault = async () => {
        setLoading(true);

        try {
            setError(null);
            const response = await fetch('/api/fault-injector/inject', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    asset_id: assetId,
                    vib_rms: vibration,
                    omega: 150.0,
                    load: 800.0,
                    wear: wear,
                    evaluate_policy: true,
                }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `Injection failed (${response.status})`);
            }

            const result = await response.json();
            dispatch(updateHealth({
                assetId,
                healthIndex: result.assessment.health_index,
                healthConfidence: result.assessment.health_confidence,
                anomalyScore: result.assessment.anomaly_score,
                physicsResidual: result.assessment.physics_residual,
                lastUpdate: result.assessment.timestamp,
            }));

            const updatedState = await fetchAssetState(assetId);
            dispatch(updateCapability({
                assetId,
                surfaceFinishGrade: updatedState.capability.surfaceFinishGrade,
                toleranceClass: updatedState.capability.toleranceClass,
                assuranceState: updatedState.capability.assuranceState,
                energyCostPerPart: updatedState.capability.energyCostPerPart,
            }));
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        setLoading(true);
        try {
            setError(null);
            const updatedState = await fetchAssetState(assetId);
            dispatch(updateHealth(updatedState.health));
            dispatch(updateCapability(updatedState.capability));
        } catch (err) {
            setError((err as Error).message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Paper sx={{ p: 2, borderRadius: 3, bgcolor: 'rgba(255,87,34,0.05)' }}>
            <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                Fault Injector
            </Typography>

            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            <Box mb={2}>
                <Typography variant="caption" color="text.secondary">
                    Vibration (mm/s): {vibration.toFixed(1)}
                </Typography>
                <Slider
                    value={vibration}
                    onChange={(_, v) => setVibration(v as number)}
                    min={0.5}
                    max={6.0}
                    step={0.1}
                    size="small"
                    marks={[
                        { value: 0.5, label: '0.5' },
                        { value: 3, label: '3' },
                        { value: 6, label: '6' },
                    ]}
                />
            </Box>

            <Box mb={2}>
                <Typography variant="caption" color="text.secondary">
                    Wear Level: {(wear * 100).toFixed(0)}%
                </Typography>
                <Slider
                    value={wear}
                    onChange={(_, v) => setWear(v as number)}
                    min={0}
                    max={1}
                    step={0.05}
                    size="small"
                    color="warning"
                    marks={[
                        { value: 0, label: '0%' },
                        { value: 0.5, label: '50%' },
                        { value: 1, label: '100%' },
                    ]}
                />
            </Box>

            <Box display="flex" gap={1}>
                <Button
                    variant="contained"
                    color="error"
                    size="small"
                    startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <BugReport />}
                    onClick={handleInjectFault}
                    disabled={loading}
                    fullWidth
                >
                    Inject Fault
                </Button>
                <Button
                    variant="outlined"
                    size="small"
                    onClick={handleReset}
                    sx={{ minWidth: 80 }}
                >
                    Refresh
                </Button>
            </Box>
        </Paper>
    );
}
