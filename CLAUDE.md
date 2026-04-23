# LLM Wiki Schema & Conventions

This document defines the rules and workflows for building and maintaining the **LLM Wiki**—a persistent, synthesized knowledge base in the `Obsidian/Uio_Telescopio/` vault.

## Directory Structure
- `raw/`: Immutable source documents (DOCX, PDF, Articles).
- `wiki/`: LLM-generated markdown files.
- `wiki/index.md`: Catalog of all pages.
- `wiki/log.md`: Chronological log of operations.

## Core Operations

### 1. Ingest
Process a new source from `raw/` into the wiki.
- **Read**: Extract text from the source.
- **Discuss**: Share key takeaways with the user.
- **Synthesize**: Update existing entity/concept pages or create new ones.
- **Link**: Ensure all new content is interlinked within the wiki.
- **Update Metadata**: All wiki pages MUST include YAML frontmatter.
- **Record**: Append an entry to `log.md` and update `index.md`.

### 2. Query
Answer questions using the wiki as the primary source of truth.
- **Search**: Reference `index.md` to find relevant pages.
- **Respond**: Synthesize an answer with citations to both wiki pages and raw sources.
- **Compound**: If an answer is valuable, file it back into the wiki as a new page.

### 3. Lint
Periodic health check of the wiki.
- **Contradictions**: Find and flag conflicting information.
- **Orphans**: Identify pages with no inbound links.
- **Data Gaps**: Suggest new questions or searches based on missing information.

## Style Guidelines
- **Markdown**: Use standard GFM.
- **Internal Links**: Use `[[Page Name]]` syntax (Obsidian style).
- **Metadata**: Every page must have:
```yaml
---
type: [entity|concept|summary|analysis]
tags: [uic, radiotelescopio, project]
created: {{date}}
sources: [Link to raw source]
---
```
- **Structure**: Use hierarchical headings (H1 for title, H2 for sections).

## Ingestion Workflow (One-by-One)
1. User drops file in `raw/`.
2. LLM reads and proposes updates.
3. User confirms/refines.
4. LLM applies edits across multiple files.
5. LLM updates index and logs the ingestion.
