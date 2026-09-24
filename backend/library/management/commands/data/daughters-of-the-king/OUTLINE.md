# Daughters of the King – 30 Days with God for Girls: series outline

Three house-written devotional books for girls aged 9–12 (Ochorus Originals), with 30 days per book. Every Scripture is quoted from the Berean Standard Bible (BSB), which is public domain. The companion series for boys is *Sons of the King* (`../sons-of-the-king/OUTLINE.md`). Both follow *Rooted* (`../rooted/OUTLINE.md`), the co-ed series for the same ages.

The day tables below are generated from the three manuscripts in this folder (`daughters-of-the-king-<n>.md`), so they match what shipped. The manuscripts are the source of truth. If a day changes, regenerate the tables rather than editing them by hand.

## The series at a glance

The anchor is 2 Corinthians 6:18: "I will be a Father to you, and you will be My sons and daughters, says the Lord Almighty." It is the key verse of Book 1, Day 5.

| Book | Focus | Slug | Reading plan |
|---|---|---|---|
| 1 | Beloved: who you are, whose you are, and the brave girls who went before you | `daughters-of-the-king-1` | `daughters-of-the-king-book-1-30-days` |
| 2 | Brave: courage for worry, a voice to speak, and hands to serve | `daughters-of-the-king-2` | `daughters-of-the-king-book-2-30-days` |
| 3 | Growing Up: your feelings, your changing body, wise choices, and God's calling | `daughters-of-the-king-3` | `daughters-of-the-king-book-3-30-days` |

## Founder decisions (2026-09-23)

- **Names:** the series has its own name rather than the Rooted brand. The boys' series is *Sons of the King*.
- **Size:** three books per series.
- **Womanhood:** character, courage and the women of the Bible. The books do not teach adult roles in the home or the church.
- **Puberty:** Book 3, Week 2 gives a fuller, age-appropriate treatment, with a parent note in the Introduction. Sex and reproduction are out of scope and left to parents. The founder reviewed the week before it shipped.
- **Same virtues, different angle:** the girls' books stress courage and a voice. The boys' books stress strength under control and gentleness.

## Format

- **Each day:** a title, the Scripture (BSB), a teaching of about 300–450 words, **Think about it** / **Try this**, and a prayer.
- **Each week** ends with "**A true story:**", a short spotlight on a woman from the *Brave for God* books. Book 3 revisits women from Books 1 and 2, each from a new angle, plus Lottie Moon.
- **Each book:** an Introduction, Day 1–30 and a Conclusion, so 32 chapters. The reading plan reads chapters 2–31, so plan day N is the chapter titled "Day N". The `(2, 31)` span in `LAUNCH_PLANS` handles this.
- **Every introduction** ends with a short note "For parents, grandparents and leaders". Every conclusion includes a gentle invitation to trust Jesus. Books 1 and 2 preview the next book, and Book 3 closes the series.
- **Key verses** don't repeat a key verse from Rooted or from earlier books in either series. Check a new day's verse against every manuscript, including verse ranges: Matthew 5:8 falls inside Matthew 5:3–9.

## Sensitive days and how they were handled

| Book · Day | Topic | Approach |
|---|---|---|
| 1 · 5 | God as Father | If your earthly dad has hurt you or isn't there, God is the perfect Father. If anyone at home is hurting you, tell a trusted adult. |
| 1 · 9 | Filters and feeds | Envy and comparison online. If screens make you feel bad about yourself, tell a parent. If something online scares you, turn it off and tell an adult. |
| 2 · 1–6 | Worry and fear | God's promises and comfort, sleep, and the "what ifs". If worry grows very big, tell a parent; there is no shame in getting help. |
| 2 · 4 | Body image | If worries about your body, weight or eating grow big, talk to a trusted grown-up. |
| 2 · 9 | Saying no | Brave enough to say no to what's wrong or unsafe. |
| 2 · 10 | Secrets that hurt | Body safety: good surprises versus secrets that hurt. No one should ask you to keep a secret about touching or pictures. It is never your fault, and telling is always right. |
| 2 · 11 | Asking for help | Help comes from the Lord, often through trusted adults. |
| 3 · 3 | Sadness | If you feel sad most of the time, tell a parent or trusted adult. Doctors and counselors can help. |
| 3 · 7–12 | **Puberty (the Week 2 block)** | Growth and body shape (weight gain is healthy, don't diet), breasts and a first bra, body hair, periods (uterus, lining, about monthly, pads, cramps, not dirty or shameful), hygiene, and hormones and moods. The only mention of reproduction: "one day… she could have a baby if God gives her one. Your mom can tell you more." Every day sends her to her mom or a woman she trusts. Days 9 and 12 carry the body-safety line. |
| 3 · 14 | Crushes | Song of Songs 2:7: don't rush love. Crushes are normal, there's no need to date, and she should talk to her parents. Be careful with pictures and messages online. |
| 3 · 17 | Online | Don't believe everything. Protect personal information, never meet online strangers, watch out for flattery and secrecy, and tell a trusted adult. |

## Building a volume

```bash
DJANGO_DEBUG=true uv run python manage.py build_rooted <n> --series daughters-of-the-king
```

`build_rooted.py` converts the manuscript (a closed Markdown subset; its docstring lists the syntax) and runs the English audit. `DAUGHTERS_OF_THE_KING[n]` (in `SERIES`) holds the book's fields. The steps that follow are the same as Rooted's (see `../rooted/OUTLINE.md`): fixture, covers, plan, `BOOK_STYLE`, shelf and prerender touches. Check every verse against the BSB, including short quotes inside the teachings.

---

## Book 1 — Beloved

*Beloved: who you are, whose you are, and the brave girls who went before you*

Introduction: You Are a Daughter of the King

**Week 1 · Whose I Am**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 1 | Called by Name | Isaiah 43:1 |  |
| 2 | Made to Reflect Him | 2 Corinthians 3:18 |  |
| 3 | God Looks at the Heart | 1 Samuel 16:7 |  |
| 4 | Real Beauty | 1 Peter 3:3–4 |  |
| 5 | His Daughter | 2 Corinthians 6:18 |  |
| 6 | He Sings over You | Zephaniah 3:17 | Amy Carmichael |

**Week 2 · The Comparison Trap**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 7 | Run Your Own Race | Galatians 6:4–5 |  |
| 8 | The Sister Nobody Noticed | Genesis 29:31 |  |
| 9 | Filters and Feeds | Proverbs 14:30 |  |
| 10 | Pleasant Places | Psalm 16:5–6 |  |
| 11 | Celebrate Her | Luke 1:41–42, 45 |  |
| 12 | All You Need | Philippians 4:19 | Gladys Aylward |

**Week 3 · Friends and Words**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 13 | Where You Go, I'll Go | Ruth 1:16 |  |
| 14 | No Favorites | James 2:1–4 |  |
| 15 | Drama-Free | Proverbs 26:20 |  |
| 16 | Words Like Honey | Proverbs 16:24 |  |
| 17 | When a Friend Hurts You | Ephesians 4:26–27 |  |
| 18 | A Friend Who Points to Jesus | Hebrews 3:13 | Corrie ten Boom |

**Week 4 · Brave Girls of the Bible**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 19 | Miriam Watches the Basket | Exodus 2:4, 7–8 |  |
| 20 | Deborah Says "Go!" | Judges 4:14 |  |
| 21 | Abigail the Peacemaker | 1 Samuel 25:32–33 |  |
| 22 | Rahab's Scarlet Cord | Joshua 2:11 |  |
| 23 | The Servant Girl Who Spoke Up | 2 Kings 5:2–3 |  |
| 24 | Mary Says Yes | Luke 1:38 | Mary Slessor |

**Week 5 · A Heart for God**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 25 | Hannah Pours Out Her Heart | 1 Samuel 1:15 |  |
| 26 | Sitting at Jesus' Feet | Luke 10:41–42 |  |
| 27 | A Beautiful Deed | Mark 14:6 |  |
| 28 | Lydia Opens Her Heart | Acts 16:14 |  |
| 29 | Strength and Honor | Proverbs 31:25 |  |
| 30 | A Woman Who Fears the Lord | Proverbs 31:30 | Mary Jones |

Conclusion: Beloved

---

## Book 2 — Brave

*Brave: courage for worry, a voice to speak, and hands to serve*

Introduction: Brave Girls

**Week 1 · When I'm Anxious**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 1 | Brave Isn't Fearless | Isaiah 41:10 |  |
| 2 | When Worry Won't Stop | Psalm 94:19 |  |
| 3 | Sweet Sleep | Proverbs 3:24 |  |
| 4 | Consider the Lilies | Matthew 6:28–30 |  |
| 5 | One Day at a Time | Matthew 6:34 |  |
| 6 | Perfect Love Drives Out Fear | 1 John 4:18 | Helen Roseveare |

**Week 2 · Using Your Voice**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 7 | A Time to Speak | Ecclesiastes 3:7 |  |
| 8 | The Daughters Who Spoke Up | Numbers 27:7 |  |
| 9 | Brave Enough to Say No | Titus 2:11–12 |  |
| 10 | No Secrets That Hurt | Ephesians 5:11, 13 |  |
| 11 | Where Help Comes From | Psalm 121:1–2 |  |
| 12 | Speaking the Truth in Love | Ephesians 4:15 | Pandita Ramabai |

**Week 3 · Serving**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 13 | Phoebe, a Great Help | Romans 16:1–2 |  |
| 14 | Priscilla Makes Room | Acts 18:26 |  |
| 15 | Dorcas's Needle | Acts 9:39 |  |
| 16 | Healed to Serve | Mark 1:31 |  |
| 17 | The Last Handful of Flour | 1 Kings 17:15–16 |  |
| 18 | Serve with Gladness | Psalm 100:2 | Ida Scudder |

**Week 4 · Leading**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 19 | Miriam Leads the Song | Exodus 15:20–21 |  |
| 20 | Wise Words | Proverbs 31:26 |  |
| 21 | Steadfast | 1 Corinthians 15:58 |  |
| 22 | The Queen Who Asked Questions | 1 Kings 10:1 |  |
| 23 | The Leader Who Serves | Luke 22:26 |  |
| 24 | Faith Passed Down | 2 Timothy 1:5 | Elisabeth Elliot |

**Week 5 · Women Who Followed Jesus**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 25 | The Women Who Followed | Luke 8:1–3 |  |
| 26 | "Daughter" | Mark 5:34 |  |
| 27 | Faith That Wouldn't Quit | Matthew 15:28 |  |
| 28 | Near the Cross | John 19:25 |  |
| 29 | "Mary!" | John 20:16 |  |
| 30 | "I Have Seen the Lord!" | John 20:18 | Lilias Trotter |

Conclusion: Brave Daughter

---

## Book 3 — Growing Up

*Growing Up: your feelings, your changing body, wise choices, and God's calling*

Introduction: Growing Up

**Week 1 · Feelings**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 1 | A Time to Laugh, a Time to Cry | Ecclesiastes 3:4 |  |
| 2 | When You're Angry | Psalm 4:4 |  |
| 3 | When You're Sad | Psalm 42:5 |  |
| 4 | When You're Embarrassed | Isaiah 54:4 |  |
| 5 | Pour It Out | Psalm 62:8 |  |
| 6 | Captain of Your Thoughts | 2 Corinthians 10:5 | Amy Carmichael |

**Week 2 · Your Body and Growing Up**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 7 | Your Body, God's Design | Psalm 139:15 |  |
| 8 | Changing Shape | Proverbs 31:17 |  |
| 9 | Growing Up Is Good | Luke 2:40 |  |
| 10 | Your Period | Isaiah 46:4 |  |
| 11 | Taking Care of Your Body | 3 John 1:2 |  |
| 12 | Feelings on a Roller Coaster | Psalm 16:8 | Ida Scudder |

**Week 3 · Wise Choices**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 13 | Wisdom Is Supreme | Proverbs 4:7 |  |
| 14 | Crushes and Feelings | Song of Songs 2:7 |  |
| 15 | Money Wise | Proverbs 13:11 |  |
| 16 | Plans in God's Hands | Proverbs 16:3 |  |
| 17 | Don't Believe Everything | Proverbs 14:15 |  |
| 18 | Clean Hands, Pure Heart | Psalm 24:3–4 | Gladys Aylward |

**Week 4 · Calling**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 19 | Made for a Purpose | Jeremiah 1:5 |  |
| 20 | Different Gifts | Romans 12:6 |  |
| 21 | Dream with God | Psalm 37:4 |  |
| 22 | Sons and Daughters | Joel 2:28 |  |
| 23 | Small Beginnings | Zechariah 4:10 |  |
| 24 | Here Am I | Isaiah 6:8 | Lottie Moon |

**Week 5 · Mentors and Finishing Well**

| Day | Title | Scripture | True story |
|---|---|---|---|
| 25 | Naomi's Advice | Ruth 3:1, 5 |  |
| 26 | Three Months with Elizabeth | Luke 1:56 |  |
| 27 | Be a Big Sister | 1 Thessalonians 5:11 |  |
| 28 | Anna Never Stopped | Luke 2:36–38 |  |
| 29 | Still Bearing Fruit | Psalm 92:14 |  |
| 30 | Renewed Day by Day | 2 Corinthians 4:16 | Mary Slessor |

Conclusion: A Daughter Growing Up

