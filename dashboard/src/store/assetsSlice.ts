import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AssetHealth {
    assetId: string;
    healthIndex: number;
    healthConfidence: number;
    anomalyScore: number;
    physicsResidual: number;
    lastUpdate: string;
}

export interface AssetCapability {
    assetId: string;
    surfaceFinishGrade: 'A' | 'B' | 'C';
    toleranceClass: string;
    assuranceState: 'assured' | 'offered' | 'notAvailable';
    energyCostPerPart: number;
}

export interface Asset {
    id: string;
    name: string;
    health: AssetHealth;
    capability: AssetCapability;
}

interface AssetsState {
    items: Record<string, Asset>;
    loading: boolean;
    error: string | null;
}

const defaultHealth = (assetId: string): AssetHealth => ({
    assetId,
    healthIndex: 100,
    healthConfidence: 1.0,
    anomalyScore: 0,
    physicsResidual: 0,
    lastUpdate: new Date().toISOString(),
});

const defaultCapability = (assetId: string): AssetCapability => ({
    assetId,
    surfaceFinishGrade: 'C',
    toleranceClass: 'N/A',
    assuranceState: 'notAvailable',
    energyCostPerPart: 0,
});

const createAsset = (assetId: string): Asset => ({
    id: assetId,
    name: assetId,
    health: defaultHealth(assetId),
    capability: defaultCapability(assetId),
});

const initialState: AssetsState = {
    items: {},
    loading: false,
    error: null,
};

const assetsSlice = createSlice({
    name: 'assets',
    initialState,
    reducers: {
        setAssets(state, action: PayloadAction<Record<string, Asset>>) {
            state.items = action.payload;
        },
        upsertAsset(state, action: PayloadAction<Asset>) {
            state.items[action.payload.id] = action.payload;
        },
        updateHealth(state, action: PayloadAction<AssetHealth>) {
            const { assetId } = action.payload;
            if (!state.items[assetId]) {
                state.items[assetId] = createAsset(assetId);
            }
            state.items[assetId].health = action.payload;
        },
        updateCapability(state, action: PayloadAction<AssetCapability>) {
            const { assetId } = action.payload;
            if (!state.items[assetId]) {
                state.items[assetId] = createAsset(assetId);
            }
            state.items[assetId].capability = action.payload;
        },
        setLoading(state, action: PayloadAction<boolean>) {
            state.loading = action.payload;
        },
        setError(state, action: PayloadAction<string | null>) {
            state.error = action.payload;
        },
    },
});

export const {
    setAssets,
    upsertAsset,
    updateHealth,
    updateCapability,
    setLoading,
    setError,
} = assetsSlice.actions;
export default assetsSlice.reducer;
