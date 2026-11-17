# Instructions for AI agents working in this repository

## Attribution

No output written to this repository or to GitHub may mention the AI tool,
its maker or its model in any form: no co-author or other trailers naming
them, no "generated with" lines, no session links, in commits, PR titles and
bodies, issues, comments, review replies or release notes. Write the
substantive summary only.

## Writing style

Never use an em-dash or an en-dash as punctuation, in any file, commit or
comment. Rewrite the sentence with commas, a colon, a semicolon or two
sentences.

## Evidence and licences

- No page text in the repository: no quotation and no close paraphrase.
  Evidence holds facts (numbers, codes, names) and page addresses only, and
  `note` fields are the researcher's own words.
- A figure from a lead list, a cite-only domain or a never domain never
  ships. Lead lists are never written to the repository.
- A domain whose terms forbid copying or reuse goes on the `never` list.
  Every new domain is ruled by the maintainer once.
- The catalogue is ODbL. A source whose terms forbid redistribution
  contributes nothing; the four own-terms sources stay apart from the ODbL
  database (see LICENSE-DATA.md).
- An entry that fails `research/check.py` is fixed or dropped, never forced.

## Research runs

Research runs follow the skill in `.agents/skills/research-sites/`
(`SKILL.md`, with `region-brief.md` for each region's agent and
`second-pass.md` for the independent check).

## Working

- Python 3.14, standard library only. Any network request sends
  `User-Agent: dive-site-harvester/1.0` and nothing naming a person or the
  project.
- Run `python3.14 pipeline/run_tests.py` and `python3.14 research/check.py`
  before committing.
- Stage explicit paths. Commit only when asked.
