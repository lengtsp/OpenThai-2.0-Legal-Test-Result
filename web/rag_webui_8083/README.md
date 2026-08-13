# RAG UI front end

This folder contains the browser interface used to inspect retrieval evidence,
citations and the comparison views in this experiment.

It intentionally contains only the front-end files: `index.html`, the two
stylesheets and a small service-worker compatibility file. It does not include
the legal corpus, benchmark artifacts, local paths, database files, runtime
logs, environment files or credentials.

The page calls relative `/api/...` routes. To use it as a live RAG interface,
serve it alongside a compatible local backend. Opening it with a static server
is still useful for viewing the layout, but search and chat require that API.

```bash
cd web/rag_webui_8083
python -m http.server 8083
```
