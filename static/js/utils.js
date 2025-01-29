export const Utils = {
    formatTime(ms) {
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    },

    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json',
                },
                ...(data && { body: JSON.stringify(data) })
            };

            const response = await fetch(endpoint, options);
            if (!response.ok) throw new Error(`API call failed: ${response.statusText}`);
            return await response.json();
        } catch (error) {
            console.error(`Error in API call to ${endpoint}:`, error);
            throw error;
        }
    }
};