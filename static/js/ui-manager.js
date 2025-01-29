export const UIManager = {
    init() {
        this.setupScrollIndicator();
        this.loadThemePreference();
    },

    setupScrollIndicator() {
        const updateIndicator = () => {
            const container = document.getElementById('table-container');
            const canScroll = container.scrollWidth > container.clientWidth;
            container.parentElement.classList.toggle('can-scroll', canScroll);
        };

        window.addEventListener('load', updateIndicator);
        window.addEventListener('resize', updateIndicator);
    },

    toggleTheme() {
        document.documentElement.classList.toggle('dark');
        localStorage.setItem('theme', 
            document.documentElement.classList.contains('dark') ? 'dark' : 'light'
        );
    },

    loadThemePreference() {
        if (localStorage.theme === 'light') {
            document.documentElement.classList.remove('dark');
        }
    }
};