# kosha's part in the search consolidation

Full review and roadmap: [`litesearch/docs/consolidation.md`](https://github.com/Karthik777/litesearch/blob/main/docs/consolidation.md).

The split being enforced: **litesearch owns retrieval, kosha owns everything that mentions a
function, a file path or a symbol.** Anything in kosha that would read the same on a corpus of
PDFs belongs one layer down.

## Landed

Three queries that start from a **location** rather than a string — the question you have with a
file open — built on litesearch's new ANN primitives (`store.ann_neighbors`, `store.clusters`,
`store.peers`):

```python
k.anchor('src/app.py', 42)      # -> the code-store rowid covering that line
k.similar('src/app.py', 42)     # k-NN: what else looks like this
k.peers('src/app.py', 42)       # the cluster it belongs to: where else did we already do this
k.code_clusters(limit=20)       # a labelled map of the repo, for orienting
```

All three take `graph=True` to enrich hits with callers/callees/pagerank, and all three are also
MCP tools. `peers` and `code_clusters` return `method` and `note` — usearch refuses to cluster a
small index, and the k-NN fallback is a different answer that the caller should be able to name.

This replaces ~150 lines in `leela/search.py`, which reimplemented all of it directly against
`kosha.code_st` and its usearch index.

## Next

1. **Code trees** (`kosha.tree`). `litesearch.tree` builds a document tree from headings; code's
   tree is `package › module › class › function` and kosha already holds every piece of it
   (`mod_name`, `lineno`, `type`). Writing nodes from the AST into the same `nodes` schema makes
   `db.toc('litesearch')` print a package outline, `db.read()` return a whole class, and
   `db.sections()` roll code hits up to modules.
2. **Split `rank_results`.** The multi-chunk coherence boost, per-source saturation decay and
   top-k loop are generic and should move to litesearch. Symbol-query detection, identifier stem
   boosts, test/compat path penalties and package soft-boosts stay here.
3. **Better cluster labels for code.** c-TF-IDF on code names clusters after unique identifiers
   (`integrate_4, integrate_6, …`) because that is exactly what IDF rewards. Stripping numeric
   suffixes and preferring the shared stem is a tokeniser argument, not a new algorithm.
