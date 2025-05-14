// portfolio/static/portfolio/js/theme-toggle.js

// Wait for the DOM to be fully loaded before running the script
document.addEventListener('DOMContentLoaded', function () {
    // Get references to the theme toggle button and its icons
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleSunIcon = document.getElementById('theme-toggle-sun-icon');
    const themeToggleMoonIcon = document.getElementById('theme-toggle-moon-icon');
    const htmlElement = document.documentElement; // Reference to the <html> element

    // Function to update the button icon based on the current theme
    function updateButtonIcon() {
        // Check if the elements exist before trying to access their classList
        if (themeToggleSunIcon && themeToggleMoonIcon) {
            if (htmlElement.classList.contains('dark')) {
                themeToggleMoonIcon.classList.remove('hidden');
                themeToggleSunIcon.classList.add('hidden');
            } else {
                themeToggleSunIcon.classList.remove('hidden');
                themeToggleMoonIcon.classList.add('hidden');
            }
        } else {
            console.warn('Theme toggle icons not found. Ensure their IDs are correct in base.html.');
        }
    }

    // Update the button icon on initial load.
    // The class on <html> should already be set by the inline script in <head>.
    updateButtonIcon();

    // Add event listener for the toggle button click, only if the button exists
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function () {
            // Toggle the 'dark' class on the <html> element
            htmlElement.classList.toggle('dark');

            // Update localStorage with the new theme preference
            if (htmlElement.classList.contains('dark')) {
                localStorage.setItem('color-theme', 'dark');
            } else {
                localStorage.setItem('color-theme', 'light');
            }

            // Update the button icon to reflect the change
            updateButtonIcon();
        });
    } else {
        console.warn('Theme toggle button not found. Ensure its ID "theme-toggle" is correct in base.html.');
    }

    // Optional: Listen for system theme changes if no user preference is stored in localStorage.
    // This part is more about reacting to OS-level changes if the user hasn't made a site-specific choice.
    // The initial theme setting script in <head> already handles the initial load based on system preference.
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
        // Only apply system preference if no theme is explicitly set by the user on the site
        if (!localStorage.getItem('color-theme')) {
            if (event.matches) { // System prefers dark
                htmlElement.classList.add('dark');
            } else { // System prefers light
                htmlElement.classList.remove('dark');
            }
            updateButtonIcon(); // Update icon if system preference changes the theme
        }
    });

    // If you are still having issues with Firefox bfcache and the button icon state,
    // you might also need to re-run updateButtonIcon() on pageshow in this file.
    window.addEventListener('pageshow', function(event) {
        if (event.persisted) {
            // The class on <html> should be correct due to the head script's pageshow listener.
            // Now, just ensure the button icon reflects that state.
            updateButtonIcon();
        }
    });
});
