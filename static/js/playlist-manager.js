
import { Utils } from './utils.js';

export const PlaylistManager = {
    async toggleSongInPlaylist(cell) {
        const songId = cell.dataset.songId;
        const playlistId = cell.dataset.playlistId;
        
        try {
            if (playlistId === 'liked_songs') {
                await this.toggleLikedStatus(cell, songId);
            } else {
                await this.togglePlaylistStatus(cell, songId, playlistId);
            }
        } catch (error) {
            alert('Failed to update playlist. Please try again.');
        }
    },

    async toggleLikedStatus(cell, songId) {
        const endpoint = cell.classList.contains('in-playlist') ? 
            '/api/unlike_song' : '/api/like_song';
        
        await Utils.apiCall(endpoint, 'POST', { song_id: songId });
        this.updateCellStatus(cell);
    },

    async togglePlaylistStatus(cell, songId, playlistId) {
        await Utils.apiCall('/api/toggle_playlist', 'POST', {
            song_id: songId,
            playlist_id: playlistId
        });
        this.updateCellStatus(cell);
    },

    updateCellStatus(cell) {
        cell.classList.toggle('in-playlist');
        cell.textContent = cell.classList.contains('in-playlist') ? '✓' : '+';
    }
};