# They Were Young: series outline

True stories for readers aged 13–17 (Ochorus Originals) of people whose faith began, or was tested, while they were teenagers. It sits between *Brave for God* (ages 8–12, a few hundred words a life) and *Portraits of Courage* (adults, book-length). The verse is 1 Timothy 4:12: "Let no one despise your youth."

The manuscripts in this folder (`they-were-young-<n>.md`) are the source of truth; `build_they_were_young` converts them (the same closed Markdown subset as the 30-day devotionals, parsed by `build_rooted.parse`).

## The series at a glance

Four books of six stories, each themed by the kind of crisis the person met young. All four are published.

| Book | Theme | People |
|---|---|---|
| 1 · Called | meeting God young | Spurgeon, Samson Occom, Robert Murray M'Cheyne, Billy Graham, Kanzo Uchimura, Richard Allen |
| 2 · Tested | faith under pressure | Patrick, Josephine Bakhita, Perpetua, the Uganda Martyrs, John Newton, Sundar Singh |
| 3 · Questions | doubt and the mind | Augustine, Pascal, Isaac Watts, Jonathan Edwards, C. S. Lewis, Bonhoeffer |
| 4 · Sent | doing something young | David Brainerd, William Carey, Mary Jones, Amy Carmichael, Eric Liddell, Jim Elliot |

Some *Brave for God* people return (Sundar Singh, Mary Jones, Carey, Elliot, Liddell), told for their teenage years, not retold.

## Format

- **Each volume:** an Introduction and six stories (`check_shape`); each story 2,500–3,500 words (the build refuses one under 2,000).
- **Each story:** opens on the decisive teenage scene, spends most of its length on the teenage years, then sweeps the rest of the life briefly. It ends with `### In Their Own Words` (one short, well-attested quotation with its source), `### Think It Through` (four discussion questions) and `### Read More on Ochorus` (the person's books, sermons and author-page biography; where the library has none of their writing, it says so).

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

## Book 2 — Tested

| Ch | Story | The test |
|---|---|---|
| 1 | Introduction: When Faith Is Tested | |
| 2 | Patrick: The Slave Who Prayed in the Snow | kidnapped from Britain at 16, six years enslaved in Ireland (5th century) |
| 3 | Josephine Bakhita: The Girl Who Said No | enslaved as a child in Sudan (c. 1877); chose freedom in Venice, 1889 |
| 4 | Perpetua: What a Thing Is Called | Carthage, 203, about 22: her prison diary and martyrdom |
| 5 | The Uganda Martyrs: Singing on the Road to Namugongo | the pages of Kabaka Mwanga, 1885–87; Namugongo, 3 June 1886 |
| 6 | John Newton: The Storm That Would Not Let Him Go | pressed into the navy at 18; the Greyhound storm, March 1748, aged 22 |
| 7 | Sadhu Sundar Singh: The Boy Who Waited for the Train | burned a Bible at 15; the vision, December 1904 |

### Book 2 notes for checking

- **Quotations from memory of old translations:** Patrick's *Confession* (N. J. D. White, 1905) and *The Passion of Perpetua and Felicity* (R. E. Wallis, 1885) are quoted in short phrases marked "in an old English translation"; none of these sources is in the library or was reachable to check word for word.
- **Traditions, not documents:** Joseph Mukasa's forgiveness of Mwanga and Hannington's "purchased the road" are given as reported by witnesses.
- **Bakhita's 1889 freedom** was a ruling by the King's Procurator, not a court; the text says "the authorities".
- **Uganda numbers** vary by source (22 Catholic and 23 Anglican martyrs are the usual counts; more died); the story says so.
- **Legends named as legends:** Patrick and the snakes and the shamrock; the disputed Tibet stories about Sundar Singh.
- **Newton** went on in the slave trade for years after his conversion; the story says so plainly.

## Book 3 — Questions

| Ch | Story | The question |
|---|---|---|
| 1 | Introduction: When Faith Asks Questions | |
| 2 | Augustine: The Restless Heart | the pears at 15–16, Carthage, Cicero's *Hortensius* at 18; the Milan garden, 386 |
| 3 | Blaise Pascal: The Boy Who Wanted Reasons | the prodigy; the calculating machine; the 1646 turn at 23; the Memorial, 1654 |
| 4 | Isaac Watts: Something Better to Sing | conviction in 1688 and trust in Christ in 1689, about 15; the hymns |
| 5 | Jonathan Edwards: The Doctrine He Hated | Yale at 13; 1 Timothy 1:17, probably 1721, about 17; the Resolutions at 19–20 |
| 6 | C. S. Lewis: The Boy Who Learned to Argue | lost faith at school; Kirkpatrick from 1914 at 15; the trenches at 19; Christ in 1931 |
| 7 | Dietrich Bonhoeffer: The Boy Who Chose the Church | Walter's death, 1918; theology at 14; Harlem 1930–31; Flossenbürg, 1945 |

### Book 3 notes for checking

- **Quotations checked word for word** against the library: Augustine's *Confessions* (Pusey), Pascal's *Pensées* and Gilberte Périer's *Life of Blaise Pascal* (still `ai_unreviewed`), Watts's *Divine Songs for Children*, and Edwards's sermon "A Divine and Supernatural Light". Works not in the library (Pascal's Memorial, Edwards's *Personal Narrative* and *Resolutions*, "When I Survey", Lewis's *Surprised by Joy*, Bonhoeffer's *The Cost of Discipleship*) are quoted only in short, famous lines; Lewis and Bonhoeffer, in copyright, a sentence each at most.
- **Traditions, not documents:** Watts being told to write better hymns; Pascal and the charcoal geometry (may have grown in the telling); the Bonhoeffer "then I shall reform it" story (family memory via Bethge).
- **Dates hedged in the text:** Augustine's ages (his own "sixteenth year" counting); Pascal's machine (18 or 19); Edwards's 1 Timothy moment (undated in the *Personal Narrative*); Lewis's theism (1929 by his account, 1930 by McGrath).
- **Library text slips found and fixed with this book:** `confessions` Book III read "unworthy to he compared" (now "be"); Bonhoeffer's author bio, its translations and *The Key Teachings of Dietrich Bonhoeffer* said he died "six days" or "a few days" before Flossenbürg was liberated (now "two weeks": 9 April and 23 April 1945).

## Book 4 — Sent

| Ch | Story | The sending |
|---|---|---|
| 1 | Introduction: Too Young to Be Sent? | |
| 2 | David Brainerd: Light in a Dark Thick Grove | converted July 1739 at 21; expelled from Yale; Kaunaumeek, the Forks, Crossweeksung 1743–46; died 1747 |
| 3 | William Carey: The Apprentice Who Lost an Argument | shoemaker's apprentice at 14; converted 1779 at 17; the *Enquiry* and Nottingham sermon, 1792; India, 1793 |
| 4 | Mary Jones: The Long Road to Bala | the walk to Thomas Charles, 1800, at about 15; the Bible Society, 1804 |
| 5 | Amy Carmichael: What Will Last | the rainy Sunday, about 1885, at about 17; the shawlies; India, 1895 |
| 6 | Eric Liddell: The Race He Would Not Run | Paris, July 1924, at 22; China from 1925; Weihsien, 1945 |
| 7 | Jim Elliot: The Man Who Would Not Keep His Life | the journal, 28 October 1949, at 22; Ecuador; January 1956 |

### Book 4 notes for checking

- **Quotations checked word for word** against the library: *The Life and Diary of David Brainerd* (including Edwards's narration), Amy Carmichael's *Things as They Are*, and Carey's epitaph as given in *Morning by Morning* (29 August). Carmichael's *If* is copyright-blocked and is neither quoted nor named. Liddell and Elliot (20th century) get one line each: Liddell's last words as remembered by the camp nurse, and Elliot's journal line in its original "that which" form.
- **From memory, worth checking against a copy:** the opening sentence of Carey's *Enquiry* (1792); Carey's "I can plod" (Eustace Carey's *Memoir*, 1836); Mary Jones's inscription (transcriptions differ); Joseph Hughes's "If for Wales…" (Bible Society wording).
- **Traditions named as traditions:** Carey's leather globe and map, "sit down, young man" and "hold the ropes"; "Expect great things… from God / for God" (the from/for wording added later); Mary Jones's barefoot walk and other details first printed in 1878–82; *Chariots of Fire*'s changes (Liddell knew of the Sunday heats months ahead; "I feel His pleasure" was written for the film).
- **Library slips found and fixed with this book:** *Brave for God: Book Two* gave the film's "I feel His pleasure" as Liddell's own words and called his 400 m time a world record (now a plain statement of his belief, and an Olympic record, in English and all six translations). Jim Elliot's author bio placed the journal line "at Wheaton" (now "a few months after he graduated", in English and Spanish) and quoted it as "gain what he cannot lose" (now the journal's "that which").

## Building a volume

```bash
DJANGO_DEBUG=true uv run python manage.py build_they_were_young <n>
```

`VOLUMES[n]` holds the book's fields. Then serialize the fixture, run `generate_covers <slug>` and `npm run og:covers`, and add the book to the For Teens shelf in `topic_seed.py`.
