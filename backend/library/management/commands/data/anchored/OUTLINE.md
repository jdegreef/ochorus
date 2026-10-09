# Anchored – 30 Days with God for Teens: series outline

House-written devotional books for readers aged 13–17 (Ochorus Originals), 30 days per book: the teen follow-on to *Rooted* (`../rooted/OUTLINE.md`, ages 9–12). Every Scripture is quoted from the Berean Standard Bible (BSB), which is public domain.

The day tables below are generated from the manuscripts in this folder (`anchored-<n>.md`), so they match what shipped. The manuscripts are the source of truth. If a day changes, regenerate the tables rather than editing them by hand.

## The series at a glance

The anchor is Hebrews 6:19: "We have this hope as an anchor for the soul, firm and secure."

| Book | Focus | Slug |
|---|---|---|
| 1 | Is It True? Who Am I? Honest questions and the God who answers them | `anchored-1` |
| 2 | Real Life: faith for the mind, the screen, the heart and the home | `anchored-2` |
| 3 | What Am I For? Calling, study and work, money, justice, sharing faith, leading, the church (planned) | `anchored-3` |

## Approach

- **Voice:** a 15-year-old addressed as an intelligent person. Hard questions get real reasons, not slogans; doubt is treated with respect (Book 1 opens with "Doubt Is Allowed"). Scenes are drawn from teen life in many countries, not one.
- **Mixed audience:** one series for everyone. *Sons of the King* and *Daughters of the King* already cover the gendered books for 9–12.
- **The gospel:** Book 1, Day 8 carries the clear invitation to trust Christ; the Conclusion repeats it gently.

## Format

- **Each day:** a title, the key passage (BSB), a teaching of about 400–550 words, **Think about it** / **Try this**, **Go deeper**, and a prayer.
- **Go deeper** points to ONE real chapter of a classic in the Ochorus library ("start with chapter 4, “Title”"), with a sentence that is true to that chapter. It is what makes the series an on-ramp to the library rather than a stand-alone devotional.
- **Each book:** an Introduction, Day 1–30 (in three parts of ten) and a Conclusion, so 32 chapters, the shape `build_rooted.check_shape` enforces.
- **Key verses** avoid the key verses of Rooted, Sons of the King and Daughters of the King, ranges included; where a natural verse was taken, the day uses another and quotes the familiar one inside the teaching. Book 1's swaps: Day 1 (John 20 → Mark 9:23–24), 6, 8 (John 14:6 → Acts 4:12), 11, 13–18, 20, 22–26, and Day 30, whose key passage is Hebrews 10:23 because the series' own Hebrews 6:19 sits inside a kids' range; 6:19 is quoted in the Introduction and in Day 30's teaching.

## Translations and Go deeper

Content has no English fallback, so a Go-deeper book that does not exist in a translation's language is a dead pointer there. A translated edition keeps the pointer only where that book has an edition in its language, and otherwise drops the Go-deeper line (or names a classic that does exist in that language). Several Book 1 picks are English-only today (e.g. *The Key Teachings of Derek Prince*, *The Person and Work of the Holy Spirit*).

## Sensitive days and how they were handled

| Book · Day | Topic | Approach |
|---|---|---|
| 1 · 6 | Suffering | Honest that the Bible gives no neat answer; if sadness won't lift, tell a trusted adult. |
| 1 · 9 | When God feels silent | Psalm 13; carries the full line: if you ever think about hurting yourself or not wanting to be alive, tell a parent or trusted adult right away. |
| 1 · 16 | Anxiety | Normal, not a failure of faith; practical help; getting help from a doctor or counsellor is fine; the self-harm line, bolded. No hotline numbers (global readership). |
| 1 · 17 | Loneliness | Trusted-adult line if loneliness becomes deep sadness. |
| 1 · 19 | Adopted | For readers with hard fathers: if anyone at home makes you feel unsafe, tell a trusted adult. |
| 1 · 24 | Purity | Pornography named once, plainly and without description; sex belongs within marriage; body-safety line bolded (pressure, requests for pictures, wrong touch: not your fault, tell a trusted adult). |
| 1 · 27 | Parents | Every family looks different; honour never means keeping a secret about being hurt; what to do if a parent asks for something clearly wrong (Ephesians 6:4 quoted too). |

Book 2's sensitive days:

| Book · Day | Topic | Approach |
|---|---|---|
| 2 · 3–4 | Panic, intrusive thoughts | Normal and treatable; see a doctor; the bolded self-harm line. |
| 2 · 9 | Body image | No numbers, weights or diet talk; if eating, food or exercise feels out of control, tell an adult and see a doctor; body-safety line. |
| 2 · 13 | Games | A stranger in a game who asks for details or pictures, or offers gifts: tell an adult. |
| 2 · 14 | Cyberbullying | Not your fault; don't retaliate; save evidence; block and report; tell a trusted adult; bolded line on threats or shared images; a word for bystanders. |
| 2 · 16–18 | Crushes, dating, breakups | Families and cultures differ, so honour your parents' rules; no one may pressure you; never send pictures; an adult's romantic interest is not romance and must be reported; body-safety and self-harm lines. No second purity lesson (Book 1 Day 24 has it). |
| 2 · 22 | Parents splitting up | Not your fault; you don't have to choose sides; safety in both homes; self-harm line. |
| 2 · 24 | Forgiving | Forgiveness never means staying somewhere unsafe or keeping a harmful secret (bolded). |
| 2 · 26 | Grief | No timetable; not your fault; self-harm line; on a loved one who may not have believed: "God knew them completely, and He is more just and more merciful than any of us." |
| 2 · 28 | Shame | A secret about what someone did TO you is not your shame; tell a trusted adult. |

## Building a volume

```bash
DJANGO_DEBUG=true uv run python manage.py build_rooted <n> --series anchored
```

`ANCHORED[n]` (in `SERIES` in `build_rooted.py`) holds the book's fields, including its own `attribution`. Then serialize the fixture, run `generate_covers <slug>` and `npm run og:covers`, and add the book to the For Teens shelf in `topic_seed.py`. Check every verse against the BSB, including short quotes inside the teachings, and re-read each Go-deeper chapter.

---

## Book 1 — Is It True? Who Am I?

*Is It True? Who Am I? Honest questions and the God who answers them*

Introduction: Welcome to Anchored

**Part 1 · Is It True?**

| Day | Title | Scripture | Go deeper |
|---|---|---|---|
| 1 | Doubt Is Allowed | Mark 9:23–24 | *Orthodoxy*, ch. 2 |
| 2 | Is There a God? | Romans 1:19–20 | *Pensées*, ch. 3 |
| 3 | Can I Trust the Bible? | 2 Timothy 3:16–17 | *The Key Teachings of Derek Prince*, ch. 2 |
| 4 | Was Jesus Real? | Luke 1:1–4 | *The Everlasting Man*, ch. 12 |
| 5 | Did He Really Rise? | 1 Corinthians 15:3–8 | *On the Incarnation*, ch. 30 |
| 6 | Why Does God Allow Suffering? | Romans 8:18, 22 | *The God of All Comfort*, ch. 7 |
| 7 | Faith and Science | Psalm 19:1–4 | *The Key Teachings of C. S. Lewis*, ch. 15 |
| 8 | Is Jesus the Only Way? | Acts 4:12 | *The Way to God*, ch. 5 |
| 9 | When God Feels Silent | Psalm 13:1–2, 5–6 | *Grace Abounding to the Chief of Sinners*, ch. 3 |
| 10 | Faith Is Not a Feeling | Hebrews 11:1 | *The Christian's Secret of a Happy Life*, ch. 7 |

**Part 2 · Who Am I?**

| Day | Title | Scripture | Go deeper |
|---|---|---|---|
| 11 | Made in His Image | Psalm 8:3–5 | *Confessions*, ch. 1 |
| 12 | Known Completely | Psalm 139:1–4 | *Morning by Morning*, ch. 2 |
| 13 | The Real You and Your Feed | John 5:44 | *The Pursuit of God*, ch. 11 |
| 14 | The Comparison Trap | 2 Corinthians 10:12 | *Humility*, ch. 6 |
| 15 | When You've Blown It | Luke 22:31–32 | *The Bruised Reed*, ch. 3 |
| 16 | Anxious | Isaiah 26:3–4 | *The Life of Trust (For Teens)*, ch. 9 |
| 17 | Lonely | Psalm 25:16–17 | *The Practice of the Presence of God*, ch. 1 |
| 18 | You Belong Somewhere | Ephesians 2:19, 22 | *The Body of Christ (For Teens)*, ch. 2 |
| 19 | Adopted | Romans 8:15–16 | *The Person and Work of the Holy Spirit*, ch. 15 |
| 20 | Grace, Not Grades | Romans 4:4–5 | *All of Grace*, ch. 3 |

**Part 3 · Following for Real**

| Day | Title | Scripture | Go deeper |
|---|---|---|---|
| 21 | Count the Cost | Luke 14:27–28 | *The Pilgrim's Progress (For Teens)*, ch. 2 |
| 22 | Standing Alone | Acts 4:19–20 | *Fox's Book of Martyrs*, ch. 2 |
| 23 | Temptation | James 1:13–15 | *The Mortification of Sin in Believers*, ch. 3 |
| 24 | Purity | 1 Thessalonians 4:3–4, 7 | *Purity of Heart*, ch. 1 |
| 25 | What You Post | Colossians 4:5–6 | *The Imitation of Christ*, ch. 11 |
| 26 | Friends Who Shape You | Proverbs 12:26 | *Growing in Wisdom*, ch. 8 |
| 27 | Parents | Ephesians 6:1–3 | *Susanna Wesley*, ch. 9 |
| 28 | Prayer When It's Boring | Matthew 6:6–8 | *With Christ in the School of Prayer*, ch. 4 |
| 29 | Hearing God | Psalm 32:8 | *The Secret of Guidance*, ch. 1 |
| 30 | Anchored | Hebrews 10:23 | *Absolute Surrender*, ch. 8 |

Conclusion: Holding Fast

---

## Book 2 — Real Life

*Real Life: faith for the mind, the screen, the heart and the home*

Introduction: Welcome Back

**Part 1 · My Mind**

| Day | Title | Scripture | Go deeper |
|---|---|---|---|
| 1 | Real Life | Romans 12:1 | *The Key Teachings of A. W. Tozer*, ch. 15 |
| 2 | Worried About the Future | Psalm 31:14–15 | *The Key Teachings of Elisabeth Elliot*, ch. 4 |
| 3 | When Fear Hits Hard | Isaiah 43:2–3 | *The Key Teachings of Corrie ten Boom*, ch. 7 |
| 4 | Thoughts That Won't Leave | Psalm 139:23–24 | *The Key Teachings of Martyn Lloyd-Jones*, ch. 14 |
| 5 | Never Good Enough | Hebrews 10:11–12 | *The Key Teachings of Martin Luther*, ch. 3 |
| 6 | Anger | Jonah 4:1, 4 | *The Imitation of Christ*, ch. 17 |
| 7 | Jealousy | 1 Samuel 18:7–9 | *The Key Teachings of C. S. Lewis*, ch. 7 |
| 8 | Bored | Ecclesiastes 2:24–25 | *Orthodoxy*, ch. 5 |
| 9 | My Body | Genesis 1:31 | *The Key Teachings of Augustine of Hippo*, ch. 21 |
| 10 | Rest | Psalm 127:1–2 | *The Key Teachings of Dietrich Bonhoeffer*, ch. 11 |

**Part 2 · My Screens and My Heart**

| Day | Title | Scripture | Go deeper |
|---|---|---|---|
| 11 | Who's in Charge, Me or My Phone? | 2 Peter 2:19 | *Confessions*, ch. 8 |
| 12 | What Fills My Mind | Matthew 6:22–23 | *Pensées*, ch. 2 |
| 13 | Games | Ecclesiastes 11:9 | *Growing in Wisdom*, ch. 14 |
| 14 | Cruelty Online | Psalm 55:12–14 | *The Key Teachings of Julia A. J. Foote*, ch. 10 |
| 15 | Influencers and What's Real | Ephesians 4:14 | *Amanda Smith: An Autobiography (For Teens)*, ch. 4 |
| 16 | Crushes | Proverbs 30:18–19 | *The Key Teachings of Elisabeth Elliot*, ch. 9 |
| 17 | Dating God's Way | Romans 13:10 | *The Key Teachings of C. S. Lewis*, ch. 13 |
| 18 | Breakups and Rejection | Isaiah 53:3 | *Portraits of Courage – Corrie ten Boom*, ch. 5 |
| 19 | Friend Drama and Gossip | Proverbs 17:9 | *The Ten Commandments*, ch. 13 |
| 20 | Seen, Liked, Still Lonely | 2 John 1:12 | *The Key Teachings of Dietrich Bonhoeffer*, ch. 9 |

**Part 3 · My People and My Pain**

| Day | Title | Scripture | Go deeper |
|---|---|---|---|
| 21 | Conflict at Home | James 4:1 | *The Key Teachings of Dietrich Bonhoeffer*, ch. 12 |
| 22 | When Parents Split Up | Psalm 147:3 | *The God of All Comfort*, ch. 8 |
| 23 | Brothers and Sisters | Genesis 33:3–4 | *They Were Young – Book 1: Called*, ch. 4 |
| 24 | Forgiving Someone Who Hurt You | Matthew 18:32–33 | *Tukutendereza*, ch. 9 |
| 25 | Saying Sorry | Luke 19:8 | *The Key Teachings of Charles G. Finney*, ch. 14 |
| 26 | When Someone Dies | John 11:32–33 | *Portraits of Courage – C. S. Lewis*, ch. 23 |
| 27 | I Failed | Micah 7:7–8 | *Samuel Ajayi Crowther (For Teens)*, ch. 9 |
| 28 | The Secret I Carry | 1 John 1:8–9 | *The Normal Christian Life*, ch. 1 |
| 29 | Wanting More Stuff | Luke 12:15 | *Sermons on Several Occasions*, ch. 51 |
| 30 | Real Life with God | Romans 15:13 | *The Inner Chamber*, ch. 1 |

Conclusion: Real Life, Real Hope
