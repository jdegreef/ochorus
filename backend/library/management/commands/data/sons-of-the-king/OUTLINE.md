# Sons of the King – 30 Days with God for Guys: series outline

Three house-written devotional books for boys aged 9–12 (Ochorus Originals), with 30 days per book. Every Scripture is quoted from the Berean Standard Bible (BSB), which is public domain. The companion series for girls is *Daughters of the King* (`../daughters-of-the-king/OUTLINE.md`), which also records the founder decisions the two series share. Both follow *Rooted* (`../rooted/OUTLINE.md`), the co-ed series for the same ages.

The day tables below are generated from the three manuscripts in this folder (`sons-of-the-king-<n>.md`), so they match what shipped. The manuscripts are the source of truth. If a day changes, regenerate the tables rather than editing them by hand.

## The series at a glance

The anchor is 2 Corinthians 6:18: "I will be a Father to you, and you will be My sons and daughters, says the Lord Almighty."

| Book | Focus | Slug | Reading plan |
|---|---|---|---|
| 1 | Strong: who you are, whose you are, and the brave men who went before you | `sons-of-the-king-1` | `sons-of-the-king-book-1-30-days` |
| 2 | Faithful: integrity, screens, temptation, sports, and following Jesus all the way | `sons-of-the-king-2` | `sons-of-the-king-book-2-30-days` |
| 3 | Growing Up: your feelings, your changing body, wise choices, and God's calling | `sons-of-the-king-3` | `sons-of-the-king-book-3-30-days` |

## Approach

- **Manhood:** character, courage and the men of the Bible, with strength under control and gentleness. The books do not teach adult roles in the home or the church.
- **Puberty:** Book 3, Week 2 gives a fuller, age-appropriate treatment, with a parent note in the Introduction. Sex and reproduction are out of scope and left to parents. The founder reviewed the week, including Day 10, before it shipped (2026-09-24).
- **Feelings are for guys too:** Book 1, Day 12 ("Real Men Cry") and Book 3, Week 1 (starting with the anger and sorrow Jesus felt, Mark 3:5) push back on "real men don't have feelings".

## Format

- **Each day:** a title, the Scripture (BSB), a teaching of about 300–450 words, **Think about it** / **Try this**, and a prayer.
- **Each week** ends with "**A true story:**", a short spotlight on a man from the *Brave for God* books. In Book 1, the fifth spotlight falls on Day 29.
- **Each book:** an Introduction, Day 1–30 and a Conclusion, so 32 chapters. The reading plan reads chapters 2–31 (span `(2, 31)` in `LAUNCH_PLANS`).
- **Every introduction** ends with a short note "For parents, grandparents and leaders". Every conclusion includes a gentle invitation to trust Jesus. Books 1 and 2 preview the next book, and Book 3 closes the series.
- **Key verses** don't repeat a key verse from Rooted or from earlier books in either series. Check verse ranges too, not only exact references: Book 3 first shipped Matthew 5:8 and 2 Timothy 4:7, which fall inside Rooted's Matthew 5:3–9 and 2 Timothy 4:6–8, and those two days were later given 1 John 3:2–3 and Acts 20:24.

## Sensitive days and how they were handled

| Book · Day | Topic | Approach |
|---|---|---|
| 1 · 4 | God as Father | Some dads are distant or have hurt their sons; God is the Father who is compassionate. |
| 1 · 10 | Don't get even | Not getting even never means letting people keep hurting you. Tell a trusted adult about bullying. |
| 1 · 17 | Treat girls with respect | Treat girls as sisters (1 Timothy 5:1–2). |
| 1 · 27 | Guarding your eyes | Psalm 119:37. Decide ahead, look away, set device boundaries with parents, and tell a parent about anything online that troubles you. |
| 1 · 28 | Honoring your father | Every family looks different. If anyone at home is hurting you or making you feel unsafe, tell a trusted adult. |
| 2 · 7–12 | Screens and gaming | Limits, online anger, and harmful content ("wise about good, innocent about evil"). Tell a parent about anything that troubles you. |
| 2 · 15 | Wrong desires | General terms only ("new and strong feelings"): run from wrong, and talk with a parent. |
| 3 · 3 | Feeling down | Elijah: rest, food, talk. If sadness lasts, or he ever feels he doesn't want to be alive, tell a parent or trusted adult right away. |
| 3 · 6 | Grief | Grieving with hope. If sadness doesn't lift, tell a trusted adult. |
| 3 · 7–12 | **Puberty (the Week 2 block)** | Growth spurts and comparing (no supplements without parents and a doctor), the voice changing and body and facial hair, hygiene, and hormones and strength. Every day sends him to his dad or a man he trusts. Day 12 carries the body-safety line. |
| 3 · 10 | **Private parts, erections, wet dreams** | Named plainly (penis, testicles) and described briefly: normal, not shameful, not something he did wrong. The only mention of reproduction: "so that one day when they're grown, they could become fathers. Your dad or mom can tell you more." Private parts are private, and he should get answers from his parents, not other kids or the internet. |
| 3 · 14 | Crushes | Song of Songs 8:4 (the refrain the girls' book quotes from 2:7): don't rush love. Treat girls with respect, don't be pressured by the guys, be careful with pictures online, and talk to parents. |
| 3 · 17 | Dares and danger | Stunts, online challenges, vaping, alcohol and drugs, weapons, and secret plans. |

## Building a volume

```bash
DJANGO_DEBUG=true uv run python manage.py build_rooted <n> --series sons-of-the-king
```

`SONS_OF_THE_KING[n]` (in `SERIES` in `build_rooted.py`) holds the book's fields. The steps that follow are the same as Rooted's (see `../rooted/OUTLINE.md`). Check every verse against the BSB, including short quotes inside the teachings.

---

## Book 1 — Strong

*Strong: who you are, whose you are, and the brave men who went before you*

Introduction: You Are a Son of the King

**Week 1 · Who I Really Am**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 1 | A New Name | John 1:40–42 |  |
| 2 | More Than My Score | Jeremiah 9:23–24 |  |
| 3 | Son and Heir | Galatians 4:6–7 |  |
| 4 | A Father's Compassion | Psalm 103:13–14 |  |
| 5 | Strength from God | Psalm 18:1, 32–33 |  |
| 6 | Gideon, the Least | Judges 6:12, 15 | Samuel Crowther |

**Week 2 · Strength Under Control**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 7 | The Strongest Man Who Fell | Judges 16:20 |  |
| 8 | Better Than a Warrior | Proverbs 16:32 |  |
| 9 | Sin at the Door | Genesis 4:6–7 |  |
| 10 | Don't Get Even | Proverbs 20:22 |  |
| 11 | Gentle and Strong | Matthew 11:28–29 |  |
| 12 | Real Men Cry | Psalm 56:8 | Festo Kivengere |

**Week 3 · Friends and Brothers**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 13 | Iron Sharpens Iron | Proverbs 27:17 |  |
| 14 | Barnabas the Encourager | Acts 11:23–24 |  |
| 15 | Like a Son with His Father | Philippians 2:22 |  |
| 16 | Choose Your Crew | 1 Corinthians 15:33 |  |
| 17 | Treat Girls with Respect | 1 Timothy 5:1–2 |  |
| 18 | Do Justice, Love Mercy | Micah 6:8 | C.T. Studd |

**Week 4 · Courage**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 19 | A Different Spirit | Numbers 14:24 |  |
| 20 | Jonathan's Climb | 1 Samuel 14:6–7 |  |
| 21 | Choose! | 1 Kings 18:21 |  |
| 22 | Brave Enough to Say Sorry | Psalm 32:5 |  |
| 23 | Stephen Stands Firm | Acts 7:59–60 |  |
| 24 | The Boy King | 2 Kings 22:1–2 | Eric Liddell |

**Week 5 · Work, Honor and Faith**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 25 | Learn from the Ant | Proverbs 6:6–8 |  |
| 26 | A Man of His Word | Matthew 5:37 |  |
| 27 | Turn My Eyes Away | Psalm 119:37 |  |
| 28 | Listen to Your Father | Proverbs 23:22 |  |
| 29 | Samuel Grew | 1 Samuel 2:26 | William Carey |
| 30 | Be Men of Courage | 1 Corinthians 16:13–14 |  |

Conclusion: Strong

---

## Book 2 — Faithful

*Faithful: integrity, screens, temptation, sports, and following Jesus all the way*

Introduction: Faithful

**Week 1 · Integrity**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 1 | Walking with Integrity | Proverbs 20:7 |  |
| 2 | Your Built-In GPS | Proverbs 11:3 |  |
| 3 | Honest Scales | Proverbs 11:1 |  |
| 4 | When No One's Watching | Proverbs 15:3 |  |
| 5 | Hidden in the Tent | Numbers 32:23 |  |
| 6 | A Faithful Man | Proverbs 28:20 | George Müller |

**Week 2 · Screens and Gaming**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 7 | Who's the Boss? | 1 Corinthians 6:12 |  |
| 8 | Count Your Days | Psalm 90:12 |  |
| 9 | Rage Quit | James 1:20 |  |
| 10 | Be Wise, Stay Innocent | Romans 16:19 |  |
| 11 | Don't Disappear | Proverbs 18:1 |  |
| 12 | Offline with God | Mark 1:35 | Adoniram Judson |

**Week 3 · Temptation**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 13 | How Temptation Works | Genesis 3:6 |  |
| 14 | Watch and Pray | Matthew 26:41 |  |
| 15 | Run and Chase | 2 Timothy 2:22 |  |
| 16 | Better Together | Ecclesiastes 4:9–10 |  |
| 17 | The Bowl of Stew | Genesis 25:32–34 |  |
| 18 | Help in the Moment | Hebrews 4:15–16 | Sundar Singh |

**Week 4 · Winning and Losing**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 19 | Run to Win | 1 Corinthians 9:24–25 |  |
| 20 | Train Yourself | 1 Timothy 4:7–8 |  |
| 21 | No Gloating | Proverbs 24:17 |  |
| 22 | Press On | Philippians 3:13–14 |  |
| 23 | Let Someone Else Say It | Proverbs 27:2 |  |
| 24 | In Jesus' Name | Colossians 3:17 | David Livingstone |

**Week 5 · Men Who Followed Jesus**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 25 | Andrew, the Bringer | John 12:20–22 |  |
| 26 | Thomas Asks | John 14:5–6 |  |
| 27 | "My Lord and My God!" | John 20:27–28 |  |
| 28 | John, Son of Thunder | 1 John 3:18 |  |
| 29 | "Do You Love Me?" | John 21:17 |  |
| 30 | "You Follow Me!" | John 21:21–22 | Hudson Taylor |

Conclusion: Found Faithful

---

## Book 3 — Growing Up

*Growing Up: your feelings, your changing body, wise choices, and God's calling*

Introduction: Growing Up

**Week 1 · Feelings**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 1 | What Jesus Felt | Mark 3:5 |  |
| 2 | Blowing Up | Proverbs 29:11 |  |
| 3 | Elijah Under the Tree | 1 Kings 19:5 |  |
| 4 | Under Pressure | Psalm 61:2 |  |
| 5 | Deep Water | Proverbs 20:5 |  |
| 6 | The God of All Comfort | 2 Corinthians 1:3–4 | John Paton |

**Week 2 · Your Body and Growing Up**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 7 | Built by God | Job 10:11 |  |
| 8 | Zacchaeus Was Small | Luke 19:3 |  |
| 9 | When I Became a Man | 1 Corinthians 13:11 |  |
| 10 | Nothing to Be Ashamed Of | Psalm 119:73 |  |
| 11 | Clean Clothes | Ecclesiastes 9:8 |  |
| 12 | The Glory of Young Men | Proverbs 20:29 | Eric Liddell |

**Week 3 · Wise Choices**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 13 | Where Wisdom Comes From | Proverbs 2:6 |  |
| 14 | Not Yet | Song of Songs 8:4 |  |
| 15 | Save Some | Proverbs 21:20 |  |
| 16 | Don't Follow the Crowd | Exodus 23:2 |  |
| 17 | Dares and Danger | Proverbs 22:3 |  |
| 18 | Pure, as He Is Pure | 1 John 3:2–3 | Jim Elliot |

**Week 4 · Calling**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 19 | Too Young? Not to God | Jeremiah 1:7 |  |
| 20 | Bezalel the Builder | Exodus 31:2–3 |  |
| 21 | With All Your Might | Ecclesiastes 9:10 |  |
| 22 | Let's Build | Nehemiah 2:18 |  |
| 23 | Skilled Hands | Proverbs 22:29 |  |
| 24 | Serve Your Generation | Acts 13:36 | George Liele |

**Week 5 · Mentors and Finishing Well**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 25 | Elisha Leaves the Plow | 1 Kings 19:21 |  |
| 26 | I Will Not Leave You | 2 Kings 2:2 |  |
| 27 | A Double Portion | 2 Kings 2:9 |  |
| 28 | Pass It On | 2 Timothy 2:2 |  |
| 29 | Strong at Eighty-Five | Joshua 14:10–11 |  |
| 30 | Finish the Race | Acts 20:24 | Simeon Nsibambi |

Conclusion: A Son Growing Up

