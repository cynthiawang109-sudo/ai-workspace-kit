# Publishing taskflow-doc-search

Version 0.1.0 has been published to PyPI. Version 0.1.1 publication is pending,
and `io.github.cynthiawang109-sudo/taskflow-doc-search` version 0.1.1 is listed
and active in the official MCP registry.

The project is licensed under MIT; see the root [LICENSE](../../LICENSE).
The distribution metadata in `pyproject.toml` declares `MIT`.

## One-time owner setup

1. Sign in to pypi.org and open
   [Publishing](https://pypi.org/manage/account/publishing/). Add a **pending
   publisher** using GitHub: project `taskflow-doc-search`, owner
   `cynthiawang109-sudo`, repository `ai-workspace-kit`, workflow filename
   `publish-doc-search.yml`, environment `pypi`.
2. Create the GitHub repository environment `pypi`. Configure release branch/tag
   restrictions and any required reviewers appropriate for the repository.
   The environment name must exactly match the PyPI publisher configuration.

The [Trusted Publishing workflow](../../.github/workflows/publish-doc-search.yml)
uses GitHub OIDC and `id-token: write` only in the publishing job. No PyPI API
tokens or stored credentials are needed. See the official
[PyPI Trusted Publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
The first successful upload creates the pending PyPI project.

## Local build and inspection

From `mcp/doc-search`, using a development virtual environment:

```sh
python -m pip install ".[dev]" build twine
python -m pytest -q
python -m build
python -m twine check dist/*
python -m zipfile -l dist/taskflow_doc_search-0.1.1-py3-none-any.whl
python -m tarfile -l dist/taskflow_doc_search-0.1.1.tar.gz
```

Inspect metadata for name, version, license, Python requirement, base dependency,
`embeddings` extra, README, and `taskflow-doc-search` entry point. Confirm both
archives contain `doc_search/`; the sdist must contain README and tests.
Install the wheel into a fresh virtual environment outside the checkout. From
outside the repository, set `AI_WORKSPACE_ROOT` to the absolute workspace path,
start `taskflow-doc-search`, and use an MCP client to initialize, list all six
tools, and call `search_docs` with a known corpus term. Run the included
client with the fresh environment's Python:

```sh
python /path/to/mcp/doc-search/scripts/smoke_installed.py /path/to/venv/bin/taskflow-doc-search /path/to/workspace
```

On Windows the executable is `venv/Scripts/taskflow-doc-search.exe`.
The client checks all six advertised tools and calls the five read-only tools;
its embeddings call uses an empty-token query, avoiding downloads and cache
changes. Embeddings ranking itself is covered by the unit tests with a fake
embedder. No model download is required for keyword search. Remove the
temporary environment and build output.

## Cut a release

1. Update the version in `pyproject.toml` and both version fields in
   `server.json`; complete the local checks above and merge the approved change.
2. Create a version tag on the intended commit (for example
   `doc-search-v0.1.1`) and **publish a GitHub Release** for it.
3. The workflow runs tests, builds and checks sdist/wheel, then publishes via
   OIDC after any environment review. Inspect the workflow and PyPI files.
   Ordinary pushes do not publish. Any published GitHub Release triggers this
   workflow, so coordinate releases for other workspace components accordingly.
4. `workflow_dispatch` is an explicit manual publishing path for the selected
   ref; it runs the same checks. Use only for a version not already uploaded:
   PyPI does not permit replacing an existing release file.

## Optional MCP registry listing

After PyPI publication, validate the included [server.json](server.json) against
its pinned schema and follow the official
[MCP registry publishing instructions](https://github.com/modelcontextprotocol/registry/tree/main/docs).
Authenticate ownership of `io.github.cynthiawang109-sudo`, confirm the package
README's `mcp-name` ownership marker, and publish with the registry publisher.
The manifest describes PyPI installation using `uvx`, stdio transport, and the
required workspace environment variable. Its publisher metadata records that
`io.github.cynthiawang109-sudo/taskflow-doc-search` is published in the MCP
registry at version 0.1.1; the listing is active.
Registry listing is separate from the PyPI workflow and is not automatic.
