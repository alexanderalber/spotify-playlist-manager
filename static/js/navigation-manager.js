export const NavigationManager = {
    selectedSongId: null,

    init() {
        this.setupRowClickHandlers();
        this.selectFirstRow();
    },

    setupRowClickHandlers() {
        document.querySelectorAll('tr[id^="song-row-"]').forEach(row => {
            row.addEventListener('click', (e) => {
                if (e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
                    const songId = row.dataset.songId;
                    this.selectRow(songId);
                }
            });
        });
    },

    selectRow(songId) {
        const prevSelected = document.querySelector('.keyboard-selected');
        if (prevSelected) {
            prevSelected.classList.remove('keyboard-selected');
        }
        
        const row = document.getElementById(`song-row-${songId}`);
        if (row) {
            row.classList.add('keyboard-selected');
            this.selectedSongId = songId;
            row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    },

    selectFirstRow() {
        const firstRow = Array.from(document.querySelectorAll('tr[id^="song-row-"]'))[0];
        if (firstRow) {
            this.selectedSongId = firstRow.dataset.songId;
            this.selectRow(this.selectedSongId);
        }
    }
};