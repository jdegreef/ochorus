# Rooted – 30 Days with God for Youth: series outline

Six house-written devotional books for readers aged 9–12 (Ochorus Originals), with 30 days per book. Every Scripture is quoted from the Berean Standard Bible (BSB), which is public domain.

This outline is generated from the six manuscripts in this folder (`rooted-<n>.md`), so it matches what shipped. The manuscripts are the source of truth. If a day changes, regenerate this file rather than editing it by hand.

## The series at a glance

The whole series uses one picture: **a tree**. Colossians 2:6–7 is on Book 1, Day 1, and the series conclusion returns to it.

| Book | Focus | Slug | Reading plan |
|---|---|---|---|
| 1 | Planted: knowing God, receiving Jesus, and learning to grow | `rooted-1` | `rooted-book-1-30-days` |
| 2 | Following Jesus: walking with Jesus from the manger to the empty tomb | `rooted-2` | `rooted-book-2-30-days` |
| 3 | Growing Fruit: the fruit of the Spirit, the words we say, and the habits of the heart | `rooted-3` | `rooted-book-3-30-days` |
| 4 | Strong in the Storm: courage for when you're afraid, sad, tempted or treated unfairly | `rooted-4` | `rooted-book-4-30-days` |
| 5 | Branching Out: loving your family, your friends, God's family and the world | `rooted-5` | `rooted-book-5-30-days` |
| 6 | Bearing Fruit: God's purpose for your life, now and forever | `rooted-6` | `rooted-book-6-30-days` |

## Format

- **Each day:** a title, the Scripture (BSB), a teaching of about 300–400 words, **Think about it** / **Try this**, and a prayer.
- **Each book:** an Introduction, Day 1–30 and a Conclusion, so 32 chapters. The reading plan reads chapters 2–31, so plan day N is the chapter titled "Day N". The `(2, 31)` span in `LAUNCH_PLANS` handles this.
- **Every introduction** ends with a short note "For parents, grandparents and leaders". Every conclusion includes a gentle invitation to trust Jesus and a preview of the next book.

## Sensitive days and how they were handled

| Book · Day | Topic | Approach |
|---|---|---|
| 4 · 10 | When someone dies | Suggests reading it with a grown-up. Grieving with hope. If a reader is unsure whether someone knew Jesus: "you can trust God with them." |
| 4 · 11 | When home is hard | It's not your fault. God is a Father who never leaves. If anyone is hurting you, tell a trusted adult right away. |
| 5 · 2, 5 | Honoring and listening to parents | No one should ask you to do something wrong or unsafe. If they do, tell another trusted adult. |
| 5 · 13, 14 | Forgiveness | Forgiving is not pretending it didn't hurt, trusting right away, or staying where you can be hurt. |
| 5 · 17 | Bullies | It's not your fault. Loving an enemy never means letting them keep hurting you. Tell a trusted adult until someone helps. Telling is not tattling. |
| 6 · 13 | The body as a temple | A one-line body-safety note. |
| 6 · 14 | Growing up | General terms only. The changes are part of God's design. Take questions to a parent. |
| 6 · 16 | Online | Staying safe online: personal information, strangers, secrets and pictures. Tell an adult. |
| 6 · 17 | Male and female | Both are made in God's image and are equally precious. Galatians 3:28. |

## Building a volume

```bash
DJANGO_DEBUG=true uv run python manage.py build_rooted <n>
```

`build_rooted.py` converts the manuscript (a closed Markdown subset; its docstring lists the syntax) and runs the English audit. `ROOTED[n]` (in `SERIES`) holds the book's fields. Then:

1. Serialize the fixture.
2. Run `generate_covers`, then `npm run og:covers`.
3. Add the `LAUNCH_PLANS` entry with span `(2, 31)`.
4. Add the `BOOK_STYLE` entry in `coverStyles.ts`. (The volume numeral needs nothing: `build_rooted` sets `series` / `series_position`, and the cover reads them.)
5. Add the book to the For Young Readers shelf in `topic_seed.py`.
6. Add the prerender touches on `books/` and `plans/`.

Check every verse against the BSB, including short quotes inside the teachings.

## Future

- The gender-specific follow-ups shipped as distinct books rather than editions of these: *Daughters of the King* (`../daughters-of-the-king/OUTLINE.md`) and *Sons of the King* (`../sons-of-the-king/OUTLINE.md`), three books each.
- Other languages would go through the normal translation pipeline (`ai_unreviewed`).

---

## Book 1 — Planted

*Planted: knowing God, receiving Jesus, and learning to grow*

Introduction: Welcome to Rooted

**Week 1 · Who Is God?**

| Day | Title | Scripture |
|---|---|---|
| 1 | Planted | Colossians 2:6–7 |
| 2 | In the Beginning | Genesis 1:1 |
| 3 | Bigger Than the Stars | Isaiah 40:26 |
| 4 | Holy, Holy, Holy | Isaiah 6:1–3 |
| 5 | God Is Love | 1 John 4:9–10 |
| 6 | The God Who Never Changes | James 1:17 |

**Week 2 · The Best News Ever**

| Day | Title | Scripture |
|---|---|---|
| 7 | Something Went Wrong | Romans 3:23–24 |
| 8 | A Promise in the Dark | Isaiah 9:6 |
| 9 | God with Us | Matthew 1:21–23 |
| 10 | The Cross | John 3:16; Romans 5:8 |
| 11 | The Empty Tomb | Luke 24:5–6 |
| 12 | Receiving the Gift | Ephesians 2:8–9 |

**Week 3 · Who I Am in Christ**

| Day | Title | Scripture |
|---|---|---|
| 13 | Made on Purpose | Psalm 139:13–14 |
| 14 | Child of God | 1 John 3:1 |
| 15 | Forgiven | Psalm 103:10–12 |
| 16 | Brand New | 2 Corinthians 5:17 |
| 17 | Never Alone | Hebrews 13:5–6 |
| 18 | The Helper Inside | John 14:16–17 |

**Week 4 · Talking with God**

| Day | Title | Scripture |
|---|---|---|
| 19 | God Is Listening | Jeremiah 33:3 |
| 20 | Our Father | Matthew 6:9–10 |
| 21 | Daily Bread | Matthew 6:11 |
| 22 | Saying Sorry to God | Psalm 51:1–2, 10 |
| 23 | Thank You, God | 1 Thessalonians 5:16–18 |
| 24 | When God Says "Wait" | Psalm 27:13–14 |

**Week 5 · Growing Deep**

| Day | Title | Scripture |
|---|---|---|
| 25 | A Lamp for My Feet | Psalm 119:105 |
| 26 | Hiding God's Word | Psalm 119:9–11 |
| 27 | Don't Just Listen — Do | James 1:22–24 |
| 28 | Growing Together | Hebrews 10:24–25 |
| 29 | Sing to the Lord | Psalm 95:1–3 |
| 30 | A Tree by the Water | Jeremiah 17:7–8 |

Conclusion: You're Planted — Keep Growing

---

## Book 2 — Following Jesus

*Following Jesus: walking with Jesus from the manger to the empty tomb*

Introduction: Come and Meet Jesus

**Week 1 · Jesus Arrives**

| Day | Title | Scripture |
|---|---|---|
| 1 | The Word Became Flesh | John 1:1; John 1:14 |
| 2 | No Room | Luke 2:6–7 |
| 3 | Good News for Shepherds | Luke 2:10–11 |
| 4 | Wise Men Worship | Matthew 2:10–11 |
| 5 | Jesus at Twelve | Luke 2:46–47, 49 |
| 6 | Growing Like Jesus | Luke 2:52 |

**Week 2 · Jesus Begins**

| Day | Title | Scripture |
|---|---|---|
| 7 | "This Is My Beloved Son" | Matthew 3:16–17 |
| 8 | Tempted but Never Sinned | Matthew 4:1–4 |
| 9 | Follow Me | Mark 1:16–18 |
| 10 | Water into Wine | John 2:5; John 2:11 |
| 11 | Nicodemus at Night | John 3:1–3 |
| 12 | Living Water | John 4:13–14 |

**Week 3 · Jesus' Power**

| Day | Title | Scripture |
|---|---|---|
| 13 | Even the Wind Obeys | Mark 4:39–41 |
| 14 | A Boy's Lunch | John 6:9–11 |
| 15 | Walking on Water | Matthew 14:29–31 |
| 16 | "What Do You Want Me to Do?" | Mark 10:51–52 |
| 17 | Let the Children Come | Mark 10:13–14 |
| 18 | Lazarus, Come Out! | John 11:25–26 |

**Week 4 · Jesus' Teaching**

| Day | Title | Scripture |
|---|---|---|
| 19 | Upside-Down Happiness | Matthew 5:3–9 |
| 20 | Salt and Light | Matthew 5:14–16 |
| 21 | Look at the Birds | Matthew 6:26 |
| 22 | The Lost Sheep | Luke 15:4–7 |
| 23 | The Runaway Son | Luke 15:20 |
| 24 | The Good Samaritan | Luke 10:36–37 |

**Week 5 · Jesus Wins**

| Day | Title | Scripture |
|---|---|---|
| 25 | Zacchaeus Climbs a Tree | Luke 19:5; Luke 19:10 |
| 26 | Hosanna! | Matthew 21:9 |
| 27 | Washing Feet | John 13:14–15 |
| 28 | "It Is Finished" | John 19:30 |
| 29 | He Is Risen! | Matthew 28:5–6 |
| 30 | Go and Tell | Matthew 28:19–20 |

Conclusion: Keep Following

---

## Book 3 — Growing Fruit

*Growing Fruit: the fruit of the Spirit, the words we say, and the habits of the heart*

Introduction: What Is Growing on Your Tree?

**Week 1 · The Fruit of the Spirit**

| Day | Title | Scripture |
|---|---|---|
| 1 | Branches on the Vine | John 15:4–5 |
| 2 | Love | 1 Corinthians 13:4–7 |
| 3 | Joy | Philippians 4:4 |
| 4 | Peace | John 14:27 |
| 5 | Patience | Colossians 3:12 |
| 6 | Kindness | Ephesians 4:32 |

**Week 2 · More Fruit**

| Day | Title | Scripture |
|---|---|---|
| 7 | Goodness | Galatians 6:9–10 |
| 8 | Faithfulness | Luke 16:10 |
| 9 | Gentleness | Proverbs 15:1 |
| 10 | Self-Control | Proverbs 25:28 |
| 11 | Humility | Philippians 2:3–5 |
| 12 | Checking Your Fruit | Galatians 5:22–23, 25 |

**Week 3 · Words**

| Day | Title | Scripture |
|---|---|---|
| 13 | A Tiny Spark | James 3:3–5 |
| 14 | Telling the Truth | Proverbs 12:22 |
| 15 | Words That Build | Ephesians 4:29 |
| 16 | No Grumbling | Philippians 2:14–15 |
| 17 | Gossip | Proverbs 16:28; Proverbs 11:13 |
| 18 | Quick to Listen | James 1:19 |

**Week 4 · Heart Habits**

| Day | Title | Scripture |
|---|---|---|
| 19 | Respect | 1 Peter 2:17 |
| 20 | Enter with Thanks | Psalm 100:4–5 |
| 21 | Work as for the Lord | Colossians 3:23–24 |
| 22 | Content | Philippians 4:11–13 |
| 23 | More Blessed to Give | Acts 20:35 |
| 24 | Guard Your Heart | Proverbs 4:23 |

**Week 5 · Pure and Wise**

| Day | Title | Scripture |
|---|---|---|
| 25 | Just Ask | James 1:5 |
| 26 | Think About Such Things | Philippians 4:8 |
| 27 | What My Eyes See | Psalm 101:3 |
| 28 | The Same in the Dark | Proverbs 10:9 |
| 29 | Pride Before a Fall | Proverbs 16:18 |
| 30 | Known by Its Fruit | Luke 6:43–45 |

Conclusion: A Fruitful Life

---

## Book 4 — Strong in the Storm

*Strong in the Storm: courage for when you're afraid, sad, tempted or treated unfairly*

Introduction: When the Storms Come

**Week 1 · When I'm Afraid**

| Day | Title | Scripture |
|---|---|---|
| 1 | Built on the Rock | Matthew 7:24–25 |
| 2 | When I Am Afraid | Psalm 56:3–4 |
| 3 | The Lord Is My Shepherd | Psalm 23:1–4 |
| 4 | Strong and Courageous | Joshua 1:9 |
| 5 | David and Goliath | 1 Samuel 17:45 |
| 6 | Sleep in Peace | Psalm 4:8 |

**Week 2 · Worry and Sadness**

| Day | Title | Scripture |
|---|---|---|
| 7 | Cast Your Cares | 1 Peter 5:7 |
| 8 | Pray Instead of Worry | Philippians 4:6–7 |
| 9 | Jesus Wept | John 11:35; Psalm 34:18 |
| 10 | When Someone Dies | 1 Thessalonians 4:13–14 |
| 11 | When Home Is Hard | Psalm 27:10 |
| 12 | God Works for Good | Romans 8:28 |

**Week 3 · Temptation**

| Day | Title | Scripture |
|---|---|---|
| 13 | The Way Out | 1 Corinthians 10:13 |
| 14 | Joseph Runs | Genesis 39:9; Genesis 39:12 |
| 15 | Don't Be Squeezed | Romans 12:2 |
| 16 | Daniel's Decision | Daniel 1:8 |
| 17 | Resist | James 4:7–8 |
| 18 | Getting Back Up | Proverbs 24:16; Lamentations 3:22–23 |

**Week 4 · Standing Firm**

| Day | Title | Scripture |
|---|---|---|
| 19 | The Armor of God | Ephesians 6:10–11 |
| 20 | Belt, Breastplate, Shoes | Ephesians 6:14–15 |
| 21 | Shield, Helmet, Sword | Ephesians 6:16–17 |
| 22 | Even If He Doesn't | Daniel 3:17–18 |
| 23 | Daniel Kept Praying | Daniel 6:10 |
| 24 | Not Ashamed | Romans 1:16 |

**Week 5 · Hope That Holds**

| Day | Title | Scripture |
|---|---|---|
| 25 | It's Not Fair | Genesis 50:20 |
| 26 | Higher Ways | Isaiah 55:8–9 |
| 27 | Wings Like Eagles | Isaiah 40:31 |
| 28 | Strong When Weak | 2 Corinthians 12:9 |
| 29 | Nothing Can Separate Us | Romans 8:38–39 |
| 30 | An Anchor for the Soul | Hebrews 6:19 |

Conclusion: Standing Strong

---

## Book 5 — Branching Out

*Branching Out: loving your family, your friends, God's family and the world*

Introduction: Branches That Reach Out

**Week 1 · Love at Home**

| Day | Title | Scripture |
|---|---|---|
| 1 | The Greatest Commandment | Matthew 22:37–40 |
| 2 | Honor Your Father and Mother | Exodus 20:12 |
| 3 | Brothers and Sisters | Psalm 133:1 |
| 4 | Serve One Another | Galatians 5:13 |
| 5 | When Parents Say No | Proverbs 1:8–9 |
| 6 | As for Me and My House | Joshua 24:15 |

**Week 2 · Friends**

| Day | Title | Scripture |
|---|---|---|
| 7 | A Friend Loves at All Times | Proverbs 17:17 |
| 8 | David and Jonathan | 1 Samuel 18:1, 3–4 |
| 9 | Walk with the Wise | Proverbs 13:20 |
| 10 | Outdo One Another | Romans 12:10 |
| 11 | The God Who Sees Me | Genesis 16:13 |
| 12 | Accept One Another | Romans 15:7 |

**Week 3 · Forgiveness and Peace**

| Day | Title | Scripture |
|---|---|---|
| 13 | Seventy-Seven Times | Matthew 18:21–22 |
| 14 | Forgive as He Forgave | Colossians 3:13 |
| 15 | Make It Right | Matthew 5:23–24 |
| 16 | As Far as It Depends on You | Romans 12:18 |
| 17 | Love Your Enemies | Luke 6:27–28 |
| 18 | Overcome Evil with Good | Romans 12:17, 21 |

**Week 4 · God's Family**

| Day | Title | Scripture |
|---|---|---|
| 19 | One Body, Many Parts | 1 Corinthians 12:12, 27 |
| 20 | Your Gift | 1 Peter 4:10 |
| 21 | Honor the Gray Head | Leviticus 19:32 |
| 22 | Welcome the Little Ones | Mark 9:35–37 |
| 23 | Carry Each Other's Burdens | Galatians 6:2 |
| 24 | Rejoice and Weep | Romans 12:15 |

**Week 5 · Loving the World**

| Day | Title | Scripture |
|---|---|---|
| 25 | Every Nation | Revelation 7:9 |
| 26 | The Least of These | Matthew 25:35–36, 40 |
| 27 | Always Ready | 1 Peter 3:15 |
| 28 | Tell Your Story | Mark 5:19–20 |
| 29 | Pray for Everyone | 1 Timothy 2:1–4 |
| 30 | By This Everyone Will Know | John 13:34–35 |

Conclusion: A Tree That Gives Shade

---

## Book 6 — Bearing Fruit

*Bearing Fruit: God's purpose for your life, now and forever*

Introduction: Made for a Purpose

**Week 1 · God's Plan for You**

| Day | Title | Scripture |
|---|---|---|
| 1 | Chosen to Bear Fruit | John 15:16 |
| 2 | God's Masterpiece | Ephesians 2:8–10 |
| 3 | Plans for Hope | Jeremiah 29:11 |
| 4 | Straight Paths | Proverbs 3:5–6 |
| 5 | Speak, Lord | 1 Samuel 3:10 |
| 6 | Don't Let Anyone Look Down on You | 1 Timothy 4:12 |

**Week 2 · Gifts and Work**

| Day | Title | Scripture |
|---|---|---|
| 7 | Well Done | Matthew 25:21 |
| 8 | All for God's Glory | 1 Corinthians 10:31 |
| 9 | Ten Times Better | Daniel 1:17, 20 |
| 10 | Where Your Treasure Is | Matthew 6:19–21 |
| 11 | Honor God First | Proverbs 3:9–10 |
| 12 | Made for Rest | Mark 2:27 |

**Week 3 · Your Body and Your Time**

| Day | Title | Scripture |
|---|---|---|
| 13 | A Temple | 1 Corinthians 6:19–20 |
| 14 | A Time for Everything | Ecclesiastes 3:1; Ecclesiastes 3:11 |
| 15 | Make the Most of Your Time | Ephesians 5:15–16 |
| 16 | Wise and Innocent | Matthew 10:16 |
| 17 | In His Image | Genesis 1:27 |
| 18 | Tend the Garden | Genesis 2:15 |

**Week 4 · Leading and Serving**

| Day | Title | Scripture |
|---|---|---|
| 19 | The Greatest Serve | Mark 10:43–45 |
| 20 | A Great Work | Nehemiah 6:3 |
| 21 | For Such a Time as This | Esther 4:14 |
| 22 | Speak Up | Proverbs 31:8–9 |
| 23 | An Example | Titus 2:7 |
| 24 | He Will Finish It | Philippians 1:6 |

**Week 5 · Looking Ahead**

| Day | Title | Scripture |
|---|---|---|
| 25 | I Will Come Back | John 14:1–3 |
| 26 | No More Tears | Revelation 21:3–5 |
| 27 | Run the Race | Hebrews 12:1–2 |
| 28 | Keep Growing | 2 Peter 3:18 |
| 29 | Finishing Well | 2 Timothy 4:6–8 |
| 30 | Rooted for Life | Psalm 1:1–3 |

Conclusion: Rooted and Built Up
