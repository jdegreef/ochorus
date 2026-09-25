"""Build a volume of a house 30-day devotional series from its manuscript.

*Rooted – 30 Days with God for Youth* and its sister series for girls and
boys, *Daughters of the King* and *Sons of the King*: devotionals for readers aged 9–12, every day a BSB
Scripture, a short teaching, "Think about it" / "Try this", and a prayer. Each
book also has an Introduction and a Conclusion, so a volume is 32 chapters: the
introduction, Day 1 … Day 30, the conclusion.

The prose is committed as Markdown under ``data/<series>/<series>-<n>.md``
(Ochorus's own writing, nothing fetched) and converted here, so adding a book is
a new manuscript plus one entry in that series' volume table in ``SERIES``.
The Markdown is a closed subset — the
manuscripts are written to it, so anything else is an error, not a guess:

    ## Heading            starts a chapter (its title)
    ### Heading           a section heading inside a chapter (<h2>)
    > line                a blockquote line; each line is its own <p>
    - item / 1. item      list items
    **bold**, *italic*    inline
    # Heading, ---        structure for the manuscript's reader only; dropped

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/<series>-<n>.en.json``. Idempotent. The series row
itself lives in ``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_rooted 1
    DJANGO_DEBUG=true uv run python manage.py build_rooted 1 --series daughters-of-the-king
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

DATA_DIR = Path(__file__).resolve().parent / "data"
AUTHOR_SLUG = "ochorus-originals"
DAYS = 30

ATTRIBUTION = (
    "An Ochorus Original, written for young readers. Scripture quotations are "
    "from the Berean Standard Bible (BSB), which is in the public domain."
)

# Per volume: the Book fields. `sort_order` is fixed here rather than taken from
# the dev DB's max, which holds only what has been built locally.
ROOTED: dict[int, dict[str, object]] = {
    1: {
        "sort_order": 75,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 1",
        "subtitle": "Planted: knowing God, receiving Jesus, and learning to grow",
        # Asserted here, not left to `generate_covers`, so a rebuild in a fresh
        # worktree (empty DB) cannot serialize a fixture with no cover.
        "cover_url": "/covers/rooted-1.svg",
        "cover_color": covers.ink_safe("#3f6b3a"),  # a deep leaf green
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12. Each day opens "
            "with a verse from the Bible, explains what it means for a young "
            "reader’s life, asks one question to think about and one thing to "
            "try, and ends with a prayer. Book 1 plants the roots: who God is, the "
            "good news of Jesus, who you are in Christ, how to pray, and how the "
            "Bible, church and worship help you grow. The first book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its first book. Its picture is a tree: a tree with "
            "deep roots keeps standing when the storms come, and Colossians 2:7 "
            "asks the same of us, to be rooted and built up in Christ. Six books "
            "of thirty days each walk that picture from the roots to the fruit.</p>"
            "<p>Book 1 lays the foundation over five weeks. The first asks who God "
            "is: the Creator who names every star, holy and full of love, and "
            "never changing. The second tells the best news ever, from the garden "
            "to the cross and the empty tomb, and ends with a clear, gentle "
            "invitation to trust Jesus. The third shows a young reader who they "
            "are in Christ: made on purpose, a child of God, forgiven, never "
            "alone. The fourth teaches prayer through the Lord’s Prayer, and the "
            "fifth shows how the Bible, obeying, church and worship make the roots "
            "grow deep.</p>"
            "<p>Every day follows the same short pattern, a few minutes long: a "
            "Scripture from the Berean Standard Bible, a teaching told with a "
            "story or a picture from everyday life, a question to think about, one "
            "thing to try that day, and a prayer to pray. It is written to be read "
            "alone by a young reader, and it works just as well read aloud at "
            "bedtime or around the table, where the questions make good "
            "conversation starters.</p>"
        ),
        "qa": [
            {
                "question": "What is Rooted – 30 Days with God for Youth?",
                "answer": "A series of short daily devotions for readers aged 9 to 12. Each day has a verse from the Bible, a few minutes of teaching about what it means, a question to think about, one thing to try that day, and a prayer. This is Book 1 of six.",
            },
            {
                "question": "What does Book 1 cover?",
                "answer": "It plants the roots of faith over five weeks: who God is, the good news of Jesus from the garden to the empty tomb, who you are in Christ, how to talk with God in prayer, and how the Bible, obeying, church and worship help you grow.",
            },
            {
                "question": "Why is the series called Rooted?",
                "answer": "Because of Colossians 2:6–7, which asks those who have received Christ Jesus as Lord to be “rooted and built up in Him.” A tree with deep roots keeps standing when storms come, and the series helps young readers grow deep roots in Jesus one day at a time.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "Can a parent read it with a child?",
                "answer": "Yes. It is written for young readers to read on their own, but it works just as well read aloud together. The “Think about it” questions make good conversation starters at bedtime or around the table.",
            },
            {
                "question": "What if I miss a day?",
                "answer": "Just pick up where you left off. The book is not a test, and God is not keeping score. What matters is spending time with Him and letting your roots keep growing.",
            },
        ],
    },
    2: {
        "sort_order": 76,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 2",
        "subtitle": "Following Jesus: walking with Jesus from the manger to the empty tomb",
        "cover_url": "/covers/rooted-2.svg",
        "cover_color": covers.ink_safe("#7a4a2a"),  # a rich soil brown
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 that walk "
            "through the life of Jesus, from the manger in Bethlehem to the empty "
            "tomb. Each day opens with a passage from the Gospels, shows what it "
            "reveals about Jesus, asks one question to think about and one thing "
            "to try, and ends with a prayer. The second book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its second book. Book 1 planted the roots: who God "
            "is, the good news, and how to pray and grow. Book 2 turns to the one "
            "those roots grow into, and spends thirty days walking beside Jesus "
            "through His life on earth, drawing on all four Gospels.</p>"
            "<p>The five weeks follow His story in order. Jesus arrives: the "
            "manger, the shepherds, the wise men, and the twelve-year-old in His "
            "Father’s house. Jesus begins: His baptism, His temptation in the "
            "wilderness, and the fishermen He called to follow Him. Jesus’ power: "
            "a storm stilled, a boy’s lunch that fed thousands, a blind beggar "
            "healed and Lazarus called out of the tomb. Jesus’ teaching: the "
            "Beatitudes, salt and light, the lost sheep, the runaway son and the "
            "good Samaritan. And Jesus wins: Zacchaeus, the donkey and the "
            "palm branches, the towel and basin, the cross and the empty tomb, "
            "ending with the Great Commission.</p>"
            "<p>Every day follows the same short pattern: a passage from the "
            "Berean Standard Bible, a teaching that tells the story and asks what "
            "it shows about Jesus, a question to think about, one thing to try "
            "that day, and a prayer. It can be read alone or aloud together, and "
            "it works whether or not a reader has started with Book 1.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 2 of Rooted about?",
                "answer": "It walks young readers through the life of Jesus in thirty short daily devotions, from His birth in Bethlehem to His resurrection and His last command to go and make disciples. Each day has a Bible passage, a short teaching, a question, something to try and a prayer.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. The stories come from all four Gospels, so it also makes a good first walk through the life of Christ.",
            },
            {
                "question": "Do I need to read Book 1 first?",
                "answer": "No. Book 2 stands on its own, and its introduction explains how each day works. Book 1 lays the foundation (who God is, the good news of Jesus and how to pray), so reading it first helps, but you can start right here.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "How does it handle the crucifixion?",
                "answer": "Honestly but gently. Week 5 tells the story of Jesus’ arrest, the cross and the empty tomb in words suited to young readers, focusing on why Jesus died and what His resurrection means.",
            },
            {
                "question": "What comes after Book 2?",
                "answer": "Book 3, which is about growing fruit: how staying connected to Jesus, the vine, grows love, joy, peace, kindness and self-control, and shapes the words we say and the habits we build.",
            },
        ],
    },
    3: {
        "sort_order": 77,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 3",
        "subtitle": "Growing Fruit: the fruit of the Spirit, the words we say, and the habits of the heart",
        "cover_url": "/covers/rooted-3.svg",
        "cover_color": covers.ink_safe("#5a3a6e"),  # a ripe-grape purple
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 about the "
            "fruit God grows in those who stay connected to Jesus, the Vine: "
            "love, joy, peace, patience, kindness and more, the words we say, the "
            "habits of the heart, and being wise and honest. Each day has a Bible "
            "verse, a short teaching, a question, something to try and a prayer. "
            "The third book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its third book. Book 1 planted the roots and Book "
            "2 walked with Jesus through His life. Book 3 asks what grows on a "
            "tree that is rooted in Him, and its answer begins where Jesus did: "
            "“I am the vine and you are the branches.” Good fruit is not glued on "
            "by trying harder. It grows from staying connected to the Vine.</p>"
            "<p>The first two weeks take the fruit of the Spirit one at a time, "
            "from love, joy and peace to gentleness and self-control, with a day "
            "on humility as the soil the rest grow in. The third week is about "
            "words: the tiny spark of the tongue, telling the truth, words that "
            "build, grumbling, gossip and listening. The fourth turns to habits of "
            "the heart: respect, thankfulness, working as for the Lord, "
            "contentment, generosity and guarding the heart. The fifth is about "
            "being pure and wise: asking for wisdom, what we think about and "
            "watch, integrity when no one is looking, and the fall that pride "
            "brings.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching with a Bible story or a picture "
            "from everyday life, a question to think about, one thing to try, and "
            "a prayer. It is written to keep character rooted in grace, pointing "
            "young readers back to Jesus and His Spirit rather than to "
            "self-improvement, and it can be read alone or aloud together.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 3 of Rooted about?",
                "answer": "Growing fruit. Over thirty short daily devotions it looks at the fruit of the Spirit, the words we say, the habits of the heart, and being wise and honest, always starting from Jesus’ words: “I am the vine and you are the branches.”",
            },
            {
                "question": "Is it just a list of rules for being good?",
                "answer": "No. Its main point is that you cannot grow good fruit by trying harder on your own. Fruit grows by staying connected to Jesus, as His Spirit works in you. Every day points back to Him.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. The week on words and the day on screens make especially good family conversations.",
            },
            {
                "question": "Do I need to read Books 1 and 2 first?",
                "answer": "No. Each book stands on its own, and the introduction explains how each day works. The earlier books lay the foundation and walk through the life of Jesus, so reading them first helps, but you can start here.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 3?",
                "answer": "Book 4, about standing strong in the storms of life: fear, worry, sadness, temptation and unfairness, with Bible heroes like David, Daniel, Joseph and Esther, and the promise that nothing can separate us from God’s love.",
            },
        ],
    },
    4: {
        "sort_order": 78,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 4",
        "subtitle": "Strong in the Storm: courage for when you’re afraid, sad, tempted or treated unfairly",
        "cover_url": "/covers/rooted-4.svg",
        "cover_color": covers.ink_safe("#34495e"),  # a storm-cloud slate
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 about standing "
            "strong in the storms of life: fear, worry, sadness and grief, "
            "temptation, and times when life isn’t fair. With David, Joseph, "
            "Daniel, his three friends and Esther, and the armor of God. Each day "
            "has a Bible verse, a short teaching, a question, something to try "
            "and a prayer. The fourth book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its fourth book. It begins with Jesus’ story of "
            "two builders: the storm hit both houses, and the one on the rock "
            "stood. Storms come to everyone, and Book 4 is about the foundation "
            "that holds when they do.</p>"
            "<p>The first week is about fear, with David’s trust, the Shepherd "
            "of Psalm 23, Joshua’s courage, Goliath, and sleeping in peace. The "
            "second is about worry and sadness: casting cares on God, praying "
            "instead of worrying, Jesus weeping, grieving with hope when someone "
            "dies, and God as Father when home is hard. The third faces "
            "temptation with Joseph and Daniel, and teaches how to get back up "
            "after a fall. The fourth puts on the armor of God and stands with "
            "Shadrach, Meshach and Abednego, Daniel in the lions’ den, and "
            "Esther. The fifth holds on to hope: Joseph’s “God intended it for "
            "good,” God’s higher ways, wings like eagles, grace that is enough, "
            "and the love nothing can separate us from.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. The days on grief and on a hard home "
            "are written gently and point readers to a trusted adult, and "
            "several days remind them to tell a trusted adult if anyone is "
            "hurting them.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 4 of Rooted about?",
                "answer": "Standing strong in the storms of life. Over thirty short daily devotions it helps young readers face fear, worry, sadness, temptation and unfairness by trusting God, with stories of David, Joseph, Daniel, his three friends and Esther.",
            },
            {
                "question": "Does it talk about hard things like death or trouble at home?",
                "answer": "Yes, gently. Day 10 is about grieving with hope when someone dies, and Day 11 is about when home is hard. Both encourage readers to talk with a trusted adult, and parents may want to read those days together with their child.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. It is especially helpful for a child who is going through something scary or sad.",
            },
            {
                "question": "Do I need to read the earlier books first?",
                "answer": "No. Each book of Rooted stands on its own, and the introduction explains how each day works. The earlier books help, but you can start here.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 4?",
                "answer": "Book 5, about how God’s love reaches out through us: loving family, being a true friend, forgiving, belonging to God’s family at church, and caring about people all over the world.",
            },
        ],
    },
    5: {
        "sort_order": 79,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 5",
        "subtitle": "Branching Out: loving your family, your friends, God’s family and the world",
        "cover_url": "/covers/rooted-5.svg",
        "cover_color": covers.ink_safe("#8a3b2e"),  # an autumn-leaf red
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 about how God’s "
            "love reaches out through us: honoring parents and loving siblings, "
            "being a true friend, forgiving and making peace, belonging to God’s "
            "family at church, and loving the whole world. Each day has a Bible "
            "verse, a short teaching, a question, something to try and a prayer. "
            "The fifth book of Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its fifth book. It begins with the two greatest "
            "commandments, to love God and to love your neighbor, and pictures "
            "them as a tree: roots going down to God and branches reaching out to "
            "people. The earlier books grew the roots. Book 5 is about the "
            "branches.</p>"
            "<p>The first week is love at home: honoring parents, brothers and "
            "sisters, serving one another, hearing a parent’s no, and “as for me "
            "and my house.” The second is about friends: a friend who loves at all "
            "times, David and Jonathan, walking with the wise, Hagar and the God "
            "who sees, and welcoming the one on the edge. The third is about "
            "forgiveness and peace: seventy-seven times, making things right, "
            "being a peacemaker, loving enemies and overcoming evil with good. "
            "The fourth is about God’s family, the church, and the fifth reaches "
            "out to the world, from every nation and the least of these to "
            "telling your own story of what Jesus has done.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching with a Bible story or a picture "
            "from everyday life, a question to think about, one thing to try, and "
            "a prayer. The days on honoring parents, forgiveness and bullies make "
            "clear that no one should be asked to do something wrong or unsafe, "
            "that forgiving is not the same as staying where you can be hurt, and "
            "that a reader who is being bullied should tell a trusted adult.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 5 of Rooted about?",
                "answer": "How God’s love reaches out through us. Over thirty short daily devotions it looks at loving family, being a true friend, forgiving and making peace, belonging to God’s family at church, and loving people all over the world.",
            },
            {
                "question": "How does it handle bullying?",
                "answer": "Carefully. Day 17 teaches Jesus’ command to love our enemies, and it makes clear that loving an enemy never means letting them keep hurting you. It tells readers who are being bullied that it is not their fault and to tell a trusted adult until someone helps.",
            },
            {
                "question": "Does forgiving someone mean pretending it didn’t hurt?",
                "answer": "No. Days 13 and 14 explain that forgiving means letting go of revenge and giving the hurt to God. It does not mean saying the wrong was okay, trusting someone again right away, or staying where you can be hurt.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. Each book of Rooted stands on its own, so it can be read with or without the earlier books.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 5?",
                "answer": "Book 6, the last book of Rooted, about bearing fruit: God’s purpose for your life, using your gifts and time well, leading by serving, finishing well, and looking ahead to the day Jesus returns.",
            },
        ],
    },
    6: {
        "sort_order": 80,
        "publication_year": 2026,
        "title": "Rooted – 30 Days with God for Youth – Book 6",
        "subtitle": "Bearing Fruit: God’s purpose for your life, now and forever",
        "cover_url": "/covers/rooted-6.svg",
        "cover_color": covers.ink_safe("#9a6a1f"),  # a harvest gold
        "description": (
            "Thirty short daily devotions for readers aged 9 to 12 about God’s "
            "purpose for their lives: chosen and created for good works, using "
            "gifts, schoolwork, money, time and rest for God, caring for the body "
            "He made, serving and speaking up, and looking ahead to Jesus’ return "
            "and the new creation. Each day has a Bible verse, a short teaching, a "
            "question, something to try and a prayer. The sixth and final book of "
            "Rooted."
        ),
        "about_html": (
            "<p>Rooted is an original Ochorus devotional series for readers aged 9 "
            "to 12, and this is its sixth and final book. The series has followed "
            "one picture from the start: a tree planted, rooted in Christ, growing "
            "fruit, standing through storms and branching out in love. Book 6 asks "
            "what all that growing is for, and answers with Jesus’ words: “I chose "
            "you. And I appointed you to go and bear fruit—fruit that will "
            "remain.”</p>"
            "<p>The first week is about God’s plan: chosen, created as His "
            "workmanship for good works, plans for a future and a hope, and young "
            "Samuel listening. The second is about gifts and work, from the "
            "parable of the talents and Daniel at school to treasure, giving and "
            "rest. The third is about the body and time: the body as a temple, the "
            "seasons of growing up, redeeming the time, wisdom online, and male "
            "and female made in God’s image. The fourth is about leading by "
            "serving, with Nehemiah, Esther and speaking up for those with no "
            "voice. The fifth looks ahead to Jesus’ return, a new creation with no "
            "more tears, running the race and finishing well, and ends the series "
            "with the tree of Psalm 1, planted by streams of water.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. The days on growing up speak in general "
            "terms and send readers to their parents with their questions, and "
            "the book includes simple body-safety and online-safety guidance. Its "
            "conclusion returns to Colossians 2:6–7, the verse that opened the "
            "series.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 6 of Rooted about?",
                "answer": "God’s purpose for your life. Over thirty short daily devotions it looks at being chosen and created for good works, using your gifts, time and money for God, caring for your body, leading by serving, and the hope of Jesus’ return.",
            },
            {
                "question": "Does it talk about growing up?",
                "answer": "Gently and in general terms. Day 14 says the changes of growing up are part of God’s good design and encourages readers to take their questions to a parent or trusted adult. Day 13 includes a short body-safety note, and Day 16 covers staying safe online.",
            },
            {
                "question": "Is this the last book of Rooted?",
                "answer": "Yes. It is the sixth and final book. Its last day and its conclusion look back over the whole series, from being planted in Book 1 to bearing fruit in Book 6, and suggest ways to keep growing afterward.",
            },
            {
                "question": "Who is it for?",
                "answer": "Readers aged 9 to 12, to read on their own or with a parent, grandparent or leader. Each book of Rooted stands on its own, so it can be read with or without the earlier books.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What should a reader do after finishing Rooted?",
                "answer": "Keep growing: read a whole book of the Bible such as the Gospel of John, keep a prayer journal, find an older Christian to read and pray with, serve at church, and read true stories of faith like the Brave for God books.",
            },
        ],
    },
}

DAUGHTERS_OF_THE_KING: dict[int, dict[str, object]] = {
    1: {
        "sort_order": 81,
        "publication_year": 2026,
        "title": "Daughters of the King – 30 Days with God for Girls – Book 1",
        "subtitle": "Beloved: who you are, whose you are, and the brave girls who went before you",
        "cover_url": "/covers/daughters-of-the-king-1.svg",
        "cover_color": covers.ink_safe("#8e3b5a"),  # a deep rose
        "description": (
            "Thirty short daily devotions for girls aged 9 to 12 about who they "
            "are as daughters of the King: worth that comes from God, not from "
            "looks or popularity; escaping the comparison trap; friendship "
            "without drama; and the brave girls of the Bible, from Miriam and "
            "Deborah to Ruth, Abigail and Mary. Each day has a Bible verse, a "
            "short teaching, a question, something to try and a prayer. The "
            "first book of Daughters of the King."
        ),
        "about_html": (
            "<p>Daughters of the King is an original Ochorus devotional series for "
            "girls aged 9 to 12, a sister to our co-ed series Rooted. Its anchor "
            "is God’s promise in 2 Corinthians 6:18: “I will be a Father to you, "
            "and you will be My sons and daughters.” This first book is about "
            "identity: who a girl is, and whose she is, when the world keeps "
            "telling her she has to be prettier, more popular or more "
            "impressive.</p>"
            "<p>The first week hears what God says about her: called by name, "
            "made to reflect Him, seen at the heart, beautiful with a gentle and "
            "quiet spirit, His daughter, sung over with joy. The second takes "
            "apart the comparison trap, with Leah the sister nobody noticed, "
            "filters and feeds, contentment, and Elizabeth celebrating Mary. The "
            "third is about friendship and words, from Ruth and Naomi to cliques, "
            "drama and honey-sweet words. The fourth meets the brave girls of the "
            "Bible: Miriam, Deborah, Abigail, Rahab, Naaman’s servant girl and "
            "Mary. The fifth turns to a heart for God with Hannah, Mary of "
            "Bethany, the woman with the perfume and Lydia.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. Each week ends with a true story from "
            "our Brave for God books: Amy Carmichael, Gladys Aylward, Corrie ten "
            "Boom, Mary Slessor and Mary Jones. The book builds character and "
            "faith through the women of Scripture and does not teach adult roles. "
            "Many girls will enjoy reading it with a mother, grandmother or "
            "mentor.</p>"
        ),
        "qa": [
            {
                "question": "What is Daughters of the King about?",
                "answer": "It is a devotional series for girls aged 9 to 12. Book 1 helps girls know who they are in God’s eyes: loved, chosen and made on purpose, with worth that comes from Him rather than from looks, popularity or comparison.",
            },
            {
                "question": "How is it different from Rooted?",
                "answer": "Rooted is for all young readers and covers the foundations of faith. Daughters of the King speaks to things girls often face in their own way, like comparison, appearance and friendship drama, and it tells the stories of women and girls in the Bible and in history who trusted God.",
            },
            {
                "question": "Which women of the Bible does it include?",
                "answer": "Leah, Elizabeth, Ruth and Naomi, Miriam, Deborah, Abigail, Rahab, the servant girl in Naaman’s house, Mary the mother of Jesus, Hannah, Mary and Martha, the woman who poured perfume on Jesus, and Lydia.",
            },
            {
                "question": "Who are the true stories at the end of each week?",
                "answer": "Five women from our Brave for God books: Amy Carmichael, Gladys Aylward, Corrie ten Boom, Mary Slessor and Mary Jones. Each short story shows a real woman who trusted God, and the full stories are in the Brave for God series.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 1?",
                "answer": "Book 2 is about being brave: facing worry and anxiety, using your voice, serving and leading, and following Jesus like the women who stayed with Him to the cross and the empty tomb.",
            },
        ],
    },
    2: {
        "sort_order": 83,
        "publication_year": 2026,
        "title": "Daughters of the King – 30 Days with God for Girls – Book 2",
        "subtitle": "Brave: courage for worry, a voice to speak, and hands to serve",
        "cover_url": "/covers/daughters-of-the-king-2.svg",
        "cover_color": covers.ink_safe("#6b3f7a"),  # a brave violet
        "description": (
            "Thirty short daily devotions for girls aged 9 to 12 about being "
            "brave: facing worry and fear with God, using your voice to speak up "
            "and say no, serving like Phoebe, Priscilla and Dorcas, leading like "
            "Miriam, and following Jesus like the women who stayed at the cross "
            "and saw the empty tomb. Each day has a Bible verse, a short "
            "teaching, a question, something to try and a prayer. The second book "
            "of Daughters of the King."
        ),
        "about_html": (
            "<p>Daughters of the King is an original Ochorus devotional series for "
            "girls aged 9 to 12. Book 1 taught a girl who she is. Book 2 asks what "
            "that means for how she lives, and its answer is courage: not being "
            "fearless, but knowing Someone bigger than her fear. It opens with "
            "Psalm 27:1: “The LORD is my light and my salvation—whom shall I "
            "fear?”</p>"
            "<p>The first week faces worry, from anxious thoughts and sleepless "
            "nights to worries about appearance and the “what ifs” of tomorrow. "
            "The second is about using her voice: the five daughters of Zelophehad "
            "who spoke up and were told they were right, saying no, secrets that "
            "hurt, asking for help and speaking the truth in love. The third meets "
            "women who served, including Phoebe, Priscilla, Dorcas and the widow "
            "of Zarephath. The fourth is about leading, with Miriam, the queen of "
            "Sheba, Lois and Eunice. The fifth follows the women who followed "
            "Jesus, to the cross and to the garden where Mary Magdalene heard Him "
            "say her name.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. Each week ends with a true story from "
            "our Brave for God books: Helen Roseveare, Pandita Ramabai, Ida "
            "Scudder, Elisabeth Elliot and Lilias Trotter. Day 10 is a simple "
            "body-safety day about secrets that hurt, and the days on worry "
            "encourage girls to tell a parent when worry grows big.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 2 of Daughters of the King about?",
                "answer": "Being brave. Over thirty short daily devotions it helps girls face worry and fear with God, use their voices well, serve others, lead by example, and follow Jesus like the brave women in the Gospels.",
            },
            {
                "question": "Does it help with anxiety and worry?",
                "answer": "Yes. The first week is about worry, fear, sleep and the ‘what ifs’. It points girls to God’s promises and comfort, and it encourages them to tell a parent or trusted adult if worry becomes very big, saying there is no shame in getting help.",
            },
            {
                "question": "What does it teach about staying safe?",
                "answer": "Day 10 explains the difference between good surprises and secrets that hurt. It teaches that no one should ask a child to keep a secret about touching, pictures or anything that makes her uncomfortable, that it is never her fault, and that telling a trusted adult is always right.",
            },
            {
                "question": "Which women does it include?",
                "answer": "From the Bible: the daughters of Zelophehad, Phoebe, Priscilla, Dorcas, the widow of Zarephath, Miriam, the queen of Sheba, Lois and Eunice, Mary Magdalene, Joanna, the woman who touched Jesus’ cloak and the Canaanite mother. From history, in the weekly true stories: Helen Roseveare, Pandita Ramabai, Ida Scudder, Elisabeth Elliot and Lilias Trotter.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 2?",
                "answer": "Book 3 is about growing up: feelings and emotions, how God designed a girl’s body and the changes that come as she grows, wise choices, discovering her calling, and finding women who can help her grow.",
            },
        ],
    },
    3: {
        "sort_order": 85,
        "publication_year": 2026,
        "title": "Daughters of the King – 30 Days with God for Girls – Book 3",
        "subtitle": "Growing Up: your feelings, your changing body, wise choices, and God’s calling",
        "cover_url": "/covers/daughters-of-the-king-3.svg",
        "cover_color": covers.ink_safe("#2f6b5e"),  # a deep, growing green
        "description": (
            "Thirty short daily devotions for girls aged 9 to 12 about growing "
            "up: handling big feelings with God, understanding the changes of "
            "puberty as His good design, making wise choices about crushes, "
            "money, time and life online, discovering her gifts and calling, and "
            "learning from older women like Naomi, Elizabeth and Anna. Each day "
            "has a Bible verse, a short teaching, a question, something to try "
            "and a prayer. The third and final book of Daughters of the King."
        ),
        "about_html": (
            "<p>Daughters of the King is an original Ochorus devotional series for "
            "girls aged 9 to 12. Book 1 taught a girl who she is, and Book 2 how "
            "to be brave. Book 3 walks with her into growing up, and it opens "
            "with a prayer from Psalm 144:12 that daughters would be “like corner "
            "pillars carved to adorn a palace”: strong, and shaped with care.</p>"
            "<p>The first week is about feelings: anger, sadness, embarrassment, "
            "moody days, and taking every thought captive. The second speaks "
            "openly and simply about puberty: growth and body shape, breast "
            "development and body hair, periods, hygiene, and hormones and "
            "changing moods, all as part of God’s good design. It leaves questions "
            "about sex and reproduction to parents, and every day sends a girl "
            "back to her mother or a woman she trusts. The third week is about "
            "wise choices: crushes, money, time, being careful online and a pure "
            "heart. The fourth is about calling: gifts, dreams, and God pouring out "
            "His Spirit on His daughters. The fifth is about mentors and "
            "finishing well, with Naomi, Elizabeth and Anna.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. Each week ends with a true story from "
            "our Brave for God books: Amy Carmichael, Ida Scudder, Gladys "
            "Aylward, Lottie Moon and Mary Slessor. A note for parents recommends "
            "reading the growing-up week together.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 3 of Daughters of the King about?",
                "answer": "Growing up. Over thirty short daily devotions it helps girls handle big feelings, understand how their bodies change, make wise choices, discover their gifts and calling, and learn from older women who love God.",
            },
            {
                "question": "Does it talk about puberty and periods?",
                "answer": "Yes. Week 2 explains simply and accurately how a girl’s body changes: growing taller, body shape, breast development, body hair, periods, hygiene and changing moods. It presents all of it as God’s good design, nothing to be ashamed of, and encourages her to ask her mother or a trusted woman her questions. Sex and reproduction are left for parents to discuss.",
            },
            {
                "question": "Should parents read it with their daughter?",
                "answer": "We recommend it, especially for Week 2. A note for parents at the start explains exactly what that week covers, and each day of it ends by pointing a girl to her mother or another woman she trusts.",
            },
            {
                "question": "What does it say about crushes and dating?",
                "answer": "Day 14 uses Song of Songs 2:7, “Do not arouse or awaken love until the time is right.” It tells girls that crushes are normal, that there is no need to rush into dating, that their worth does not depend on whether a boy likes them, and to talk openly with their parents.",
            },
            {
                "question": "Which women does it include?",
                "answer": "From the Bible: Ruth and Naomi, Mary and Elizabeth, and Anna the prophetess, among others. From history, in the weekly true stories: Amy Carmichael, Ida Scudder, Gladys Aylward, Lottie Moon and Mary Slessor.",
            },
            {
                "question": "Is this the last book in the series?",
                "answer": "Yes. Daughters of the King has three books: Beloved, Brave and Growing Up. Its companion series for boys is Sons of the King, and our Rooted series is for all young readers.",
            },
        ],
    },
}

SONS_OF_THE_KING: dict[int, dict[str, object]] = {
    1: {
        "sort_order": 82,
        "publication_year": 2026,
        "title": "Sons of the King – 30 Days with God for Guys – Book 1",
        "subtitle": "Strong: who you are, whose you are, and the brave men who went before you",
        "cover_url": "/covers/sons-of-the-king-1.svg",
        "cover_color": covers.ink_safe("#2f4a6b"),  # a deep steel blue
        "description": (
            "Thirty short daily devotions for boys aged 9 to 12 about who they "
            "are as sons of the King: worth that comes from God, not scores or "
            "stats; strength under control; friends who make you better; "
            "courage from Caleb, Jonathan, Elijah and Stephen; and working hard, "
            "keeping your word and standing firm. Each day has a Bible verse, a "
            "short teaching, a question, something to try and a prayer. The "
            "first book of Sons of the King."
        ),
        "about_html": (
            "<p>Sons of the King is an original Ochorus devotional series for "
            "boys aged 9 to 12, a brother to Daughters of the King and our co-ed "
            "series Rooted. Its anchor is God’s promise in 2 Corinthians 6:18: “I "
            "will be a Father to you, and you will be My sons and daughters.” "
            "This first book is about identity and strength: what makes a guy "
            "strong, when the world keeps measuring him by his scores, his "
            "muscles and how tough he looks.</p>"
            "<p>The first week hears what God says about him: a new name like "
            "Peter’s, worth that is more than his score, a son and heir, a "
            "compassionate Father, strength from God, and Gideon, the least. The "
            "second is about strength under control: Samson, anger, Cain and the "
            "sin at the door, revenge, the gentleness of Jesus, and why real men "
            "cry. The third is about friends and brothers, from iron sharpening "
            "iron and Barnabas the encourager to finding a mentor, treating girls "
            "with respect, and standing up for the kid nobody likes. The fourth "
            "is about courage with Caleb, Jonathan, Elijah, Stephen and the boy "
            "king Josiah. The fifth is about work, honor and faith, ending with "
            "“Be men of courage… Do everything in love.”</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. Each week ends with a true story from "
            "our Brave for God books: Samuel Crowther, Festo Kivengere, C.T. "
            "Studd, Eric Liddell and William Carey. The book builds character and "
            "faith through the men of Scripture and does not teach adult roles. "
            "Many boys will enjoy reading it with a father, grandfather or "
            "mentor.</p>"
        ),
        "qa": [
            {
                "question": "What is Sons of the King about?",
                "answer": "It is a devotional series for boys aged 9 to 12. Book 1 helps boys know who they are in God’s eyes and what real strength is: worth that comes from God rather than scores or toughness, and strength that is under control and used in love.",
            },
            {
                "question": "How is it different from Rooted?",
                "answer": "Rooted is for all young readers and covers the foundations of faith. Sons of the King speaks to things boys often face in their own way, like anger, proving themselves, hiding their feelings and friendship, and it tells the stories of men in the Bible and in history who trusted God.",
            },
            {
                "question": "Does it talk about feelings and anger?",
                "answer": "Yes. Week 2 is about strength under control: handling anger, not taking revenge, being gentle like Jesus, and knowing that real men cry, as David and Jesus did.",
            },
            {
                "question": "Who are the true stories at the end of each week?",
                "answer": "Five men from our Brave for God books: Samuel Crowther, Festo Kivengere, C.T. Studd, Eric Liddell and William Carey. Each short story shows a real man who trusted God, and the full stories are in the Brave for God series.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 1?",
                "answer": "Book 2 is about being faithful: integrity when no one is watching, being wise with screens and gaming, handling temptation, winning and losing well, and following Jesus like the disciples.",
            },
        ],
    },
    2: {
        "sort_order": 84,
        "publication_year": 2026,
        "title": "Sons of the King – 30 Days with God for Guys – Book 2",
        "subtitle": "Faithful: integrity, screens, temptation, sports, and following Jesus all the way",
        "cover_url": "/covers/sons-of-the-king-2.svg",
        "cover_color": covers.ink_safe("#2f5d50"),  # a steady forest green
        "description": (
            "Thirty short daily devotions for boys aged 9 to 12 about being "
            "faithful: integrity when no one is watching, staying the boss of "
            "screens and gaming, fighting temptation with God’s help and good "
            "friends, winning and losing well, and following Jesus like Andrew, "
            "Thomas, John and Peter. Each day has a Bible verse, a short teaching, "
            "a question, something to try and a prayer. The second book of Sons "
            "of the King."
        ),
        "about_html": (
            "<p>Sons of the King is an original Ochorus devotional series for boys "
            "aged 9 to 12. Book 1 taught a boy who he is and what real strength "
            "looks like. Book 2 is about being faithful, taking its lead from 1 "
            "Corinthians 4:2: “Now it is required of stewards that they be found "
            "faithful.” God has trusted a boy with his time, his gifts, his body "
            "and his friendships, and faithfulness is what He asks in return.</p>"
            "<p>The first week is about integrity: being real all the way through, "
            "honest scales in games and tests, what God sees when no one else is "
            "watching, and Achan’s treasure hidden in the tent. The second is "
            "about screens and gaming: who is the boss, numbering our days, rage "
            "quitting, staying innocent about evil, not disappearing from real "
            "life, and meeting God first. The third is about temptation, from how "
            "it worked in the garden to Esau’s bowl of stew and the help Jesus "
            "gives in the moment. The fourth is about winning and losing well. "
            "The fifth follows four men who followed Jesus: Andrew the bringer, "
            "Thomas who asked, John the Son of Thunder who learned to love, and "
            "Peter, who failed and was restored.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. Each week ends with a true story from "
            "our Brave for God books: George Müller, Adoniram Judson, Sundar "
            "Singh, David Livingstone and Hudson Taylor. The book encourages boys "
            "to find a trusted friend or mentor to help them stay accountable, "
            "and to tell a parent about anything online that troubles them.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 2 of Sons of the King about?",
                "answer": "Being faithful. Over thirty short daily devotions it looks at integrity, screens and gaming, temptation, winning and losing, and following Jesus like the disciples did.",
            },
            {
                "question": "Does it talk about video games and screens?",
                "answer": "Yes. Week 2 is about staying the boss of screens: setting limits, using time wisely, handling anger while gaming, staying away from harmful content, not disappearing from real life, and giving God the first part of the day.",
            },
            {
                "question": "How does it help with temptation?",
                "answer": "Week 3 shows how temptation works, starting in the garden of Eden, and teaches boys to watch and pray, run from wrong and chase what is good, get help from a trusted friend or mentor, and run straight to Jesus in the moment.",
            },
            {
                "question": "Who are the true stories at the end of each week?",
                "answer": "Five men from our Brave for God books: George Müller, Adoniram Judson, Sundar Singh, David Livingstone and Hudson Taylor. Each short story shows a real man who stayed faithful to God.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every Scripture is quoted from the Berean Standard Bible (BSB), a modern and readable translation that is in the public domain.",
            },
            {
                "question": "What comes after Book 2?",
                "answer": "Book 3 is about growing up: handling emotions, how God designed a boy’s body and the changes that come as he grows, responsibility, discovering his calling, and finding men who can help him grow.",
            },
        ],
    },
    3: {
        "sort_order": 86,
        "publication_year": 2026,
        "title": "Sons of the King – 30 Days with God for Guys – Book 3",
        "subtitle": "Growing Up: your feelings, your changing body, wise choices, and God’s calling",
        "cover_url": "/covers/sons-of-the-king-3.svg",
        "cover_color": covers.ink_safe("#7a4a2a"),  # a workshop oak brown
        "description": (
            "Thirty short daily devotions for boys aged 9 to 12 about growing up: "
            "handling anger, sadness, pressure and grief with God, understanding "
            "the changes of puberty as His good design, making wise choices about "
            "crushes, money, the crowd and danger, discovering his gifts and "
            "calling, and learning from Elijah and Elisha, Paul and Timothy, and "
            "Caleb. Each day has a Bible verse, a short teaching, a question, "
            "something to try and a prayer. The third and final book of Sons of "
            "the King."
        ),
        "about_html": (
            "<p>Sons of the King is an original Ochorus devotional series for boys "
            "aged 9 to 12. Book 1 taught a boy who he is, and Book 2 how to be "
            "faithful. Book 3 walks with him into growing up, and it opens with 1 "
            "John 2:14: “I have written to you, young men, because you are strong, "
            "and the word of God abides in you, and you have overcome the evil "
            "one.”</p>"
            "<p>The first week is about feelings, starting with the anger and "
            "sorrow Jesus Himself felt, then anger, feeling down, pressure, "
            "talking about what is inside, and grief. The second speaks openly and "
            "simply about puberty: growth spurts, the voice changing, body and "
            "facial hair, the private parts growing, erections and wet dreams, "
            "hygiene, and hormones and strength, all as part of God’s good design. "
            "It leaves questions about sex and reproduction to parents, and every "
            "day sends a boy back to his father or a man he trusts. The third week "
            "is about wise choices: crushes, money, the crowd, dares and danger, "
            "and a pure heart. The fourth is about calling, with Jeremiah, "
            "Bezalel the craftsman and Nehemiah the builder. The fifth is about "
            "mentors and finishing well, with Elijah and Elisha, Paul and Timothy, "
            "and Caleb at eighty-five.</p>"
            "<p>Every day follows the same short pattern: a Scripture from the "
            "Berean Standard Bible, a teaching, a question to think about, one "
            "thing to try, and a prayer. Each week ends with a true story from "
            "our Brave for God books: John Paton, Eric Liddell, Jim Elliot, "
            "George Liele and Simeon Nsibambi. A note for parents recommends "
            "reading the growing-up week together.</p>"
        ),
        "qa": [
            {
                "question": "What is Book 3 of Sons of the King about?",
                "answer": "Growing up. Over thirty short daily devotions it helps boys handle their feelings, understand how their bodies change, make wise choices, discover their gifts and calling, and learn from older men who walk with God.",
            },
            {
                "question": "Does it talk about puberty?",
                "answer": "Yes. Week 2 explains simply and accurately how a boy’s body changes: growth spurts, the voice deepening, body and facial hair, the private parts growing, erections and wet dreams, hygiene, and hormones. It presents all of it as God’s good design, nothing to be ashamed of, and encourages him to ask his father or a trusted man his questions. Sex and reproduction are left for parents to discuss.",
            },
            {
                "question": "Should parents read it with their son?",
                "answer": "We recommend it, especially for Week 2 and Day 10. A note for parents at the start explains exactly what that week covers, and each day of it ends by pointing a boy to his father or another man he trusts.",
            },
            {
                "question": "Does it say it’s okay for boys to have feelings?",
                "answer": "Yes. Week 1 begins with Jesus, who felt anger and sorrow, and teaches boys to name their feelings, cool down before acting in anger, rest and talk when they feel low, and grieve with hope. It encourages them to tell a parent or trusted adult if sadness lasts or grows big.",
            },
            {
                "question": "Which men does it include?",
                "answer": "From the Bible: Jesus, Elijah and Elisha, Zacchaeus, Jeremiah, Bezalel, Nehemiah, David, Paul and Timothy, and Caleb. From history, in the weekly true stories: John Paton, Eric Liddell, Jim Elliot, George Liele and Simeon Nsibambi.",
            },
            {
                "question": "Is this the last book in the series?",
                "answer": "Yes. Sons of the King has three books: Strong, Faithful and Growing Up. Its companion series for girls is Daughters of the King, and our Rooted series is for all young readers.",
            },
        ],
    },
}

# The title each series' covers set in place of the full one — the series
# numeral and the subtitle already carry "Book N" and the volume's theme, so the
# full "<Series> – 30 Days with God for … – Book N" only crowds the cover.
COVER_TITLE = {
    "rooted": "Rooted",
    "daughters-of-the-king": "Daughters of the King",
    "sons-of-the-king": "Sons of the King",
}

# The series a book can be built into, by `Series.slug`: each one's volumes are
# `<slug>-<n>`, read from `data/<slug>/<slug>-<n>.md`.
SERIES: dict[str, dict[int, dict[str, object]]] = {
    "rooted": ROOTED,
    "daughters-of-the-king": DAUGHTERS_OF_THE_KING,
    "sons-of-the-king": SONS_OF_THE_KING,
}

_INLINE = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"\*(.+?)\*"), r"<em>\1</em>"),
]
_LIST = re.compile(r"^(?:-|\d+\.) (.*)$")
# `quote_marks.convert` sets the double marks; single marks are ours to set. A
# mark after a space, a dash or an OPENING double mark opens a nested
# quotation; everything else is an apostrophe or a closing mark — including
# one after a closing double mark (`…of God."'"`).
_OPEN_SINGLE = re.compile(r"(^\"|(?<=\s)\"|^|[\s“(—])'")


def _single_marks(text: str) -> str:
    return _OPEN_SINGLE.sub(r"\1‘", text).replace("'", "’")


def _inline(text: str) -> str:
    out = html.escape(_single_marks(text), quote=False)
    for pattern, repl in _INLINE:
        out = pattern.sub(repl, out)
    return out


def _blocks(lines: list[str]) -> str:
    """One chapter's Markdown lines as HTML."""
    out: list[str] = []
    para: list[str] = []
    quote: list[str] = []
    items: list[str] = []
    list_tag = ""

    def flush():
        nonlocal list_tag
        if para:
            out.append("<p>" + "<br>".join(_inline(x) for x in para) + "</p>")
            para.clear()
        if quote:
            out.append(
                "<blockquote>"
                + "".join(f"<p>{_inline(x)}</p>" for x in quote if x)
                + "</blockquote>"
            )
            quote.clear()
        if items:
            out.append(
                f"<{list_tag}>" + "".join(f"<li>{_inline(x)}</li>" for x in items)
                + f"</{list_tag}>"
            )
            items.clear()
            list_tag = ""

    for line in lines:
        line = line.rstrip()
        if line.startswith(">"):
            if para or items:
                flush()
            quote.append(line[1:].strip())
            continue
        m = _LIST.match(line)
        if m:
            tag = "ul" if line.startswith("-") else "ol"
            if para or quote or (items and tag != list_tag):
                flush()
            list_tag = tag
            items.append(m.group(1))
            continue
        if not line.strip() or line.strip() == "---":
            flush()
            continue
        if line.startswith("### "):
            flush()
            out.append(f"<h2>{_inline(line[4:])}</h2>")
            continue
        if line.startswith("#"):
            raise CommandError(f"unexpected heading inside a chapter: {line!r}")
        if quote or items:
            flush()
        para.append(line.strip())
    flush()
    return "".join(out)


def parse(manuscript: str) -> list[tuple[str, str]]:
    """``(title, body_html)`` per chapter, in order."""
    chapters: list[tuple[str, list[str]]] = []
    for line in manuscript.splitlines():
        if line.startswith("## "):
            chapters.append((_single_marks(line[3:].strip()), []))
        elif line.startswith("# "):
            continue  # the book title and week dividers
        elif chapters:
            chapters[-1][1].append(line)
    return [(title, _blocks(lines)) for title, lines in chapters]


def check_shape(titles: list[str]) -> None:
    """Introduction, Day 1 … Day 30, Conclusion — the shape the plan relies on."""
    want = [f"Day {n} " for n in range(1, DAYS + 1)]
    days = titles[1:-1]
    if (
        len(titles) != DAYS + 2
        or not titles[0].startswith("Introduction")
        or not titles[-1].startswith("Conclusion")
        or any(not t.startswith(w) for t, w in zip(days, want, strict=True))
    ):
        raise CommandError(f"manuscript is not Introduction, Day 1–{DAYS}, Conclusion: {titles}")


class Command(BaseCommand):
    help = "Build a volume of a house 30-day devotional series (Rooted by default) from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int)
        parser.add_argument("--series", default="rooted", choices=sorted(SERIES))

    @transaction.atomic
    def handle(self, *args, **opts):
        series, volume = opts["series"], opts["volume"]
        if volume not in SERIES[series]:
            raise CommandError(f"{series} has no volume {volume}; known: {sorted(SERIES[series])}")
        meta = SERIES[series][volume]
        slug = f"{series}-{volume}"
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc

        try:
            series_row = Series.objects.get(slug=series)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {series!r} not found — load series.json first.") from exc

        chapters = parse((DATA_DIR / series / f"{slug}.md").read_text())
        check_shape([title for title, _ in chapters])

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series_row,
            "series_position": volume,
            "cover_title": COVER_TITLE[series],
            **meta,
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body, _ = convert(clean_fragment(body), outer_guillemets=False)
            body = settled_chapter_body(slug, order, body)
            title, _ = convert(title, outer_guillemets=False)
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
