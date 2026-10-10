# Tell Me the Story: outline

The Bible's own stories retold for children aged 6 to 10 (an Ochorus Original), short enough to read aloud at bedtime. The name comes from Katherine Hankey's hymn *Tell Me the Old, Old Story* (1866, public domain). The manuscripts in this folder (`tell-me-the-story-<n>.md`) are the source of truth; `build_tell_me_the_story` converts them (the closed Markdown subset of `build_rooted.parse`), lifts each story's questions into `Chapter.study_questions`, and checks the shape.

It sits below *The Big Story* (the whole Bible for ages 13 to 17) and beside *Brave for God* (true lives for ages 8 to 12). *Hurlbut's Life of Christ for Young and Old* stays the classic for older readers.

## Stance

Mainstream evangelical, as *The Big Story*. The Bible is God's true Word, and God is the hero of every story: a story ends "God kept His promise", not "be brave like David". Where Christians genuinely differ (how long the days of Genesis 1 were, and so on), a children's story simply tells what the text says and doesn't argue.

## Faithfulness rules

- **Nothing invented and passed off as Scripture.** A story may add small, plain scene-setting a child needs (the heat, the dark, how far a walk is), but never a new event, a new character or a speech the Bible doesn't give.
- **Speech stays close to the text.** People in the story say what the Bible says they said, in simple words. Anything set in quotation marks with a reference in brackets is exact BSB.
- **Hard stories are told honestly, without gore.** Cain and Abel, the flood, Moriah and Joseph's brothers are in the Bible for a reason; the stories say what happened in a sentence and move on to what God did.
- **Every Jesus link comes from the New Testament itself.** A story gets a "Looking ahead to Jesus" line only where the New Testament makes the link (John 1:51 for Jacob's ladder, Hebrews 12:24 for Abel). Where it doesn't (Babel, Rebekah, Hagar), there is no link.

## Each story

- **Opening verse:** a `>` blockquote, `"…" — Book 1:2`, exact BSB (checked by script). The young-reader layout draws it as a card.
- **The story:** about 400 to 600 words, about four minutes read aloud at the gentle 0.9× speed. Short sentences, real names, British spelling. "He" is capitalised for God, as in the BSB.
- `**Looking ahead to Jesus:**` one or two sentences, only where the New Testament links the story to Jesus.
- `**Read it in your Bible:**` the passage, for a grown-up to read alongside or an older child to read alone.
- **A closing prayer:** the last paragraph, all in italics, ending "Amen." The layout draws it as the "now we pray" card.
- `### Talk about it together`: three questions, each `- Q:` with an `  A:` line beneath. Two recall the story; the third brings it home. The answers are for the grown-up reading along. The build moves them into `Chapter.study_questions`, where the reader folds the answers and read-aloud speaks only the questions.

## The series: eight books in three parts

**Old Testament Stories**
1. In the Beginning (Genesis): creation to Joseph
2. Out of Egypt (Exodus to Ruth): baby Moses, the Passover, the Red Sea, Sinai, Jericho, Deborah, Gideon, Ruth
3. Kings and Prophets (1 Samuel to Malachi): Hannah, Samuel, David, Solomon, Elijah, Naaman, Jonah, Daniel, Esther, Nehemiah

**The Life of Jesus**
4. The King Is Born: Jesus' birth, the boy in the temple, His baptism, the first disciples, the woman at the well
5. Wonders and Stories: the storm stilled, the 5,000 fed, Jairus's daughter, Zacchaeus, the lost son, the good Samaritan
6. The Greatest Rescue: Palm Sunday, the Last Supper, the cross, the empty tomb, Emmaus, breakfast by the sea, the ascension

**New Testament Stories**
7. The Church Begins: Pentecost, the lame man healed, Stephen, Philip and the Ethiopian, Saul, Dorcas, Peter in prison
8. To the Ends of the Earth: Lydia, the jailer, Priscilla and Aquila, the shipwreck, Onesimus, John on Patmos

## Book 1: In the Beginning

An Introduction (for the child, with a note for grown-ups, and its own three questions: the reader wants questions on every chapter or none), then twenty-one stories from Genesis.

1. God Makes Everything (Genesis 1:1–2:3)
2. A Garden for Adam and Eve (Genesis 2)
3. The Snake's Trick (Genesis 3)
4. Two Brothers (Genesis 4:1–16)
5. Noah Builds a Boat (Genesis 6–8)
6. The Rainbow Promise (Genesis 8:15–9:17)
7. The Tower That Reached Too High (Genesis 11:1–9)
8. Abram Sets Out (Genesis 12:1–9)
9. Count the Stars (Genesis 15:1–6)
10. Sarah Laughs (Genesis 18:1–15; 21:1–7)
11. The God Who Sees (Genesis 16; 21:8–21)
12. God Will Provide (Genesis 22:1–19)
13. A Bride at the Well (Genesis 24)
14. Twin Brothers (Genesis 25:19–34; 27)
15. A Stairway to Heaven (Genesis 28:10–22)
16. Jacob Wrestles (Genesis 32–33)
17. Joseph's Colourful Robe (Genesis 37)
18. Joseph in Prison (Genesis 39–40)
19. Pharaoh's Dreams (Genesis 41)
20. The Brothers Come to Egypt (Genesis 42–44)
21. "I Am Joseph!" (Genesis 45; 50:15–21)

## Checking

- Every opening verse, and every quotation with a reference in brackets, against the BSB text, by script.
- Ages, numbers and names against the chapter (Abram 75, Abraham 100, Joseph 17 and 30, twenty pieces of silver).
- The English audit, and the house title case.
