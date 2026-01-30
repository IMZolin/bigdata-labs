#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p data

# Download the compressed CSV
echo "Downloading OpenFoodFacts dataset..."
curl -L https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz -o data/products.csv.gz

# Extract the CSV
echo "Extracting CSV..."
gzip -d -k data/products.csv.gz  # -k keeps the .gz file

echo "Done! CSV saved as data/products.csv"
