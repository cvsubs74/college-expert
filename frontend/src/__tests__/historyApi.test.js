/**
 * api.js wrapper added for the year-history consumers (#286):
 *   - getUniversityHistory → GET {KB}?id&action=history
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('axios', () => {
    const mockAxios = {
        post: vi.fn(),
        get: vi.fn(),
        create: vi.fn(() => ({
            post: vi.fn(),
            get: vi.fn(),
        })),
    };
    return { default: mockAxios };
});

import axios from 'axios';
import { getUniversityHistory } from '../services/api';

beforeEach(() => {
    axios.get.mockReset();
});

describe('getUniversityHistory', () => {
    it('GETs the KB base URL with id + action=history', async () => {
        axios.get.mockResolvedValue({
            data: { success: true, snapshots: [], reported_trends: [], notes: [] },
        });

        const result = await getUniversityHistory('testu');

        expect(axios.get).toHaveBeenCalledTimes(1);
        const [url, config] = axios.get.mock.calls[0];
        expect(url).toBe('http://test-kb.example'); // from setup.js env mocks
        expect(config.params).toEqual({ id: 'testu', action: 'history' });
        expect(result.success).toBe(true);
    });

    it('returns success:false with the server error on failure', async () => {
        axios.get.mockRejectedValue({
            response: { data: { error: 'University ghost not found' } },
            message: 'Request failed with status code 404',
        });

        const result = await getUniversityHistory('ghost');
        expect(result.success).toBe(false);
        expect(result.error).toBe('University ghost not found');
    });

    it('falls back to the network message when there is no response body', async () => {
        axios.get.mockRejectedValue({ message: 'Network Error' });
        const result = await getUniversityHistory('testu');
        expect(result.success).toBe(false);
        expect(result.error).toBe('Network Error');
    });
});
