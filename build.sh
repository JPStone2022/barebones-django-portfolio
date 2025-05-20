#!/usr/bin/env bash
# build.sh - Script executed by Render during deployment builds

# Exit immediately if a command exits with a non-zero status.
set -o errexit

echo "Starting build..."

# Upgrade pip and install dependencies from requirements.txt
pip install --upgrade pip
pip install -r requirements.txt
echo "Dependencies installed."

# Run collectstatic to gather static files into STATIC_ROOT
echo "Running collectstatic..."
python manage.py collectstatic --no-input --clear
echo "Collectstatic finished."

# Apply any outstanding database migrations
echo "Running database migrations..."
python manage.py migrate --no-input # && python manage.py import_data data/demos.csv --model_type demos --update # && python manage.py import_data data/skills.csv --model_type skills --update && python manage.py import_data data/topics.csv --model_type topics --update
echo "Migrations finished."
python manage.py initial_populate_all
# --- Add Data Import/Update Commands Here ---
# IMPORTANT: Use the --update flag to avoid duplicates on redeploy!
# Adjust paths, model_type, and unique_field as needed for your CSVs.
# echo "Importing/Updating data from CSV..."

# Example for projects (update based on slug)
# Ensure data/projects.csv is committed to your Git repo
# python manage.py import_data data/projects.csv --model_type projects --update --unique_field slug

# Example for skills (update based on name)
# Ensure data/skills.csv is committed to your Git repo
# python manage.py import_data data/skills.csv --model_type skills --update --unique_field name

# Example for topics (update based on slug)
# Ensure data/topics.csv is committed to your Git repo
# python manage.py import_data data/topics.csv --model_type topics --update --unique_field slug

# Example for certificates (update based on title)
# Ensure data/certificates.csv is committed to your Git repo
# python manage.py import_data data/certificates.csv --model_type certificates --update --unique_field title

# Example for recommendations (update based on name)
# Ensure data/recommendations.csv is committed to your Git repo
# python manage.py import_data data/recommendations.csv --model_type recommendations --update --unique_field name

echo "Data import/update step finished."
# --- End Data Import/Update Commands ---


echo "Build finished successfully!"
