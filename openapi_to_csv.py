#!/usr/bin/env python3
import json
import argparse
import sys
import csv

HTTP_METHODS = {"get","post","put","patch","delete","options","head","trace"}

def load_json(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end+1])
        raise

def join_tags(tags):
    if isinstance(tags, list):
        return "; ".join(str(t) for t in tags)
    return str(tags) if tags else ""

def collect_params(op_level, path_level):
    params = []
    for coll in (path_level or []), (op_level or []):
        for p in coll:
            if not isinstance(p, dict):
                continue
            name = p.get("name","")
            loc = p.get("in","")
            required = p.get("required", False)
            typ = ""
            if isinstance(p.get("schema"), dict):
                typ = p["schema"].get("type","")
            elif "type" in p:
                typ = p.get("type","")
            star = "*" if required else ""
            if typ:
                params.append(f"{name} ({loc}){star} : {typ}")
            else:
                params.append(f"{name} ({loc}){star}")
    # de-dup while preserving order
    seen = set()
    uniq = []
    for x in params:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return "; ".join(uniq)

def get_request_body(op):
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return ""
    req = "required" if rb.get("required") else "optional"
    content = rb.get("content", {})
    if isinstance(content, dict) and content:
        media = ", ".join(list(content.keys())[:5])
        if media:
            req += f" ({media})"
    return req

def get_responses(op):
    responses = op.get("responses", {})
    if isinstance(responses, dict):
        return ", ".join(str(k) for k in responses.keys())
    return ""

def detect_servers(spec):
    if "servers" in spec and isinstance(spec["servers"], list):
        return [s.get("url","") for s in spec["servers"]]
    if "host" in spec:
        scheme = "https"
        if isinstance(spec.get("schemes"), list) and spec["schemes"]:
            scheme = spec["schemes"][0]
        base = spec.get("basePath","")
        return [f"{scheme}://{spec['host']}{base}"]
    return []

def main():
    # Hardcoded input and output file names
    file_name="test-api-docs"
    input_file = file_name+".json"
    output_file = file_name+".csv"

    spec = load_json(input_file)
    version = spec.get("openapi") or spec.get("swagger") or "unknown"
    servers = detect_servers(spec)

    paths = spec.get("paths", {})
    rows = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        path_params = methods.get("parameters", []) if isinstance(methods.get("parameters"), list) else []
        for method, op in methods.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            tags = op.get("tags") or []
            summary = op.get("summary") or ""
            description = op.get("description") or ""
            operation_id = op.get("operationId") or ""
            deprecated = bool(op.get("deprecated", False))
            security = op.get("security", [])
            params_joined = collect_params(op.get("parameters"), path_params)
            req_body = get_request_body(op)
            status_codes = get_responses(op)
            rows.append({
                "API Group (tags)": join_tags(tags),
                "Method": method.upper(),
                "Path": path,
                "Summary": summary,
                "Description": description,
                "OperationId": operation_id,
                "Deprecated": "true" if deprecated else "false",
                "Auth (security)": json.dumps(security) if security else "",
                "Parameters": params_joined,
                "RequestBody": req_body,
                "Responses": status_codes
            })


    # sort for readability
    rows.sort(key=lambda r: (r["API Group (tags)"], r["Path"], r["Method"]))


    # write CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "API Group (tags)", "Method", "Path", "Summary", "Description", "OperationId",
            "Deprecated", "Auth (security)", "Parameters", "RequestBody", "Responses"
        ])
        writer.writeheader()
        writer.writerows(rows)

    # Print a short summary to stdout
    print(f"Wrote {len(rows)} endpoints to {output_file}")
    if servers:
        print("Server URLs: " + " | ".join(servers))
    print(f"Spec version: {version}")

if __name__ == "__main__":
    main()
