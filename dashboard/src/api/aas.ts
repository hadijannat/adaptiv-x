/**
 * AAS API Client for Dashboard.
 * 
 * Fetches asset state from the BaSyx AAS Environment via Vite proxy.
 */

import type { Asset, AssetHealth, AssetCapability } from '../store/assetsSlice';

const AAS_BASE_URL = '/api/aas';

function encodeId(identifier: string): string {
    // Base64-URL encode an identifier for AAS API paths
    return btoa(identifier).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export async function listAssets(): Promise<string[]> {
    try {
        const response = await fetch(`${AAS_BASE_URL}/shells`);
        if (!response.ok) {
            throw new Error(`Failed to fetch shells: ${response.status}`);
        }
        const data = await response.json();
        const shells = data.result || data;

        return shells.map((shell: { idShort?: string; id?: string }) => {
            const id = shell.idShort || shell.id || '';
            return id.includes(':') ? id.split(':').pop() : id;
        }).filter(Boolean) as string[];
    } catch (error) {
        console.error('Failed to list assets:', error);
        throw error;
    }
}

export async function fetchAssetState(assetId: string): Promise<Asset> {
    const healthSubmodelId = `urn:adaptivx:submodel:health:${assetId}`;
    const capabilitySubmodelId = `urn:adaptivx:submodel:capability:${assetId}`;

    const health = await fetchHealthSubmodel(healthSubmodelId, assetId);
    const capability = await fetchCapabilitySubmodel(capabilitySubmodelId, assetId);

    return {
        id: assetId,
        name: assetId,
        health,
        capability,
    };
}

async function fetchHealthSubmodel(submodelId: string, assetId: string): Promise<AssetHealth> {
    const encodedId = encodeId(submodelId);

    try {
        const response = await fetch(`${AAS_BASE_URL}/submodels/${encodedId}`);
        if (!response.ok) {
            throw new Error(`Health submodel not found: ${response.status}`);
        }
        const data = await response.json();
        const elements = data.submodelElements || [];

        const getValue = (idShort: string): string | undefined => {
            const el = elements.find((e: { idShort: string }) => e.idShort === idShort);
            return el?.value;
        };

        return {
            assetId,
            healthIndex: parseInt(getValue('HealthIndex') || '100', 10),
            healthConfidence: parseFloat(getValue('HealthConfidence') || '1.0'),
            anomalyScore: parseFloat(getValue('AnomalyScore') || '0'),
            physicsResidual: parseFloat(getValue('PhysicsResidual') || '0'),
            lastUpdate: getValue('LastUpdate') || new Date().toISOString(),
        };
    } catch (error) {
        console.error(`Failed to fetch health for ${assetId}:`, error);
        return {
            assetId,
            healthIndex: 100,
            healthConfidence: 1.0,
            anomalyScore: 0,
            physicsResidual: 0,
            lastUpdate: new Date().toISOString(),
        };
    }
}

async function fetchCapabilitySubmodel(submodelId: string, assetId: string): Promise<AssetCapability> {
    const encodedId = encodeId(submodelId);

    try {
        const response = await fetch(`${AAS_BASE_URL}/submodels/${encodedId}`);
        if (!response.ok) {
            throw new Error(`Capability submodel not found: ${response.status}`);
        }
        const data = await response.json();
        const elements = data.submodelElements || [];

        // Find ProcessCapability:Milling collection
        const millingCapability = elements.find(
            (e: { idShort: string }) => e.idShort === 'ProcessCapability:Milling'
        );

        if (!millingCapability?.value) {
            throw new Error('Milling capability not found');
        }

        const getValue = (idShort: string): string | undefined => {
            const el = millingCapability.value.find((e: { idShort: string }) => e.idShort === idShort);
            return el?.value;
        };

        const grade = getValue('SurfaceFinishGrade');
        const normalizedGrade = grade === 'A' || grade === 'B' || grade === 'C' ? grade : 'C';

        const assurance = getValue('AssuranceState');
        const normalizedAssurance =
            assurance === 'assured' || assurance === 'offered' || assurance === 'notAvailable'
                ? assurance
                : 'notAvailable';

        return {
            assetId,
            surfaceFinishGrade: normalizedGrade,
            toleranceClass: getValue('ToleranceClass') || '±0.02mm',
            assuranceState: normalizedAssurance,
            energyCostPerPart: parseFloat(getValue('EnergyCostPerPart_kWh') || '0.85'),
        };
    } catch (error) {
        console.error(`Failed to fetch capability for ${assetId}:`, error);
        return {
            assetId,
            surfaceFinishGrade: 'C',
            toleranceClass: 'N/A',
            assuranceState: 'notAvailable',
            energyCostPerPart: 0,
        };
    }
}
