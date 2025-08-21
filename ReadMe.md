

# OpenAPI JSON Parser & API List Exporter

This repository provides scripts to parse OpenAPI (Swagger) JSON files and export useful API information in CSV and Excel formats.

## Example OpenAPI Source

- [Swagger Petstore UI](https://petstore.swagger.io/)
- [Swagger JSON](https://petstore.swagger.io/v2/swagger.json)

## Usage

### 1. Export All API Details to Excel & CSV

This script extracts endpoints, parameters, responses, tags, models, and security definitions into multiple CSV files and a single Excel workbook with multiple sheets.

```sh
python openAi_to_Excel.py PetStore-swagger.json
```

This is useful for reverse engineering and understanding the system.

### 2. Export API List Only to CSV

This script generates a CSV file containing a list of all API endpoints.

```sh
python openapi_to_csv.py PetStore-swagger.json
```

This helps to quickly get a list of APIs only.