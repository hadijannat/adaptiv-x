import { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
    Box,
    Button,
    Paper,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Chip,
    CircularProgress,
} from '@mui/material';
import { Send, Refresh } from '@mui/icons-material';
import { RootState } from '../store';
import { addJob, Job } from '../store/jobsSlice';

export function DispatcherView() {
    const dispatch = useDispatch();
    const jobs = useSelector((state: RootState) => state.jobs.items);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDispatch = async () => {
        setLoading(true);
        const jobId = `JOB-${Date.now().toString().slice(-6)}`;

        try {
            setError(null);
            const response = await fetch('/api/dispatcher/dispatch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    job_id: jobId,
                    description: 'Precision milling job',
                    capability_requirements: {
                        surface_finish_grade: 'A',
                        assurance_required: true,
                    },
                }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `Dispatch failed (${response.status})`);
            }

            const result = await response.json();
            dispatch(addJob({
                jobId: result.job_id,
                description: 'Precision milling job',
                assignedAsset: result.assigned_asset,
                status: result.assigned_asset ? 'assigned' : 'failed',
                timestamp: result.timestamp,
                candidatesEvaluated: result.candidates_evaluated,
                selectionReason: result.selection_reason,
            }));
        } catch (err) {
            setError((err as Error).message);
            dispatch(addJob({
                jobId,
                description: 'Precision milling job',
                assignedAsset: null,
                status: 'failed',
                timestamp: new Date().toISOString(),
                candidatesEvaluated: 0,
                selectionReason: (err as Error).message,
            }));
        } finally {
            setLoading(false);
        }
    };

    const getStatusColor = (status: Job['status']) => {
        switch (status) {
            case 'assigned': return 'success';
            case 'pending': return 'warning';
            case 'completed': return 'info';
            case 'failed': return 'error';
        }
    };

    return (
        <Paper sx={{ p: 3, borderRadius: 4 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
                <Typography variant="h6" fontWeight={600}>
                    Job Dispatcher
                </Typography>
                <Box display="flex" gap={1}>
                    <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        size="small"
                        onClick={() => window.location.reload()}
                    >
                        Refresh
                    </Button>
                    <Button
                        variant="contained"
                        startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <Send />}
                        onClick={handleDispatch}
                        disabled={loading}
                        sx={{
                            background: 'linear-gradient(135deg, #00BCD4 0%, #0097A7 100%)',
                            '&:hover': {
                                background: 'linear-gradient(135deg, #26C6DA 0%, #00ACC1 100%)',
                            },
                        }}
                    >
                        Dispatch Precision Job
                    </Button>
                </Box>
            </Box>

            <TableContainer>
                <Table size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Job ID</TableCell>
                            <TableCell>Description</TableCell>
                            <TableCell>Assigned To</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Candidates</TableCell>
                            <TableCell>Reason</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {jobs.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                                    <Typography color="text.secondary">
                                        No jobs dispatched yet. Click "Dispatch Precision Job" to test routing.
                                    </Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            jobs.map((job) => (
                                <TableRow key={job.jobId} hover>
                                    <TableCell>
                                        <Typography variant="body2" fontWeight={500}>
                                            {job.jobId}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>{job.description}</TableCell>
                                    <TableCell>
                                        {job.assignedAsset ? (
                                            <Chip label={job.assignedAsset} size="small" color="primary" />
                                        ) : (
                                            <Typography color="text.secondary">—</Typography>
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        <Chip
                                            label={job.status}
                                            size="small"
                                            color={getStatusColor(job.status)}
                                        />
                                    </TableCell>
                                    <TableCell>{job.candidatesEvaluated}</TableCell>
                                    <TableCell>
                                        <Typography variant="caption" color="text.secondary" noWrap sx={{ maxWidth: 200, display: 'block' }}>
                                            {job.selectionReason}
                                        </Typography>
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>

            {error && (
                <Box mt={2}>
                    <Typography variant="caption" color="error">
                        {error}
                    </Typography>
                </Box>
            )}
        </Paper>
    );
}
