
import { NavigationManager } from './navigation-manager.js';
import { PlaybackManager } from './playback-manager.js';
import { PlaylistManager } from './playlist-manager.js';
import { Utils } from './utils.js';

export const KeyboardManager = {
    handleKeyPress(e) {
        // Ignore if we're in an input field
        if (e.target.tagName === 'INPUT') return;

        const songRows = Array.from(document.querySelectorAll('tr[id^="song-row-"]'));
        const currentIndex = songRows.findIndex(row => 
            row.id === `song-row-${NavigationManager.selectedSongId}`
        );

        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                if (currentIndex > 0) {
                    const prevRow = songRows[currentIndex - 1];
                    NavigationManager.selectRow(prevRow.dataset.songId);
                }
                break;

            case 'ArrowDown':
                e.preventDefault();
                if (currentIndex < songRows.length - 1) {
                    const nextRow = songRows[currentIndex + 1];
                    NavigationManager.selectRow(nextRow.dataset.songId);
                }
                break;

            case ' ':
                e.preventDefault();
                if (NavigationManager.selectedSongId) {
                    PlaybackManager.togglePlay(NavigationManager.selectedSongId);
                }
                break;

            case 'Escape':
                e.preventDefault();
                PlaybackManager.stopPlayback();
                break;

            case 'ArrowLeft':
                e.preventDefault();
                Utils.apiCall('/api/seek', 'POST', { position_ms: -20000 });
                break;

            case 'ArrowRight':
                e.preventDefault();
                Utils.apiCall('/api/seek', 'POST', { position_ms: 20000 });
                break;

            default:
                // Number keys 1-9 for quick playlist toggle
                if (e.key >= '1' && e.key <= '9') {
                    const playlistIndex = parseInt(e.key) - 1;
                    if (NavigationManager.selectedSongId) {
                        const cells = document
                            .getElementById(`song-row-${NavigationManager.selectedSongId}`)
                            .querySelectorAll('.playlist-cell');
                        if (cells[playlistIndex]) {
                            PlaylistManager.toggleSongInPlaylist(cells[playlistIndex]);
                        }
                    }
                }
        }
    }
};