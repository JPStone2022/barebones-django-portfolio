// static_src/tailwind.config.js
module.exports = {
  darkMode: 'class',
  content: [
    '../templates/**/*.html',        // For project-level templates
    '../**/templates/**/*.html',     // For app-level templates (e.g., ../my_app/templates/**/*.html)
    '../**/forms.py',                // If you use classes in Django forms
    './src/**/*.js',                 // If you have JS files using Tailwind classes
    // Add any other paths specific to your project structure
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};