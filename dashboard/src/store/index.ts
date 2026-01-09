import { configureStore } from '@reduxjs/toolkit';
import assetsReducer from './assetsSlice';
import jobsReducer from './jobsSlice';

export const store = configureStore({
    reducer: {
        assets: assetsReducer,
        jobs: jobsReducer,
    },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
