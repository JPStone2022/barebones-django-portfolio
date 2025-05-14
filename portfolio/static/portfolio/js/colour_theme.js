// --- Get references to ALL elements that need styling ---
const themeBlock = document.getElementById('theme-block');

// Intro Block Elements
const introBlock = document.getElementById('intro-block');
const introHeading = document.getElementById('intro-heading');
const introText = document.getElementById('intro-text');
const introButton = document.getElementById('intro-button');

// Project Card Elements
const projectCard = document.getElementById('project-card');
const projectImage = document.getElementById('project-image');
const projectContent = document.getElementById('project-content');
const projectHeading = document.getElementById('project-heading');
const projectText = document.getElementById('project-text');
const projectSkills = document.getElementById('project-skills'); // Container for skill tags
const projectLink = document.getElementById('project-link');

// Demo Card Elements
const demoCard = document.getElementById('demo-card');
const demoInteractiveArea = document.getElementById('demo-interactive-area');
const demoPlaceholderText = document.getElementById('demo-placeholder-text');
const demoContent = document.getElementById('demo-content');
const demoHeading = document.getElementById('demo-heading');
const demoText = document.getElementById('demo-text');
const demoLink = document.getElementById('demo-link');

// Features Block Elements
const featuresBlock = document.getElementById('features-block');
const featuresHeading = document.getElementById('features-heading');
const featuresList = document.getElementById('features-list');

// Theme Control Buttons
const playfulBtn = document.getElementById('playful-theme-btn');
const darkBtn = document.getElementById('dark-theme-btn');
const professionalBtn = document.getElementById('professional-theme-btn');

// --- Define Theme Classes ---
// Base layout classes common to elements
const baseBlockLayout = 'p-6 rounded-lg shadow-sm border-l-4 transition-colors duration-300 ease-in-out';
const baseCardLayout = 'rounded-lg shadow-md overflow-hidden flex flex-col transition-colors duration-300 ease-in-out';
const baseCardContentLayout = 'p-6 flex flex-col flex-grow border-t transition-colors duration-300 ease-in-out';
const baseSkillTag = 'inline-block px-2 py-0.5 rounded-full text-xs font-semibold transition-colors duration-300 ease-in-out';

// Playful Theme Classes
const playfulClasses = {
themeBlock: 'p-6 rounded-lg shadow-inner transition-all duration-300 ease-in-out space-y-8 bg-gradient-to-br from-sky-50 to-yellow-50',
// Intro
introBlock: `${baseBlockLayout} bg-white border-yellow-400`,
introHeading: 'text-xl font-semibold mb-3 text-sky-700',
introText: 'mb-4 leading-relaxed text-sky-800',
introButton: 'px-4 py-2 text-sm font-medium rounded-md shadow transition duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-yellow-400 text-sky-900 hover:bg-yellow-300 focus:ring-yellow-300 focus:ring-offset-white',
// Project Card
projectCard: `${baseCardLayout} bg-white border border-sky-200`,
projectImageSrc: 'https://placehold.co/600x400/FACC15/0C4A6E?text=Playful+Project',
projectContent: `${baseCardContentLayout} border-sky-100`,
projectHeading: 'text-lg font-semibold mb-2 text-sky-700',
projectText: 'text-sm mb-4 flex-grow text-gray-700',
projectSkillTag: `${baseSkillTag} bg-yellow-200 text-yellow-800`,
projectLink: 'text-sm font-medium hover:underline focus:outline-none focus:ring-1 rounded px-1 text-sky-600 hover:text-yellow-500 focus:ring-yellow-300',
// Demo Card
demoCard: `${baseCardLayout} bg-white border border-pink-200`,
demoInteractiveArea: 'h-40 flex items-center justify-center bg-pink-100 border-b border-pink-200',
demoPlaceholderText: 'text-lg font-medium italic text-pink-600',
demoContent: `${baseCardContentLayout} border-pink-100`,
demoHeading: 'text-lg font-semibold mb-2 text-pink-700',
demoText: 'text-sm mb-4 flex-grow text-gray-700',
demoLink: 'text-sm font-medium hover:underline focus:outline-none focus:ring-1 rounded px-1 text-pink-600 hover:text-yellow-500 focus:ring-yellow-300',
// Features Block
featuresBlock: `${baseBlockLayout} bg-white border-sky-500`,
featuresHeading: 'text-xl font-semibold mb-3 text-sky-700',
featuresList: 'list-disc list-inside space-y-1 text-sm leading-relaxed text-gray-700 marker:text-yellow-500',
};

// Dark Theme Classes
const darkClasses = {
themeBlock: 'p-6 rounded-lg shadow-inner transition-all duration-300 ease-in-out space-y-8 bg-slate-900',
// Intro
introBlock: `${baseBlockLayout} bg-slate-800 border-cyan-500`,
introHeading: 'text-xl font-semibold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-400',
introText: 'mb-4 leading-relaxed text-slate-300',
introButton: 'px-4 py-2 text-sm font-medium rounded-md shadow transition duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-cyan-500 text-slate-900 hover:bg-cyan-400 focus:ring-cyan-300 focus:ring-offset-slate-800',
// Project Card
projectCard: `${baseCardLayout} bg-slate-800 border border-slate-700`,
projectImageSrc: 'https://placehold.co/600x400/0F172A/67E8F9?text=Dark+Project',
projectContent: `${baseCardContentLayout} border-slate-700`,
projectHeading: 'text-lg font-semibold mb-2 text-slate-100',
projectText: 'text-sm mb-4 flex-grow text-slate-300',
projectSkillTag: `${baseSkillTag} bg-slate-600 text-slate-200`,
projectLink: 'text-sm font-medium hover:underline focus:outline-none focus:ring-1 rounded px-1 text-cyan-400 hover:text-cyan-300 focus:ring-cyan-500',
// Demo Card
demoCard: `${baseCardLayout} bg-slate-800 border border-slate-700`,
demoInteractiveArea: 'h-40 flex items-center justify-center bg-slate-700 border-b border-slate-600',
demoPlaceholderText: 'text-lg font-medium italic text-purple-400',
demoContent: `${baseCardContentLayout} border-slate-700`,
demoHeading: 'text-lg font-semibold mb-2 text-slate-100',
demoText: 'text-sm mb-4 flex-grow text-slate-300',
demoLink: 'text-sm font-medium hover:underline focus:outline-none focus:ring-1 rounded px-1 text-purple-400 hover:text-purple-300 focus:ring-purple-500',
// Features Block
featuresBlock: `${baseBlockLayout} bg-slate-800 border-teal-500`,
featuresHeading: 'text-xl font-semibold mb-3 text-teal-400',
featuresList: 'list-disc list-inside space-y-1 text-sm leading-relaxed text-slate-300 marker:text-teal-500',
};

// Professional Theme Classes
const professionalClasses = {
themeBlock: 'p-6 rounded-lg shadow-inner transition-all duration-300 ease-in-out space-y-8 bg-gray-100',
// Intro
introBlock: `${baseBlockLayout} bg-white border-blue-600`,
introHeading: 'text-xl font-semibold mb-3 text-gray-800',
introText: 'mb-4 leading-relaxed text-gray-600',
introButton: 'px-4 py-2 text-sm font-medium rounded-md shadow transition duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-400 focus:ring-offset-white',
// Project Card
projectCard: `${baseCardLayout} bg-white border border-gray-200`,
projectImageSrc: 'https://placehold.co/600x400/EBF4FF/1D4ED8?text=Pro+Project', // Light blue bg, dark blue text
projectContent: `${baseCardContentLayout} border-gray-200`,
projectHeading: 'text-lg font-semibold mb-2 text-gray-900',
projectText: 'text-sm mb-4 flex-grow text-gray-700',
projectSkillTag: `${baseSkillTag} bg-blue-100 text-blue-800`,
projectLink: 'text-sm font-medium hover:underline focus:outline-none focus:ring-1 rounded px-1 text-blue-600 hover:text-blue-800 focus:ring-blue-300',
// Demo Card
demoCard: `${baseCardLayout} bg-white border border-gray-200`,
demoInteractiveArea: 'h-40 flex items-center justify-center bg-gray-100 border-b border-gray-200',
demoPlaceholderText: 'text-lg font-medium italic text-gray-500',
demoContent: `${baseCardContentLayout} border-gray-200`,
demoHeading: 'text-lg font-semibold mb-2 text-gray-900',
demoText: 'text-sm mb-4 flex-grow text-gray-700',
demoLink: 'text-sm font-medium hover:underline focus:outline-none focus:ring-1 rounded px-1 text-blue-600 hover:text-blue-800 focus:ring-blue-300',
// Features Block
featuresBlock: `${baseBlockLayout} bg-white border-gray-500`,
featuresHeading: 'text-xl font-semibold mb-3 text-gray-800',
featuresList: 'list-disc list-inside space-y-1 text-sm leading-relaxed text-gray-600 marker:text-blue-600',
};

// --- Event Listeners ---
playfulBtn.addEventListener('click', () => applyTheme(playfulClasses));
darkBtn.addEventListener('click', () => applyTheme(darkClasses));
professionalBtn.addEventListener('click', () => applyTheme(professionalClasses));

// --- Apply Theme Function ---
function applyTheme(theme) {
// Apply to outer theme block container
themeBlock.className = theme.themeBlock;

// Apply to Intro Block
introBlock.className = theme.introBlock;
introHeading.className = theme.introHeading;
introText.className = theme.introText;
introButton.className = theme.introButton;

// Apply to Project Card
projectCard.className = theme.projectCard;
projectImage.src = theme.projectImageSrc; // Update image source for theme
projectContent.className = theme.projectContent;
projectHeading.className = theme.projectHeading;
projectText.className = theme.projectText;
projectLink.className = theme.projectLink;
// Apply skill tag styles dynamically
projectSkills.querySelectorAll('.skill-tag').forEach(tag => {
tag.className = theme.projectSkillTag;
});

// Apply to Demo Card
demoCard.className = theme.demoCard;
demoInteractiveArea.className = theme.demoInteractiveArea;
demoPlaceholderText.className = theme.demoPlaceholderText;
demoContent.className = theme.demoContent;
demoHeading.className = theme.demoHeading;
demoText.className = theme.demoText;
demoLink.className = theme.demoLink;

// Apply to Features Block
featuresBlock.className = theme.featuresBlock;
featuresHeading.className = theme.featuresHeading;
featuresList.className = theme.featuresList;
}

// --- Initial Theme ---
// Set the initial theme when the page loads (e.g., Professional)
applyTheme(professionalClasses);