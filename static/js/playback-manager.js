import { Utils } from './utils.js';
import { NavigationManager } from './navigation-manager.js';

export const PlaybackManager = {
    currentlyPlaying: null,
    playbackUpdateInterval: null,

    async togglePlay(songId) {
        try {
            if (this.currentlyPlaying === songId) {
                await this.stopPlayback();
            } else {
                await this.startPlayback(songId);
            }
        } catch (error) {
            console.error('Playback error:', error);
            alert('Make sure Spotify is open and playing somewhere');
        }
    },

    async startPlayback(songId) {
        await Utils.apiCall('/api/play', 'POST', { song_id: songId });
        this.updatePlaybackState(songId);
        await this.markAsPlayed(songId);
        this.startPlaybackUpdates();
        NavigationManager.selectRow(songId);
    },

    async stopPlayback() {
        await Utils.apiCall('/api/stop', 'POST');
        this.updatePlaybackState(null);
        this.stopPlaybackUpdates();
    },

    updatePlaybackState(songId) {
        if (this.currentlyPlaying) {
            document.getElementById(`song-row-${this.currentlyPlaying}`)
                .classList.remove('active-song');
        }

        this.currentlyPlaying = songId;
        if (songId) {
            document.getElementById(`song-row-${songId}`)
                .classList.add('active-song');
        }
    },

    async markAsPlayed(songId) {
        await Utils.apiCall('/api/mark_played', 'POST', { song_id: songId });
        document.getElementById(`song-row-${songId}`).classList.add('played');
    },

    startPlaybackUpdates() {
        if (this.playbackUpdateInterval) {
            clearInterval(this.playbackUpdateInterval);
        }
        this.updatePlaybackStatus();
        this.playbackUpdateInterval = setInterval(() => this.updatePlaybackStatus(), 1000);
    },

    stopPlaybackUpdates() {
        if (this.playbackUpdateInterval) {
            clearInterval(this.playbackUpdateInterval);
            this.playbackUpdateInterval = null;
        }
    },

    async updatePlaybackStatus() {
        if (!this.currentlyPlaying) return;
        
        try {
            const data = await Utils.apiCall('/api/playback_status');
            if (data.is_playing) {
                const progressText = `(${Utils.formatTime(data.progress_ms)}/${Utils.formatTime(data.duration_ms)})`;
                const playButton = document.querySelector(`#song-row-${this.currentlyPlaying} .play-button`);
                playButton.innerHTML = `<div class="flex justify-center items-center w-full h-full"><span class="text-xs text-gray-800 dark:text-white">${progressText}</span></div>`;
            }
        } catch (error) {
            console.error('Error updating playback status:', error);
        }
    }
};