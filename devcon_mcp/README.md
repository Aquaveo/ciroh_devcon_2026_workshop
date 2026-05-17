# DevCon 2026 — MCP Server Workshop

In this workshop you build a small MCP (Model Context Protocol) server that
exposes NRDS hydrology data to an LLM. You will write **eight lines of code**
spread across three files. Everything else is already wired for you.

## What is MCP

MCP is a protocol that lets an LLM talk to **tools** (functions it can call)
and **prompts** (reusable instruction templates). Your MCP server publishes a
schema; the LLM reads it; the LLM picks tools and fills in arguments.

This workshop server publishes:
- 2 tools to list / query NRDS parquet+netcdf output files on S3
- 2 prompt templates — one to list files for a selector, one to run a query
  against a selected file

## File map

| File | What it does | Do you edit it? |
|---|---|---|
| `engine.py` | Creates the FastMCP instance + `/health` route | **No** |
| `server.py` | Boots the server, configures logging + CORS | **No** |
| `validations.py` | Pydantic `Literal` types + hint strings (the LLM-visible enum surface) | **No** |
| `_helpers.py` | S3 + DuckDB + date plumbing | **No** |
| `logic.py` | **Challenge 1** — data-shaping logic | **Yes** |
| `tools.py` | **Challenge 2** — MCP tool wiring | **Yes** |
| `prompts.py` | **Challenge 3** — prompt template | **Yes** |

## Run the server

```bash
python -m devcon_mcp.server
```

Confirm it is up:

```bash
curl http://localhost:9003/health
# -> {"status":"ok"}
```

The MCP endpoint itself is at `http://localhost:9003/mcp` (Streamable HTTP).

**Watch the terminal where the server is running** — each tool call prints a
log line, and the data-layer code prints what S3 returned before Challenge 1A's
shaping runs. When something doesn't feel right, this is the first place to look:

- *Did the LLM hit my tool?* → look for `Tool ... called` lines (from `tools.py`).
- *Did S3 actually return files?* → look for `S3 listing returned N raw paths`
  (from `logic.py`, just before Challenge 1A).
- *Did my selector resolve a file?* → look for `query_output_file_from_output_selector`
  followed by a downstream DuckDB log line.

## The three challenges

### Challenge 1 — Data-shaping logic (`logic.py`)

**1A.** In `list_available_output_files`, the S3 `ls` call gives you a flat
list of file URLs. Sort them and shape them into the `{"name": ..., "path": ...}`
records the tool returns. Look for the `=== CHALLENGE 1A ===` banner.

**1B.** In `query_output_file_from_output_selector`, resolve the selected file
with `get_output_file(...)`, then run the query against it with
`query_output_file(...)`. Look for the `=== CHALLENGE 1B ===` banner.

### Challenge 2 — Tool wiring (`tools.py`)

Each `@mcp.tool` decorated function already has its argument schema declared.
Your job is to call the matching logic function and return the result. Look
for the `=== CHALLENGE 2 (part A) ===` and `=== CHALLENGE 2 (part B) ===`
banners.

### Challenge 3 — Prompt template, list variant (`prompts.py`)

Return an f-string that asks the LLM to list output files for the given
selector arguments. Look for the `=== CHALLENGE 3 ===` banner.

### Challenge 4 — Prompt template, query variant (`prompts.py`)

Return an f-string that asks the LLM to run a DuckDB SQL query against the
output file selected by the given selector arguments. Look for the
`=== CHALLENGE 4 ===` banner.

---

## Answers

Open these only if you are stuck.

### 1A — `logic.py::list_available_output_files`

Replace `items=[]` with:

```python
files = sorted(files)
items = [{"name": f.split("/")[-1], "path": f} for f in files]
```

### 1B — `logic.py::query_output_file_from_output_selector`

Replace the placeholder body with:

```python
resolved = get_output_file(
    configuration=configuration, date=date, forecast=forecast,
    cycle=cycle, vpu=vpu, ensemble=ensemble,
    file_name=file_name, index=None if file_name else (index or 0),
)
if not resolved.get("ok"):
    return resolved
return query_output_file(s3_url=resolved["selected"]["path"], query=query)
```

### 2 — `tools.py` (both tool bodies)

For `list_available_output_files_tool`:

```python
return list_available_output_files(
    configuration=configuration, date=date, forecast=forecast,
    cycle=cycle, vpu=vpu, ensemble=ensemble,
)
```

For `query_output_file_from_output_selector_tool`:

```python
return query_output_file_from_output_selector(
    configuration=configuration, date=date, forecast=forecast,
    cycle=cycle, vpu=vpu, query=query,
    ensemble=ensemble, file_name=file_name, index=index,
)
```

### 3 — `prompts.py::list_output_files`

Replace the placeholder return with:

```python
return (
    f"List the available output files for the {configuration} configuration "
    f"on {date}, {forecast} forecast, cycle {cycle}, vpu {vpu}."
)
```

### 4 — `prompts.py::query_output_file`

Replace the placeholder return with:

```python
return (
    
    f"Run the DuckDB query `{query}` against the output file for the "
    f"{configuration} configuration on {date}, {forecast} forecast, "
    f"cycle {cycle}, vpu {vpu}."
)
```