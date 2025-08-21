#!/usr/bin/env python3
"""
Parse a Swagger (OpenAPI 2.0) JSON file and export tabular data.

Outputs:
  - endpoints.csv
  - parameters.csv
  - responses.csv
  - tags.csv
  - models.csv
  - model_properties.csv
  - securities.csv
  - swagger_tables.xlsx   (all of the above as sheets)

Usage:
  python export_swagger_tables.py /path/to/swagger.json  # default prints where files saved
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import pandas as pd


def read_swagger(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_http_methods() -> set:
    # OpenAPI 2.0 standard HTTP methods
    return {"get", "put", "post", "delete", "options", "head", "patch"}


def safe_get(d: dict, key: str, default=None):
    v = d.get(key, default)
    return v if v is not None else default


def join_or_none(values: Optional[List[Any]], sep=", "):
    if not values:
        return None
    return sep.join(str(v) for v in values)


def extract_endpoints(sw: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    base_path = sw.get("basePath")
    host = sw.get("host")
    schemes = sw.get("schemes", [])

    for path, path_item in sw.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        # Path-level parameters (applies to all operations unless overridden)
        path_level_params = path_item.get("parameters", [])

        for method, op in path_item.items():
            if method.lower() not in list_http_methods() or not isinstance(op, dict):
                continue

            tags = op.get("tags", [])
            api_group = tags[0] if tags else None

            consumes = op.get("consumes", sw.get("consumes"))
            produces = op.get("produces", sw.get("produces"))

            # Security requirement (operation-level overrides global)
            security = op.get("security", sw.get("security", []))
            security_flat = []
            for sec in security or []:
                for scheme, scopes in sec.items():
                    if scopes:
                        security_flat.append(f"{scheme}({', '.join(scopes)})")
                    else:
                        security_flat.append(scheme)

            rows.append({
                "api_group": api_group,
                "tags": join_or_none(tags),
                "operationId": op.get("operationId"),
                "summary": op.get("summary"),
                "description": op.get("description"),
                "deprecated": op.get("deprecated", False),
                "method": method.upper(),
                "path": path,
                "full_url_template": build_full_url_template(schemes, host, base_path, path),
                "consumes": join_or_none(consumes),
                "produces": join_or_none(produces),
                "parameters_count": len(op.get("parameters", [])) + len(path_level_params),
                "responses_count": len(op.get("responses", {})),
                "security": join_or_none(security_flat),
            })

    return pd.DataFrame(rows)


def build_full_url_template(schemes, host, base_path, path) -> Optional[str]:
    if not host:
        return None
    scheme = schemes[0] if schemes else "https"
    bp = base_path or ""
    return f"{scheme}://{host}{bp}{path}"


def extract_parameters(sw: Dict[str, Any]) -> pd.DataFrame:
    """
    Flattens both path-level and operation-level parameters.
    """
    rows = []
    for path, path_item in sw.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        path_level_params = path_item.get("parameters", [])

        for method, op in path_item.items():
            if method.lower() not in list_http_methods() or not isinstance(op, dict):
                continue

            tags = op.get("tags", [])
            api_group = tags[0] if tags else None
            operation_id = op.get("operationId")

            # Combine path-level + op-level parameters
            params = []
            params.extend(path_level_params)
            params.extend(op.get("parameters", []))

            for p in params:
                schema = p.get("schema")
                items = p.get("items")
                enum_vals = p.get("enum")
                row = {
                    "api_group": api_group,
                    "operationId": operation_id,
                    "method": method.upper(),
                    "path": path,
                    "name": p.get("name"),
                    "in": p.get("in"),
                    "description": p.get("description"),
                    "required": p.get("required", False),
                    "type": p.get("type"),
                    "format": p.get("format"),
                    "collectionFormat": p.get("collectionFormat"),
                    "items_type": safe_get(items or {}, "type"),
                    "items_format": safe_get(items or {}, "format"),
                    "enum": join_or_none(enum_vals),
                    "$ref": safe_get(schema or {}, "$ref"),
                    "schema_type": safe_get(schema or {}, "type"),
                }
                rows.append(row)

    return pd.DataFrame(rows)


def extract_responses(sw: Dict[str, Any]) -> pd.DataFrame:
    rows = []
    for path, path_item in sw.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        for method, op in path_item.items():
            if method.lower() not in list_http_methods() or not isinstance(op, dict):
                continue

            tags = op.get("tags", [])
            api_group = tags[0] if tags else None
            operation_id = op.get("operationId")

            responses = op.get("responses", {})
            for code, resp in responses.items():
                if not isinstance(resp, dict):
                    continue
                schema = resp.get("schema") or {}
                rows.append({
                    "api_group": api_group,
                    "operationId": operation_id,
                    "method": method.upper(),
                    "path": path,
                    "status_code": code,
                    "description": resp.get("description"),
                    "schema_type": schema.get("type"),
                    "schema_format": schema.get("format"),
                    "schema_$ref": schema.get("$ref"),
                    "schema_items_type": safe_get(schema.get("items", {}), "type"),
                    "schema_items_$ref": safe_get(schema.get("items", {}), "$ref"),
                })
    return pd.DataFrame(rows)


def extract_tags(sw: Dict[str, Any]) -> pd.DataFrame:
    tags = sw.get("tags", [])
    rows = []
    for t in tags:
        rows.append({
            "name": t.get("name"),
            "description": t.get("description"),
            "externalDocs_description": safe_get(t.get("externalDocs", {}), "description"),
            "externalDocs_url": safe_get(t.get("externalDocs", {}), "url"),
        })
    return pd.DataFrame(rows)


def extract_securities(sw: Dict[str, Any]) -> pd.DataFrame:
    secs = sw.get("securityDefinitions", {}) or {}
    rows = []
    for name, s in secs.items():
        scopes = s.get("scopes", {})
        rows.append({
            "name": name,
            "type": s.get("type"),
            "in": s.get("in"),
            "name_in_header": s.get("name"),
            "flow": s.get("flow"),
            "authorizationUrl": s.get("authorizationUrl"),
            "tokenUrl": s.get("tokenUrl"),
            "scopes": join_or_none([f"{k}:{v}" for k, v in scopes.items()]),
        })
    return pd.DataFrame(rows)


def extract_models_and_properties(sw: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Extract 'definitions' (models) and their properties.
    """
    defs = sw.get("definitions", {}) or {}
    model_rows, prop_rows = [], []

    for model_name, model in defs.items():
        required = model.get("required", [])
        xml = model.get("xml", {})
        model_rows.append({
            "model_name": model_name,
            "type": model.get("type"),
            "xml_name": xml.get("name"),
            "description": model.get("description"),
            "required_fields": join_or_none(required),
        })

        props = model.get("properties", {}) or {}
        for prop_name, prop in props.items():
            items = prop.get("items")
            xmlp = prop.get("xml", {})
            enum_vals = prop.get("enum")
            prop_rows.append({
                "model_name": model_name,
                "property_name": prop_name,
                "type": prop.get("type"),
                "format": prop.get("format"),
                "description": prop.get("description"),
                "enum": join_or_none(enum_vals),
                "items_type": safe_get(items or {}, "type"),
                "items_format": safe_get(items or {}, "format"),
                "items_$ref": safe_get(items or {}, "$ref"),
                "$ref": prop.get("$ref"),
                "xml_name": xmlp.get("name"),
                "xml_wrapped": safe_get(xmlp, "wrapped"),
                "example": prop.get("example"),
            })

    return pd.DataFrame(model_rows), pd.DataFrame(prop_rows)


def export_tables(sw_path: Path, out_dir: Path) -> None:
    sw = read_swagger(sw_path)

    endpoints = extract_endpoints(sw)
    parameters = extract_parameters(sw)
    responses = extract_responses(sw)
    tags = extract_tags(sw)
    securities = extract_securities(sw)
    models, model_props = extract_models_and_properties(sw)

    out_dir.mkdir(parents=True, exist_ok=True)

    # CSVs
    endpoints.to_csv(out_dir / "endpoints.csv", index=False)
    parameters.to_csv(out_dir / "parameters.csv", index=False)
    responses.to_csv(out_dir / "responses.csv", index=False)
    tags.to_csv(out_dir / "tags.csv", index=False)
    models.to_csv(out_dir / "models.csv", index=False)
    model_props.to_csv(out_dir / "model_properties.csv", index=False)
    securities.to_csv(out_dir / "securities.csv", index=False)

    # Excel workbook
    with pd.ExcelWriter(out_dir / "swagger_tables.xlsx", engine="xlsxwriter") as xl:
        endpoints.to_excel(xl, sheet_name="endpoints", index=False)
        parameters.to_excel(xl, sheet_name="parameters", index=False)
        responses.to_excel(xl, sheet_name="responses", index=False)
        tags.to_excel(xl, sheet_name="tags", index=False)
        models.to_excel(xl, sheet_name="models", index=False)
        model_props.to_excel(xl, sheet_name="model_properties", index=False)
        securities.to_excel(xl, sheet_name="securities", index=False)


def main():
    # Default to the PetStore example in this workspace if path not provided
    default_path = Path("/mnt/data/PetStore-swagger.json")
    sw_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    if not sw_path.exists():
        print(f"Swagger file not found: {sw_path}")
        sys.exit(1)

    out_dir = Path.cwd() / "swagger_tables_output"
    export_tables(sw_path, out_dir)
    print(f"Done. Tables saved to: {out_dir.resolve()}")


if __name__ == "__main__":
    main()
