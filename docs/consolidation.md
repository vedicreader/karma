# kosha's part in the search consolidation

Full review and roadmap: [`litesearch/docs/consolidation.md`](https://github.com/Karthik777/litesearch/blob/main/docs/consolidation.md).

The split being enforced: **litesearch owns retrieval, kosha owns everything that mentions a
function, a file path or a symbol.** Anything in kosha that would read the same on a corpus of
PDFs belongs one layer down.

## Landed

Nothing from the location-first query set. `anchor` / `similar` / `peers` / `code_clusters` were
specced here and wired up as MCP tools, but never implemented on `Kosha` — the tools raised
`AttributeError` on call. They have been removed from `mcp.py` and `SKILL.md` rather than left
as a promise. Retrieval consolidation continues below.

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
