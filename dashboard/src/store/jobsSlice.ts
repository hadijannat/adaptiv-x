import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Job {
    jobId: string;
    description: string;
    assignedAsset: string | null;
    status: 'pending' | 'assigned' | 'completed' | 'failed';
    timestamp: string;
    candidatesEvaluated: number;
    selectionReason: string;
}

interface JobsState {
    items: Job[];
    loading: boolean;
}

const initialState: JobsState = {
    items: [],
    loading: false,
};

const jobsSlice = createSlice({
    name: 'jobs',
    initialState,
    reducers: {
        addJob(state, action: PayloadAction<Job>) {
            state.items.unshift(action.payload);
            // Keep only last 20 jobs
            if (state.items.length > 20) {
                state.items.pop();
            }
        },
        updateJobStatus(state, action: PayloadAction<{ jobId: string; status: Job['status'] }>) {
            const job = state.items.find(j => j.jobId === action.payload.jobId);
            if (job) {
                job.status = action.payload.status;
            }
        },
        setLoading(state, action: PayloadAction<boolean>) {
            state.loading = action.payload;
        },
    },
});

export const { addJob, updateJobStatus, setLoading } = jobsSlice.actions;
export default jobsSlice.reducer;
