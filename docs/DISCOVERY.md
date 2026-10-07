# Search and agent discovery

Mesh Workbench publishes a crawlable documentation site at https://shakystar.github.io/mesh-workbench/ and a public source repository at https://github.com/shakystar/mesh-workbench . Search engines decide whether and when to index or rank these pages; deployment is not an indexing confirmation.

## Implemented

- A descriptive repository title, description and Blender/modeling/agent topics.
- Static HTML documentation with real text links, page titles, canonical URLs, social preview metadata and SoftwareSourceCode structured data matching the visible project.
- A [sitemap](https://shakystar.github.io/mesh-workbench/sitemap.xml) for the published HTML pages.
- Raw Markdown alongside HTML, [llms.txt](../llms.txt), a [descriptive tool manifest](../tool-manifest.json), and an [agent quickstart](AGENT_QUICKSTART.md) with actual commands and failure behavior.
- MIT license and contribution workflow, documented dependency boundaries and measured modeling examples.

These changes help tools discover and understand the project. `llms.txt` is an optional documentation convention, not a search ranking switch. `tool-manifest.json` is project metadata, not an MCP registry registration. No public MCP endpoint or PyPI package publication is claimed.

## Indexing follow-up

Verified on 2026-10-07: the URL-prefix property `https://shakystar.github.io/mesh-workbench/` is owned and verified through the homepage HTML meta tag. Keep that public tag in `scripts/build_docs.py`; removing it can invalidate ownership. No account credentials are stored in this repository.

The sitemap submission was accepted, and the homepage plus agent quickstart were added to Google's priority crawl queue through URL Inspection. These are accepted requests, not completed indexing.

The Sitemaps report still displays **Could not fetch**, with 0 discovered pages, after one resubmission. Independent HTTP requests return 200/application/xml and parse 21 in-scope URLs. Google's own live URL test of the sitemap at 2026-10-07 14:51 KST reports crawling allowed, page fetch successful and indexing allowed. The live fetch and Sitemaps processing status are separate observations; the report error is not claimed resolved. No site-side cause was established, and no access restrictions were weakened.

Next verification: inspect the Sitemaps processing result and indexed status after Google recrawls. Repeated indexing requests do not improve queue priority. See [Google's sitemap fetch troubleshooting](https://support.google.com/webmasters/answer/7451001?hl=en). Search rankings and AI citations remain unverified. A compact [registration record](audits/SEARCH_DISCOVERY.json) preserves these boundaries.

This is a GitHub Pages project site. A `robots.txt` in `/mesh-workbench/` would not control crawlers for the host root, so the project does not pretend to configure root crawler policy. If host-wide crawler controls are needed, manage them at the owning `shakystar.github.io` site. Public project pages use `index,follow` metadata.

## Maintain

Edit the source Markdown, then `python -m pip install -r requirements-docs.txt` and `python scripts/build_docs.py --output runs/site`. The builder preserves raw Markdown and checks internal published links. The Documentation workflow builds and deploys the site after pushes to main. Keep the agent guide, manifest, examples and verified status consistent when runtime capabilities change.

References: [GitHub topics](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics), [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [Google AI search guidance](https://developers.google.com/search/docs/appearance/ai-features), [llms.txt proposal](https://llmstxt.org/).
