# Django Advanced Portfolio & AI/ML Demos Hub

This repository contains the source code for a comprehensive personal portfolio website built with Django (`dl_portfolio_project`). It's designed to showcase projects, skills, certificates, blog posts, and interactive AI/Machine Learning demos. The content is highly customizable through the Django admin interface and CSV data imports.

## Live Site

**(Link to your live portfolio site here, e.g., `https://www.yourname.com`)**

## Table of Contents

1.  [Key Features](#key-features)
2.  [Technology Stack](#technology-stack)
3.  [Project Structure](#project-structure)
4.  [Setup and Installation](#setup-and-installation)
    * [Prerequisites](#prerequisites)
    * [Cloning the Repository](#cloning-the-repository)
    * [Setting up the Virtual Environment](#setting-up-the-virtual-environment)
    * [Installing Dependencies](#installing-dependencies)
    * [Database Setup](#database-setup)
    * [Environment Variables](#environment-variables)
    * [Initial Data Population](#initial-data-population)
5.  [Running the Application](#running-the-application)
6.  [Admin Interface](#admin-interface)
7.  [Deployment (Render.com)](#deployment-rendercom)
8.  [Future Enhancements (Examples)](#future-enhancements-examples)
9.  [Contributing](#contributing)
10. [License](#license)
11. [Contact](#contact)

## Key Features

* **Dynamic Personal Profile**: Customizable "About Me", "Hire Me", and general profile information managed via the Django admin and CSV imports.
* **Portfolio Showcase**: Dedicated sections for:
    * **Projects**: Detailed project pages with descriptions, images, technologies used, challenges, outcomes, and links (GitHub, live demo, papers).
    * **Certificates**: Display of certifications with issuer, date, and links to credentials.
    * **Skills**: Categorized skills with descriptions.
    * **Topics**: Organization of projects and content by topic areas.
* **Interactive Demos Hub**:
    * A variety of AI/ML demos including Image Classification (TensorFlow/Keras), Sentiment Analysis (Hugging Face Transformers), Data Analysis & Wrangling (Pandas, Matplotlib), Explainable AI (Scikit-learn), Causal Inference (Statsmodels), Optimization (SciPy), and Neural Machine Translation (Keras).
    * Generic framework for adding more content-driven demo/concept explanation pages, populated from CSVs.
* **Blog**: Integrated blogging platform with Markdown support (`markdownify`).
* **Recommendations**: Section for sharing recommended products, tools, or resources, populated from CSVs.
* **Colophon Page**: Details the technologies and tools used to build the site.
* **Legal Pages**: Privacy Policy, Terms & Conditions, Accessibility Statement, all manageable via the `UserProfile` model.
* **Sitemap & Robots.txt**: Dynamically generated `sitemap.xml` and `robots.txt` for SEO.
* **Responsive Design**: Styled with Tailwind CSS for adaptability across devices.
* **Dark Mode**: User-selectable light/dark theme (JS toggle and `localStorage`).
* **SEO Friendly**: Meta tags for titles, descriptions, and keywords are dynamically generated.
* **Data Import System**: Robust management commands (`import_data`, `initial_populate_all`, `populate_demos_from_csv`, `populate_recommendations_from_csv`) to populate and update content from CSV files.
* **Syntax Highlighting**: Uses Prism.js for code snippets in demos and blog posts.

## Technology Stack

### Backend
* **Python** (v3.11.5 as per `render.yaml`)
* **Django** (v5.2 as per `requirementsOLD.txt`)
* **Gunicorn** (v23.0.0 - for production WSGI server)
* **dj_database_url** (for database configuration flexibility)
* **python-dotenv** (for managing environment variables locally)
* **psycopg2-binary** (PostgreSQL adapter for production)
* **Django REST framework** (v3.16.0 - Listed in requirements, available for API capabilities)

### Frontend
* **HTML5**
* **Tailwind CSS** (v3.x - via CDN)
* **JavaScript** (Vanilla JS for interactivity, e.g., `theme-toggle.js`)
* **Font Awesome** (v5.15.4 - for icons, via CDN)
* **Google Fonts** (Inter)
* **Prism.js** (for syntax highlighting, via CDN)

### Databases
* **SQLite** (for local development)
* **PostgreSQL** (for production on Render.com)

### AI/ML & Data Science Libraries (for Demos - from `requirementsOLD.txt`)
* **TensorFlow / Keras** (v2.19.0 / v3.9.2)
* **Hugging Face Transformers** (v4.51.3)
* **Pandas** (v2.2.3)
* **NumPy** (v2.1.3)
* **Matplotlib** (v3.10.1) / **Seaborn** (v0.13.2)
* **Scikit-learn** (v1.6.1)
* **Statsmodels** (v0.14.4)
* **SciPy** (v1.15.2)

### Deployment & Tools
* **Git** (Version Control)
* **Render.com** (Hosting Platform)
* **Whitenoise** (v6.9.0 - for serving static files in production)
* **(Your CI/CD tool)** - *Specify if applicable*

## Project Structure

The project is organized into several Django apps, with `dl_portfolio_project` being the main project directory containing `settings.py` and root `urls.py`.

* `portfolio/`: The core application managing user profiles, projects, certificates, colophon, and main site pages (home, about, contact, CV, hire-me, legal pages). Includes `portfolio.context_processors.user_profile_context`.
* `blog/`: Handles blog posts and related functionality.
* `skills/`: Manages skill categories and individual skills.
* `topics/`: Manages topics for categorizing projects.
* `demos/`: Contains views, templates, and management commands (like `populate_demos_from_csv.py`) for all interactive demos and concept explanation pages.
* `recommendations/`: Manages recommended products or resources, including a management command (`populate_recommendations_from_csv.py`) and `recommendations.context_processors.recommendation_context`.
* `core/` (or `dl_portfolio_project/`): Project-level configurations.
    * `management/commands/`: Contains general custom Django management commands like `import_data.py` and `initial_populate_all.py`.
* `templates/`: Project-level templates directory, including `base.html` and `robots.txt`.
* `static/`: Project-level static files (CSS, JS, images).
* `mediafiles/`: Directory for user-uploaded media (configured in `settings.py`).
* `staticfiles/`: Directory where static files are collected for production (configured in `settings.py`).

**Middleware includes:** `whitenoise.middleware.WhiteNoiseMiddleware` for efficient static file serving.

## Setup and Installation

Follow these steps to set up the project locally for development.

### Prerequisites
* Python 3.11.5 (or as specified in your `requirements.txt` / `runtime.txt`)
* Pip (Python package installer)
* Git
* (Optional, for production-like setup) PostgreSQL or your chosen database server.

### Cloning the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
cd YOUR_REPOSITORY_NAME
Setting up the Virtual EnvironmentIt's highly recommended to use a virtual environment:python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
Installing DependenciesInstall all required packages. An example requirementsOLD.txt was provided; ensure you have an up-to-date requirements.txt for your project.pip install -r requirements.txt 
(Generate with pip freeze > requirements.txt from your activated virtual environment after installing all packages.)Database SetupMigrations: Apply the database migrations:python manage.py migrate
(Optional) Create a Superuser: To access the Django admin panel:python manage.py createsuperuser
Environment VariablesThis project uses python-dotenv to load environment variables from a .env file in the project root for local development. For production (e.g., on Render), these are set directly in the hosting environment.Create a .env file in the project root:SECRET_KEY='your_strong_secret_key_for_development_only'
DEBUG=True
DATABASE_URL='sqlite:///db.sqlite3' # For local SQLite

# Optional Email Settings for local testing (if using SMTP backend)
# EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend' # Or console.EmailBackend
# EMAIL_HOST='smtp.example.com'
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER='your_email@example.com'
# EMAIL_HOST_PASSWORD='your_email_password'
# DEFAULT_FROM_EMAIL='your_email@example.com'

# For Render.com, these will be set in the environment:
# DATABASE_URL (provided by Render's PostgreSQL service)
# SECRET_KEY (generated by Render or set by you)
# PYTHON_VERSION
# WEB_CONCURRENCY
# DJANGO_ALLOWED_HOSTS (e.g., 'your-app-name.onrender.com 127.0.0.1')
Your settings.py is configured to read these variables.Initial Data PopulationThis project uses custom management commands to populate the database from CSV files. The main script for this is initial_populate_all.py, which in turn calls other specific scripts.Prepare CSV Files:Ensure you have a data_import/ directory in your project's base directory (as specified in settings.PY:CSV_FILES).Place all necessary CSV files as configured in settings.py in the CSV_FILES dictionary.General Data: The import_data.py script expects CSVs for: UserProfile, SkillCategories, Skills, ProjectTopics, Certificates, Projects, BlogPosts, and ColophonEntries.Demos Data: populate_demos_from_csv.py uses a "summary" CSV (for Demo model cards) and a "content" CSV (for Demo metadata and DemoSection details).Recommendations Data: populate_recommendations_from_csv.py uses a "summary" CSV (for RecommendedProduct) and a "content" CSV (for metadata and RecommendationSection).Refer to the respective management command files for details on expected CSV column headers.Configure CSV Paths in settings.py:The settings.py file contains a CSV_FILES dictionary mapping keys to relative paths (e.g., 'USER_PROFILE_CSV': 'data_import/00_user_profile.csv'). Verify these paths.Run the Population Script:python manage.py initial_populate_all
This command will call import_data, populate_demos_from_csv, and populate_recommendations_from_csv in sequence. Review the output for any errors. You can also run these scripts individually:# Example:
python manage.py import_data data_import/00_user_profile.csv --model_type userprofile --update --unique_field site_identifier
python manage.py populate_demos_from_csv data_import/07a_demos_summary.csv data_import/07b_demos_content.csv
python manage.py populate_recommendations_from_csv data_import/08a_recommendations_summary.csv data_import/08b_recommendations_content.csv
Running the ApplicationLocal DevelopmentOnce the setup is complete, run the Django development server:python manage.py runserver
The application will typically be available at http://127.0.0.1:8000/.ProductionIn production (e.g., on Render.com), the application is served using Gunicorn, as specified in render.yaml:gunicorn dl_portfolio_project.wsgi:applicationAdmin InterfaceAccess the Django admin panel at http://127.0.0.1:8000/admin/ (or your production URL + /admin/) using the superuser credentials.Deployment (Render.com)This project is configured for deployment on Render.com using the render.yaml blueprint file.Key render.yaml configurations:Database: A PostgreSQL database service (portfolio-db) is defined.Web Service: A Python web service (portfolio-web) is defined.Python Version: 3.11.5Build Command: ./build.shStart Command: gunicorn dl_portfolio_project.wsgi:applicationEnvironment Variables: DATABASE_URL (from the database service), SECRET_KEY (auto-generated), PYTHON_VERSION, WEB_CONCURRENCY.build.sh Script:The build.sh script automates the deployment build process on Render:Upgrades pip.Installs Python dependencies from requirements.txt.Runs python manage.py collectstatic --no-input to gather static files for Whitenoise.Runs python manage.py migrate --no-input to apply database migrations.Note: The build.sh script contains commented-out lines for individual import_data commands. For a fresh deployment where data needs to be populated, you might consider adding a call to python manage.py initial_populate_all in build.sh or running it manually via Render's shell after the first deployment. Subsequent data updates can be managed via the admin or by re-running specific import commands with the --update flag.Static Files:Static files are handled by Whitenoise, which is configured in settings.py (whitenoise.middleware.WhiteNoiseMiddleware).Future Enhancements (Examples)Interactive visualizations for project data or blog statistics.Advanced search functionality with faceting.User accounts for comments or saving preferences.Integration with a headless CMS for some content types.More sophisticated AI/ML demos with real-time interaction.ContributingContributions are welcome! If you'd like to contribute, please follow these steps:Fork the repository.Create a new branch (git checkout -b feature/your-feature-name).Make your changes and commit them (git commit -m 'Add some feature').Push to the branch (git push origin feature/your-feature-name).Open a Pull Request.Please ensure your code adheres to the project's coding standards (e.g., run a linter like Flake8 or Black).License(Specify your project's license here, e.g., MIT License, Apache 2.0. If unsure, you can start with MIT.)Example:This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
ContactYour Name – @YourTwitterHandle – your.email@example.comProject Link: