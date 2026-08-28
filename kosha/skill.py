"""Search your repo and every installed package by meaning, then walk the call graph that connects them, reach for this before you grep, open a source file, or write code a dependency already provides. FTS5 keyword search, vector search and a static call graph over local SQLite: no LLM calls, no network, answers in milliseconds.

## Start here

`Kosha()` opens two SQLite stores, the repo index (`.kosha/code.db`) and the env index of installed packages (XDG `kosha/env.db`), plus the call graph over both. Check freshness before you trust an answer, because a stale index is indistinguishable from a missing result:

```python
from kosha import Kosha
k = Kosha()
k.status()
# {'files': 4, 'packages': 355, 'graph_nodes': 10630, 'stale_files': 0, 'stale_pkgs': 5, 'new_files': 0}
```

Sync only when something you actually need is stale, a full sync embeds every changed chunk and is the one slow operation here:

```python
k.sync(in_parallel=True)          # repo + stale packages + graph
k.sync(embed=False)               # rebuild the graph without re-embedding
k.sync(pkgs=['httpx'], repo=False)  # one package
```

Then query. `context` is the default and searches both stores; `env_context` and `repo_context` are the one-sided, faster versions:

```python
for r in k.env_context('atomic file write preserving permissions', limit=8):
    print(r['metadata']['mod_name'], r['metadata'].get('lineno'), r['content'][:120])
```

## Which call answers which question

| Question | Call |
|---|---|
| Is the index fresh? | `k.status()` |
| Does a dependency already do this? | `k.env_context('desc', limit=8)` |
| What pattern does this codebase use? | `k.context('desc', graph=True, limit=15)` |
| Repo only, no packages | `k.repo_context('desc')` |
| Triage many hits without full code bodies | `k.context('desc', compact=True)` |
| Who calls this, what does it call, what are its peers? | `k.ni('fastcore.basics.merge')` |
| How do two nodes connect? | `k.short_path('a.fn', 'b.fn')` |
| What's within n hops? | `k.neighbors('kosha.core.Kosha', depth=2)` |
| What does a package actually export? | `k.public_api('fastcore')` |
| What is load-bearing in a package? | `k.top_nodes('fastcore', k=5)` |
| How does package A reach package B? | `k.api_call_paths('kosha', 'litesearch')` |
| What does this project depend on, by coupling? | `k.dep_stack(depth=2)` |
| Where should new code go? | `k.where_to_add('desc', limit=5)` |
| Which package is for this job? | `k.pkg_context('desc')` |
| Search long-form docs, not code | `k.docs_context('desc')` |

`doc(Kosha)` lists every method with its signature, the table above is the map, not the API reference. Ingestion (`update_repo`, `update_pkgs`, `process_env`) and destructive calls (`nuke`, `rm_pkg`, `prune_old_pkgs`) are on the same class; `sync` is the only one worth calling directly.

## Filters

Filters live inside the query string, mixed with natural language, and apply to `context`, `env_context` and `repo_context`. Bare package names are auto-detected as `package:`, so `k.context('fastcore atomic save')` already scopes itself.

| Token | Aliases | Example | Effect |
|---|---|---|---|
| `package:` | `pkg:`, `packages:`, `pkgs:` | `package:fastcore` | one package |
| `path:` | `dir:`, `folder:`, `paths:` | `path:xtras` | path substring |
| `file:` | `filename:`, `files:` | `file:xtras*` | filename glob |
| `lang:` | `ext:`, `extension:`, `langs:` | `lang:py` | language by extension |
| `type:` | `types:` | `type:FunctionDef` | AST node type |

Values are comma-separated for OR (`package:httpx,requests`), and a trailing `!` (`package!:x`) parses to the same thing, every filter is already a hard SQL predicate. A `package:` filter turns repo search off, since the two can't both be what you meant.

A filter-shaped token with any other key is reported under `parseq(q)[1]['_unknown']`, and the CLI warns on stderr. This matters more than it looks: an unrecognised key isn't dropped, it's searched as text against every package, which returns a confident-looking page of results for a question nobody asked.

## Reading a result

```python
{'content':  'def merge(*ds):\n    "Merge all dicts"\n    ...',
 'metadata': {'mod_name': 'fastcore.basics.merge',   # the handle for ni() / short_path()
              'path': '.../fastcore/basics.py', 'lineno': 655,
              'type': 'FunctionDef', 'package': 'fastcore',
              'public_api': True, 'docstring': 'Merge all dicts'},
 'pagerank': 0.00027, 'in_degree': 8, 'out_degree': 12,
 'callers': [...], 'callees': [...], 'co_dispatched': []}
```

`pagerank` is blast radius: a high-pagerank node is load-bearing, so changing it ripples. `callers` tells you where to hook in upstream, `callees` what you can reuse below.

`co_dispatched` is the least obvious and often the most useful: functions assigned together in one list, dict or tuple at module level, route tables, handler maps, plugin registries. When you need to add another handler, this names its peers and where the registration lives, without reading the glue code.

The graph fields only appear when `graph=True` (the default for `context`); the search-only methods return `content` and `metadata` alone.

## The call graph

`k.graph` is the graph engine itself, built by pyan3 static analysis plus AST parsing for dynamic edges, and it holds more than the `Kosha` shortcuts expose, `k.graph.ranked(k=10, module='fastcore')`, `k.graph.callers`, `k.graph.file2nodes`, `k.graph.co_dispatched`. `doc(k.graph)` lists them.

Node names are the fully-qualified `mod_name` from a result's metadata. A name that isn't in the graph returns empty rather than raising, so an empty `short_path` means "no path found or node not indexed", check `k.ni(name)` before concluding the code doesn't connect.

## Long-form docs

The code stores hold AST chunks, which is the wrong shape for prose. `k.docs` is a tree-aware `litesearch.api.Index` over READMEs and docs directories, created lazily on first access:

```python
k.add_pkg_docs('fastcore')          # the full README, not the 2k-char blurb in pkg_context
k.add_docs('path/to/docs')          # a directory, a file, or {title: text}
k.docs_context('how do I install')  # ranked sections, each with a read handle
k.docs.read(node_id)['text']        # one whole section, reassembled
```

`docs_context(q, sections=False)` returns raw chunks instead. The docs index has no staleness tracking: re-ingesting upserts by content hash but won't evict a stale version.

## Reranking

`context`, `env_context`, `repo_context` and `pkg_context` take `rerank=True`, which reorders the results with a flashrank cross-encoder (the first call downloads a ~3MB model). It reorders what was retrieved and never adds to it, costing roughly 15-35ms.

It is off by default on purpose. On queries whose wording matches the target's docstring the gain is large; on paraphrased queries most of the loss is retrieval, not ordering, and the cross-encoder can't recover it. Widening the candidate pool first measures worse while costing linearly more, so `context` reranks only its existing top-k.

## Outside Python

The same index is reachable three other ways, which matters when the caller isn't a Python process:

- **CLI**, `kosha sync`, `kosha context 'query' --limit 10 --rerank`, `kosha ni <mod_name>`, `kosha public-api <pkg>`, `--as_json` on any of them.
- **Daemon**, `kosha daemon &` holds one warm embedding model and takes `{"cmd": ..., "args": {...}}` as JSON on stdin, which removes the few-second cold start from every call.
- **MCP**, `kosha-mcp` exposes the same operations as MCP tools over stdio. If the host already has it configured, call those instead of importing anything.

## The stores are litesearch databases

`k.codedb` and `k.envdb` are plain `litesearch.Database` objects, so the whole litesearch API works on them, extra tables, raw SQL, custom stores:

```python
list(k.envdb.q("select content from store where json_extract(metadata,'$.mod_name') = ?", ['fastcore.basics.merge']))
summaries = k.envdb.get_store(name='summaries')   # e.g. an agent-written layer over undocumented code
```

Embeddings are stored and read back as `float16`; `kosha.core.cast_emb` is what pins that, so a custom `efn` can't silently write a wider dtype.

Docs: https://vedicreader.github.io/kosha/skill.html.md"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/05_skill.ipynb.

# %% auto #0
__all__ = ['Kosha', 'CodeGraph', 'pkg_url']

# %% ../nbs/05_skill.ipynb #1a2b811a
import kosha.core, kosha.graph
from .core import Kosha, pkg_url
from .graph import CodeGraph
from pyskills import allow

# Read-only surface only: sync/update_*/nuke/rm_pkg write to disk, so allowing them is the host's call.
allow({Kosha: ['status', 'context', 'env_context', 'repo_context', 'pkg_context', 'docs_context',
               'public_api', 'top_nodes', 'api_call_paths', 'dep_stack', 'where_to_add',
               'pkgs_in_env', 'pkgs2consider'],
       CodeGraph: ['node_info', 'node_infos', 'callers', 'callees', 'co_dispatched', 'neighbors',
                   'short_path', 'short_paths', 'ranked', 'file2nodes']},
      pkg_url)

_all_ = ['Kosha', 'CodeGraph', 'pkg_url']
