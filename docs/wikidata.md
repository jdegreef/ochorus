# Ochorus on Wikidata: "full work available at URL" (P953)

Wikidata has a property for exactly what Ochorus offers: **P953, "full work
available at URL"**, a link from a *work's* item (say *The Pilgrim's Progress*,
Q268211) to a place its full text can be read for free. Search engines and
library tools read Wikidata, and the links matter most in languages where
Ochorus may have the only free text (Luganda, Swahili, Amharic).

Nothing in the repo edits Wikidata. `backend/scripts/wikidata_p953.py` writes
a QuickStatements batch, and **you** review it and submit it from your own
Wikidata account.

## What the batch says

Each line adds one P953 statement for one language edition:

```
Q268211	P953	"https://ochorus.com/sw/books/pilgrims-progress/"	P407	Q7838	P1476	sw:"Safari ya Msafiri"
```

- **P953**: the edition's book page on ochorus.com. It is a plain URL with no
  tracking parameters.
- **P407** (language of work or name): the edition's language, given as its
  Wikidata item.
- **P1476** (title): the edition's title, in its own language. It is left out
  when the title contains a double quote, which QuickStatements cannot escape.

The script includes a work only when all of these hold:

- It is **public domain**, judged by the same rule the site uses for its
  JSON-LD license (`library/rights.py`). This leaves out the Ochorus Originals
  and works shared by permission.
- It is **the work itself**. Young-reader retellings (`-children`, `-teens`)
  and the Modern English edition are the house's own books, not editions of
  the work, so they are left out.
- The edition is **published**.
- The work is **matched to its Wikidata item** in
  `backend/scripts/wikidata_works.json` (slug → QID). The QID must be the
  *work*, never an "edition or translation" item (Q3331189). Wikidata keeps
  editions as separate items, and P953 belongs on the work.

## Running it

```
cd backend
uv run python scripts/wikidata_p953.py --check-live > /tmp/p953.tsv   # only URLs answering 200
uv run python scripts/wikidata_p953.py --unmapped                      # works still without a QID
```

Always use `--check-live` for a batch you will submit. It fetches each URL and
keeps only the ones that answer 200, so a language page that has not been
built yet cannot be linked.

## Reviewing and submitting

1. Open a few lines' QIDs on wikidata.org and check that each is the right
   *work*: right title, right author, an item for the work and not an edition.
   Fix or delete wrong rows in `wikidata_works.json` and run the script again.
2. Check the items do not already carry an ochorus.com P953. QuickStatements
   adds a duplicate value happily, so a second run of the same batch would
   double every link. Keep the batches you submit, and submit only new lines
   next time. `--only <slug> …` limits a run to particular works.
3. Go to <https://quickstatements.toolforge.org/>, log in with your Wikidata
   account, choose **New batch**, paste the file, and choose **Import V1
   commands**.
4. Read the preview, then **Run**. For a first batch, run 5 to 10 lines and
   look at the edited items before you run the rest.

## Etiquette

- **One URL per language edition**, on the work's item. Do not add the same
  URL to edition items, author items, or several works.
- **No promotional statements.** Add only P953 with its language and title.
  Do not add descriptions, "content deliverer" or sponsor claims, a new item
  for Ochorus itself, or links to anything that is not the full text.
- Link only what is **free and complete**. A page that needs an account, shows
  an excerpt, or might go away does not belong.
- Batch edits are visible under your account. If an editor questions or
  reverts one, reply on their talk page and do not re-add it. The Wikidata
  community can decline links, and that is fine.
- For large runs (hundreds of edits), it is courteous to mention the batch at
  [Wikidata:Project chat](https://www.wikidata.org/wiki/Wikidata:Project_chat)
  first.

## Growing the mapping

`--unmapped` lists the eligible works that have no QID yet, with their
languages. For each one, find the work's item. Search by title and check
"author" (P50) and "instance of" (P31: a literary or written work, not
"version, edition or translation"). Then add `"slug": "Q…"` to
`wikidata_works.json`. A work with no item on Wikidata is left out, so don't
create items just to hang a link on.
