# They Were Young: series outline

True stories for readers aged 13–17 (Ochorus Originals) of people whose faith began, or was tested, while they were teenagers. It sits between *Brave for God* (ages 8–12, a few hundred words a life) and *Portraits of Courage* (adults, book-length). The verse is 1 Timothy 4:12: "Let no one despise your youth."

The manuscripts in this folder (`they-were-young-<n>.md`) are the source of truth; `build_they_were_young` converts them (the same closed Markdown subset as the 30-day devotionals, parsed by `build_rooted.parse`).

## The series at a glance

Four books of six stories, each themed by the kind of crisis the person met young. Books 1 and 2 first; 3 and 4 if the first two find readers.

| Book | Theme | People |
|---|---|---|
| 1 · Called | meeting God young | Spurgeon, Samson Occom, Robert Murray M'Cheyne, Billy Graham, Kanzo Uchimura, Richard Allen |
| 2 · Tested (planned) | faith under pressure | Patrick, Josephine Bakhita, Perpetua, the Uganda Martyrs, John Newton, Sundar Singh |
| 3 · Questions (planned) | doubt and the mind | Augustine, Pascal, C. S. Lewis, Jonathan Edwards, Bonhoeffer, Isaac Watts |
| 4 · Sent (planned) | doing something young | Mary Jones, Amy Carmichael, William Carey, David Brainerd, Jim Elliot, Eric Liddell |

Some *Brave for God* people return (Sundar Singh, Mary Jones, Carey, Elliot, Liddell), told for their teenage years, not retold.

## Format

- **Each volume:** an Introduction and six stories (`check_shape`); each story 2,500–3,500 words (the build refuses one under 2,000).
- **Each story:** opens on the decisive teenage scene, spends most of its length on the teenage years, then sweeps the rest of the life briefly. It ends with `### In Their Own Words` (one short, well-attested quotation with its source), `### Think It Through` (three discussion questions) and `### Read More on Ochorus` (the person's books, sermons and author-page biography; where the library has none of their writing, it says so).

## Accuracy rules

- No invented dialogue or events. Where the sources give only an outline, or disagree, the story says so in the text (e.g. Spurgeon's chapel and date, the preacher who reached Occom, Allen's undated conversion and freedom, Graham's exact age).
- Quotations are short and attributed. Twentieth-century subjects (Graham) get a sentence at most; the rest is paraphrase.
- Scripture is BSB, except where a story gives the words a person actually heard or read (Spurgeon's "Look unto me", Isaiah 45:22 KJV), which keep their historical wording and are marked as such.

## Book 1 — Called

| Ch | Story | Teenage turning point |
|---|---|---|
| 1 | Introduction: Before You Were Grown | |
| 2 | Charles Spurgeon: The Boy Who Looked | Colchester, January 1850, aged 15 |
| 3 | Samson Occom: The Boy Who Taught Himself to Read | Mohegan, the Great Awakening, c. 1740–41, about 16–17 |
| 4 | Robert Murray M'Cheyne: A Brother Who Cannot Die | Edinburgh, his brother David's death, July 1831, aged 18 |
| 5 | Billy Graham: The Boy Who Hid in the Choir | Charlotte, the Mordecai Ham meetings, autumn 1934, about 16 |
| 6 | Kanzo Uchimura: The Boy Who Prayed Against God | Sapporo, the Covenant of Believers in Jesus, 1877, aged 16 |
| 7 | Richard Allen: The Night the Dungeon Shook | Delaware, enslaved, c. 1777, about 17 |

### Facts the writers flagged as less than certain (kept hedged or left out)

- **Spurgeon:** the exact date (6 January 1850) and the Artillery Street chapel, both questioned by some historians and hedged in the text.
- **Occom:** the preacher (Wheelock credits James Davenport; Occom names none), and his ages at conversion and at Wheelock's school.
- **M'Cheyne:** David's exact age at death (given as "in his twenties").
- **Graham:** whether he was 15 or just 16 that night (his birthday was 7 November).
- **Uchimura:** the cross became clear to him only at Amherst in 1886, which he called his real conversion; the story presents Sapporo and Amherst as one journey.
- **Allen:** the conversion and freedom dates, which he leaves blank, and the date of the St. George's gallery incident (1787 vs c. 1792).
- **Left out:** that Allen caught yellow fever (unconfirmed). The library's text of Allen's 1793 narrative reads "five hundred men" called in to bury the dead, where the original likely reads "five hired men". That may be an extraction slip in `life-experience-gospel-labours` worth an english-qa look; the story doesn't use it.

## Building a volume

```bash
DJANGO_DEBUG=true uv run python manage.py build_they_were_young <n>
```

`VOLUMES[n]` holds the book's fields. Then serialize the fixture, run `generate_covers <slug>` and `npm run og:covers`, and add the book to the For Teens shelf in `topic_seed.py`.
