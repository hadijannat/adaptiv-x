import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
    Box,
    Container,
    Typography,
    Grid,
    AppBar,
    Toolbar,
    Chip,
    Alert,
} from '@mui/material';
import { PrecisionManufacturing, Hub } from '@mui/icons-material';
import { RootState } from './store';
import { setAssets, setError, setLoading } from './store/assetsSlice';
import { HealthPanel } from './components/HealthPanel';
import { SkillCard } from './components/SkillCard';
import { DispatcherView } from './components/DispatcherView';
import { FaultInjector } from './components/FaultInjector';
import { useMqtt } from './hooks/useMqtt';
import { fetchAssetState, listAssets } from './api/aas';

export default function App() {
    const dispatch = useDispatch();
    const assets = useSelector((state: RootState) => state.assets.items);
    const loading = useSelector((state: RootState) => state.assets.loading);
    const error = useSelector((state: RootState) => state.assets.error);
    const { isConnected } = useMqtt();

    useEffect(() => {
        let active = true;

        const loadAssets = async () => {
            dispatch(setLoading(true));
            try {
                const assetIds = await listAssets();
                const assetStates = await Promise.all(
                    assetIds.map((assetId) => fetchAssetState(assetId))
                );
                if (!active) return;
                const record = assetStates.reduce((acc, asset) => {
                    acc[asset.id] = asset;
                    return acc;
                }, {} as Record<string, typeof assetStates[number]>);
                dispatch(setAssets(record));
                dispatch(setError(null));
            } catch (err) {
                if (!active) return;
                dispatch(setError((err as Error).message));
            } finally {
                if (active) {
                    dispatch(setLoading(false));
                }
            }
        };

        loadAssets();
        const interval = setInterval(loadAssets, 10000);

        return () => {
            active = false;
            clearInterval(interval);
        };
    }, [dispatch]);

    return (
        <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
            {/* Header */}
            <AppBar
                position="static"
                sx={{
                    bgcolor: 'transparent',
                    backgroundImage: 'linear-gradient(90deg, rgba(0,188,212,0.1) 0%, transparent 100%)',
                    borderBottom: '1px solid rgba(255,255,255,0.08)',
                }}
            >
                <Toolbar>
                    <Hub sx={{ mr: 2, color: 'primary.main' }} />
                    <Typography variant="h6" fontWeight={700} sx={{ flexGrow: 1 }}>
                        Adaptiv-X
                        <Typography component="span" variant="caption" sx={{ ml: 1, opacity: 0.7 }}>
                            Self-Healing Digital Twin
                        </Typography>
                    </Typography>
                    <Chip
                        icon={<PrecisionManufacturing />}
                        label={isConnected ? 'MQTT Connected' : 'MQTT Disconnected'}
                        color={isConnected ? 'success' : 'warning'}
                        size="small"
                        variant="outlined"
                    />
                </Toolbar>
            </AppBar>

            <Container maxWidth="xl" sx={{ py: 4 }}>
                {error && (
                    <Alert severity="error" sx={{ mb: 3 }}>
                        {error}
                    </Alert>
                )}

                {/* Asset Grid */}
                <Grid container spacing={4}>
                    {Object.values(assets).map((asset) => (
                        <Grid item xs={12} md={6} key={asset.id}>
                            <Box display="flex" flexDirection="column" gap={3}>
                                {/* Health Panel */}
                                <HealthPanel health={asset.health} assetName={asset.name} />

                                {/* Skills & Fault Injector Side by Side */}
                                <Grid container spacing={2}>
                                    <Grid item xs={12} sm={7}>
                                        <SkillCard capability={asset.capability} />
                                    </Grid>
                                    <Grid item xs={12} sm={5}>
                                        <FaultInjector assetId={asset.id} />
                                    </Grid>
                                </Grid>
                            </Box>
                        </Grid>
                    ))}
                </Grid>

                {!loading && Object.values(assets).length === 0 && !error && (
                    <Alert severity="info" sx={{ mt: 3 }}>
                        No assets discovered yet. Ensure the AAS Environment is running and seeded.
                    </Alert>
                )}

                {/* Dispatcher Section */}
                <Box mt={4}>
                    <DispatcherView />
                </Box>

                {/* Footer */}
                <Box mt={4} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                        Adaptiv-X v0.1.0 • Capability-Based Self-Healing for Industrial Digital Twins
                    </Typography>
                </Box>
            </Container>
        </Box>
    );
}
