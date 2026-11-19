"""Build a volume of *A Cloud of Praying Witnesses* from its manuscript.

A house series for adults on prayer through the whole story of the church, one
volume to an era; the plan of all eleven is
``data/a-cloud-of-praying-witnesses/SERIES-PLAN.md``. Every volume is an
Introduction, its chapters, a Conclusion and two appendices, and every chapter
ends with the same six sections (``REQUIRED``).

A volume is three files under ``data/a-cloud-of-praying-witnesses/``:

- ``volume-NN.md``, the manuscript (Ochorus's own writing, nothing fetched), in
  the closed Markdown subset of ``build_rooted.parse``;
- ``volume-NN.chapters.json``, one record per ``##`` section, in order: its
  title (checked against the manuscript, so a record cannot slip onto the wrong
  chapter), its key verse (which the chapter must cite) and the theme of each
  of its three key insights, from the series' ``THEMES``; the insights
  themselves are read from the chapter's own "Three key insights" list.
  ``person``, ``era``, ``region`` and ``read_more`` feed the last volume's
  timeline and reading list, which gather every volume's records;
- ``volume-NN.appendices.md``, GENERATED from the other two and never edited:
  Appendix 1 gathers the insights by theme; Appendix 2 indexes every Scripture
  the chapters cite, read from the prose with ``scripture.extract_citations``
  (the reader's own citation grammar), so a verse added to a chapter is
  indexed on the next build. Committed so it can be reviewed like the
  chapters; ``tests_praying_witnesses`` fails when it is stale.

The last volume (``FINAL_VOLUME``) carries the series appendices in place of its
own two: A and B merge every volume's insights and Scripture index, C is a
timeline of every chapter's ``person``/``era``/``region``, D is the hand-written
methods toolkit (``series-toolkit.md``), and E lists every chapter's
``read_more`` books. Because they read every volume, an edit to any volume makes
the last volume's appendices stale too, and the same test says so.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/<slug>.en.json``. Idempotent. The series row lives in
``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_praying_witnesses 2
"""

from __future__ import annotations

import html
import json
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit, scripture
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_faithful_with_little import ATTRIBUTION
from library.management.commands.build_rooted import AUTHOR_SLUG, DATA_DIR, parse
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES_SLUG = "a-cloud-of-praying-witnesses"
SERIES_DIR = DATA_DIR / SERIES_SLUG

# The sections every chapter ends with; a chapter missing one is a broken page.
REQUIRED = (
    "Three key insights",
    "For us today",
    "Try this",
    "A closing prayer",
    "Questions for reflection",
    "Read more on Ochorus",
)

# The series' closed theme list, in the order Appendix 1 prints them. Shared by
# every volume, so the last volume's master index can merge their appendices.
THEMES = (
    "The Father's Love",
    "Learning to Pray",
    "Making Room for Prayer",
    "Asking Boldly",
    "Persistence",
    "Faith",
    "Humility and Mercy",
    "Forgiveness",
    "Thanksgiving",
    "Guidance and Surrender",
    "Prayer in Suffering and Testing",
    "Praying Together",
    "Praying for Others",
    "Christ Who Prays for Us",
)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "slug": "the-prayers-jesus-learned",
        "book": {
            "publication_year": 2026,
            "title": "The Prayers Jesus Learned",
            "subtitle": "Prayer in the Old Testament",
            "cover_url": "/covers/art/the-prayers-jesus-learned.jpg",
            "cover_color": covers.ink_safe("#1c1f3d"),  # a starlit indigo
            "description": (
                "Seventeen short chapters on the great prayers of the Old Testament, the "
                "prayers Jesus grew up with: Abraham pleading for a city, Jacob wrestling "
                "through the night, Moses standing in the gap, Hannah pouring out her soul, "
                "David's psalms of longing and repentance, Elijah on Mount Carmel, Jonah in "
                "the deep, Daniel at his open window, Nehemiah before the king, and Habakkuk "
                "rejoicing when the fields are bare."
            ),
            "about_html": (
                "<p>When Jesus prayed on the cross, the words that came to His lips were the "
                "words of the Psalms. He had grown up with them: sung on the road to "
                "Jerusalem at the great feasts, heard every Sabbath in the synagogue at "
                "Nazareth, said morning and evening at home. This book listens to those "
                "prayers. It is Volume 1 of A Cloud of Praying Witnesses, an Ochorus series "
                "that follows the people of God at prayer from the first pages of the Bible "
                "to the church around the world today.</p>"
                "<p>Its seventeen chapters move through four parts of the story: the fathers "
                "of faith, Abraham and Jacob; Moses, who stood in the gap for his people and "
                "asked to see God's glory; the judges and kings, from Hannah and Samuel to "
                "David and Solomon; and the prophets, the exile and the return, from Elijah "
                "and Hezekiah to Daniel, Nehemiah, the psalms of lament and Habakkuk. These "
                "were not perfect people, and their prayers are not the prayers of the "
                "strong, but of the weak who learned that God hears.</p>"
                "<p>Every chapter opens with a key verse and a story, quotes voices from the "
                "past such as E. M. Bounds, Andrew Murray and Charles Spurgeon word for word "
                "from their books in the library, and ends with three key insights, a word "
                "for today, a practice to try, a closing prayer and questions for "
                "reflection. Two appendices gather every insight by theme and every "
                "Scripture in Bible order. Scripture is quoted from the Open Word Bible "
                "(OWB), Balanced edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is The Prayers Jesus Learned about?",
                    "answer": "The great prayers of the Old Testament, in seventeen short chapters: Abraham, Jacob, Moses, Hannah, Samuel, David, Solomon, Elijah, Jehoshaphat, Hezekiah, Jonah, Daniel, Nehemiah, the psalms of lament and Habakkuk. These are the prayers Jesus grew up with, and the book shows how He carried them into His own praying.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. This prelude listens to the Old Testament; Volume 2 sits with Jesus, the Teacher of Prayer; later volumes follow the apostles and then the praying men and women of every century and every part of the world, down to the global church today.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "How is each chapter laid out?",
                    "answer": "Each chapter opens with a key verse and a story, looks at what the passage shows about prayer, quotes a voice from the past, and ends with three key insights, a section called For us today, one practice to try that week, a closing prayer and questions for reflection.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes seventeen days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    2: {
        "slug": "jesus-teacher-of-prayer",
        "book": {
            "publication_year": 2026,
            "title": "Jesus, Teacher of Prayer",
            "subtitle": "Lord, teach us to pray",
            "cover_color": covers.ink_safe("#2b3a67"),  # a deep before-dawn blue
            "description": (
                "Twenty short chapters on how Jesus prayed and what He taught about "
                "prayer: rising before dawn, praying all night before great "
                "decisions, the Lord's Prayer, the secret room, asking, seeking and "
                "knocking, persistence, humility, faith, praying together, giving "
                "thanks, and His last prayers in the Upper Room, in Gethsemane and on "
                "the cross. Each chapter has a key verse, voices from Andrew Murray, "
                "E. M. Bounds, Thomas Watson, R. A. Torrey and others, three key "
                "insights, and a practice for the week."
            ),
            "about_html": (
                "<p>The disciples had watched Jesus heal the sick and calm the storm, "
                "but the one thing they asked Him to teach them was how to pray. This "
                "book sits beside them in that school. It is Volume 2 of A Cloud of "
                "Praying Witnesses, an Ochorus series that follows the people of "
                "God at prayer from the Old Testament to the church around the world "
                "today, and it begins where every praying Christian has learned: with "
                "Jesus Himself.</p>"
                "<p>Its twenty chapters follow four movements. We watch Jesus at "
                "prayer, before dawn and all night on a mountain. We walk slowly "
                "through the prayer He taught, and into the secret room. We listen to "
                "His teaching: ask, seek and knock; never give up; humble yourself; "
                "believe; pray together; pray for the harvest; give thanks; ask in His "
                "name. And we stand near Him at His last prayers, for Peter, for the "
                "unity of His people, in Gethsemane and on the cross, and end where He "
                "is now, at the right hand of the Father, always living to pray for "
                "us.</p>"
                "<p>Every chapter opens with a key verse and a story, quotes voices "
                "from the past such as Andrew Murray, E. M. Bounds, Thomas Watson, R. A. "
                "Torrey and George Müller word for word from their books in the "
                "library, and ends with three key insights, a word for today, a "
                "practice to try, a closing prayer and questions for reflection. Two "
                "appendices gather every insight by theme and every Scripture in Bible "
                "order. Scripture is quoted from the Open Word Bible (OWB), Balanced "
                "edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Jesus, Teacher of Prayer about?",
                    "answer": "How Jesus prayed and what He taught about prayer, in twenty short chapters: His early mornings and nights of prayer, the Lord's Prayer, the secret room, His teaching on asking, persistence, humility, faith and praying together, and His last prayers for Peter, for His people, in Gethsemane and on the cross, ending with His prayer for us now in heaven.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. After a prelude on the prayers of the Old Testament, it follows Jesus, the apostles, and then the praying men and women of every century and every part of the world, from the martyrs and the desert fathers to the global church today. This book is Volume 2.",
                },
                {
                    "question": "How is each chapter laid out?",
                    "answer": "Each chapter opens with a key verse and a story, looks at what the passage shows about prayer, quotes a voice from the past, and ends with three key insights, a section called For us today, one practice to try that week, a closing prayer and questions for reflection.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes twenty days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which classic writers does it quote?",
                    "answer": "Andrew Murray and E. M. Bounds most often, then Thomas Watson and R. A. Torrey, with George Müller, Dwight L. Moody and Charles Spurgeon, each quoted exactly from a book you can read in full in the library.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    3: {
        "slug": "devoted-to-prayer",
        "book": {
            "publication_year": 2026,
            "title": "Devoted to Prayer",
            "subtitle": "The Apostles and the First Church",
            "cover_url": "/covers/art/devoted-to-prayer.jpg",
            "cover_color": covers.ink_safe("#24305e"),  # a dawn-blue
            "description": (
                "Twenty short chapters on how the first Christians prayed: waiting in the "
                "upper room, devoted to the prayers, praying under threat, Stephen praying "
                "for his killers, the church praying all night for Peter, Paul and Silas "
                "singing at midnight, the prayers of Paul's letters, the Spirit's help when "
                "we do not know what to pray, never stop praying, prayer for rulers and for "
                "the sick, and the golden bowls of Revelation."
            ),
            "about_html": (
                "<p>When Jesus was taken up into heaven, His followers had no leader they "
                "could see, no buildings, no money and no plan anyone else would take "
                "seriously. They went back into Jerusalem, climbed the stairs to an upper "
                "room, and prayed. This book follows what happened next. It is Volume 3 of "
                "A Cloud of Praying Witnesses, an Ochorus series that follows the people of "
                "God at prayer from the Old Testament to the church around the world "
                "today.</p>"
                "<p>Its twenty chapters move in three parts. In Jerusalem we wait with the "
                "hundred and twenty, join the first believers devoted to the prayers, pray "
                "with the church under threat, kneel with Stephen and pray through the night "
                "for Peter in prison. On the move we watch the church at Antioch fast and "
                "send out its first missionaries, find women praying by a river in Philippi, "
                "and hear Paul and Silas singing at midnight. In the letters we read the "
                "prayers Paul wrote for the churches he loved, learn how the Spirit helps "
                "our weakness, pray for rulers and for the sick, and end with John on "
                "Patmos, watching the prayers of God's people rise before the throne.</p>"
                "<p>Every chapter opens with a key verse and a story, quotes voices from the "
                "past such as E. M. Bounds, Andrew Murray, Charles Spurgeon and R. A. Torrey "
                "word for word from their books in the library, and ends with three key "
                "insights, a word for today, a practice to try, a closing prayer and "
                "questions for reflection. Two appendices gather every insight by theme and "
                "every Scripture in Bible order. Scripture is quoted from the Open Word "
                "Bible (OWB), Balanced edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Devoted to Prayer about?",
                    "answer": "How the first Christians prayed, from the upper room in Jerusalem to the letters of Paul, James and John: twenty short chapters on waiting for the Spirit, praying together, praying under threat, praying for enemies, rulers and the sick, praying without stopping, and the prayers of God's people rising before the throne in Revelation.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. Volume 1 listens to the prayers of the Old Testament, Volume 2 sits with Jesus, the Teacher of Prayer, and this third volume follows the apostles and the first church. Later volumes follow the praying men and women of every century and every part of the world.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "How is each chapter laid out?",
                    "answer": "Each chapter opens with a key verse and a story, looks at what the passage shows about prayer, quotes a voice from the past, and ends with three key insights, a section called For us today, one practice to try that week, a closing prayer and questions for reflection.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes twenty days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    4: {
        "slug": "faithful-unto-death",
        "book": {
            "publication_year": 2026,
            "title": "Faithful unto Death",
            "subtitle": "Martyrs and Desert Fathers",
            "cover_url": "/covers/art/faithful-unto-death.jpg",
            "cover_color": covers.ink_safe("#3a2a2e"),  # a desert dusk
            "description": (
                "Eighteen short chapters on how the church prayed from about AD 100 to 500: "
                "the Didache's three times a day, Clement praying for rulers who persecute, "
                "Ignatius and Polycarp facing death, Perpetua in prison, Cyprian on the Lord's "
                "Prayer, Antony and the desert mothers and fathers, Cassian's one-verse prayer, "
                "Ephrem's hymns, Monica's tears, Augustine's restless heart, Patrick in Ireland "
                "and the Jesus Prayer."
            ),
            "about_html": (
                "<p>When the last of the apostles died, the church had to go on praying "
                "without anyone who had seen the Lord with their own eyes. For much of the "
                "next two hundred years, being a Christian was against the law. This book "
                "follows the believers who prayed through those years and the centuries "
                "after them, up to about the year 500. It is Volume 4 of A Cloud of Praying "
                "Witnesses, an Ochorus series that follows the people of God at prayer from "
                "the Old Testament to the church around the world today.</p>"
                "<p>Its eighteen chapters move in three parts. In the age of the martyrs we "
                "learn to pray three times a day from the Didache, hear Clement pray for "
                "rulers who persecute, walk with Ignatius on the road to the lions, stand "
                "with Polycarp at the stake and sit with Perpetua and Felicity in prison. In "
                "the desert we follow Antony and the mothers and fathers who came after him, "
                "learn John Cassian's one short verse for the whole day, and hear Macrina and "
                "Ephrem turn a home and a city to prayer and song. Last come teachers, "
                "mothers and missionaries: John Chrysostom, Monica, Augustine, Patrick, and "
                "the Jesus Prayer.</p>"
                "<p>Every chapter tells its story from the earliest sources and says plainly "
                "where tradition takes over. It quotes the witnesses themselves word for word "
                "from their books in the library, and ends with three key insights, a word "
                "for today, a practice to try, a closing prayer and questions for reflection. "
                "Two appendices gather every insight by theme and every Scripture in Bible "
                "order. Scripture is quoted from the Open Word Bible (OWB), Balanced edition, "
                "which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Faithful unto Death about?",
                    "answer": "How Christians prayed in the four centuries after the apostles, from about AD 100 to 500: eighteen short chapters on the martyrs who prayed in prison and at the stake, the mothers and fathers of the desert, and the teachers, mothers and missionaries who taught the church to pray, from the Didache to Augustine, Patrick and the Jesus Prayer.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. Volume 1 listens to the prayers of the Old Testament, Volume 2 sits with Jesus, the Teacher of Prayer, Volume 3 follows the apostles and the first church, and this fourth volume follows the martyrs and desert fathers. Later volumes follow the praying men and women of every century and every part of the world.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Are the stories in this book historical?",
                    "answer": "They come from the oldest sources we have: letters, prison diaries, sermons and lives written by people who knew these believers. Where a detail is only a later tradition, or where scholars are unsure, the chapter says so.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes eighteen days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    5: {
        "slug": "seven-times-a-day",
        "book": {
            "publication_year": 2026,
            "title": "Seven Times a Day",
            "subtitle": "Monks, Mystics and Missionaries",
            "cover_url": "/covers/art/seven-times-a-day.jpg",
            "cover_color": covers.ink_safe("#2a3150"),  # a morning slate
            "description": (
                "Seventeen short chapters on how the church prayed from about AD 500 to "
                "1500: Benedict's hours of prayer, the praying church of Ethiopia, the "
                "Church of the East in China, Columba's Iona, Gregory of Narek, Anselm, "
                "Bernard, Francis and Clare of Assisi, Thomas Aquinas, The Cloud of "
                "Unknowing, the monks of Mount Athos, Julian of Norwich, Catherine of Siena, "
                "Wycliffe, Hus and Thomas à Kempis."
            ),
            "about_html": (
                "<p>This book covers a thousand years, from the fall of the old Roman world "
                "in the West to the eve of the Reformation. People sometimes picture those "
                "centuries as a dark and empty time, but for the life of prayer they were "
                "anything but empty. In monasteries and villages, on islands and mountains, "
                "in great cities and along the trade roads of Asia, believers kept praying "
                "and taught the next generation to pray. It is Volume 5 of A Cloud of "
                "Praying Witnesses, an Ochorus series that follows the people of God at "
                "prayer from the Old Testament to the church around the world today.</p>"
                "<p>Its seventeen chapters move in four parts. With the monks and "
                "missionaries we keep Benedict's seven hours of prayer, find the ancient "
                "church of Ethiopia, follow the Church of the East to China and land on "
                "Iona with Columba. Then we seek God's face with Gregory of Narek, Anselm, "
                "Bernard, Francis and Clare; learn from teachers and mystics such as Thomas "
                "Aquinas, the monks of Mount Athos, Julian of Norwich and Catherine of "
                "Siena; and come back to the Word with Wycliffe, Hus and Thomas à "
                "Kempis.</p>"
                "<p>Every chapter tells its story from the oldest sources, says plainly "
                "where legend takes over and when a famous prayer is not really by the "
                "person whose name it carries. It quotes the witnesses word for word from "
                "their books in the library where it can, and ends with three key insights, "
                "a word for today, a practice to try, a closing prayer and questions for "
                "reflection. Two appendices gather every insight by theme and every "
                "Scripture in Bible order. Scripture is quoted from the Open Word Bible "
                "(OWB), Balanced edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Seven Times a Day about?",
                    "answer": "How Christians prayed through the thousand years from about AD 500 to 1500: seventeen short chapters on monks and missionaries, seekers of God's face, teachers and mystics, and the first reformers, from Benedict and the church of Ethiopia to Julian of Norwich, Jan Hus and Thomas à Kempis.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first four volumes follow prayer in the Old Testament, the teaching of Jesus, the first church, and the martyrs and desert fathers. This fifth volume follows the monks, mystics and missionaries of the next thousand years, and later volumes follow the praying men and women of every century and every part of the world.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Why is it called Seven Times a Day?",
                    "answer": "The title comes from Psalm 119:164, \"I praise you seven times every day\", the verse Benedict used in his Rule for the hours of prayer that monks kept through the day. The book asks what that rhythm can teach ordinary believers today.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes seventeen days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    6: {
        "slug": "a-mighty-fortress",
        "book": {
            "publication_year": 2026,
            "title": "A Mighty Fortress",
            "subtitle": "Prayer and the Reformation",
            "cover_url": "/covers/art/a-mighty-fortress.jpg",
            "cover_color": covers.ink_safe("#22355a"),  # a morning blue
            "description": (
                "Seventeen short chapters on how believers prayed in the age of the "
                "Reformation, from about 1500 to 1650: Luther and his simple way to pray, "
                "Calvin, Cranmer's common prayer, Knox, Teresa of Ávila, John of the Cross, "
                "Ignatius and the examen, Francis de Sales, the hidden Christians of Japan, "
                "Lancelot Andrewes, George Herbert, Richard Sibbes, Richard Baxter, John "
                "Bunyan, Brother Lawrence and the Anabaptist martyrs."
            ),
            "about_html": (
                "<p>In the 1500s the church in the West was torn apart and renewed at the "
                "same time. Reformers called believers back to the Bible and to faith in "
                "Christ alone; within the Catholic church, too, men and women sought a "
                "deeper life of prayer. Christians of that age sometimes persecuted one "
                "another, and many died for their faith. Yet on every side there were people "
                "who prayed, and who taught others to pray. It is Volume 6 of A Cloud of "
                "Praying Witnesses, an Ochorus series that follows the people of God at "
                "prayer from the Old Testament to the church around the world today.</p>"
                "<p>Its seventeen chapters follow Martin Luther, who wrote his barber a "
                "simple way to pray, John Calvin, Thomas Cranmer and the first prayer book "
                "in English, and John Knox; Teresa of Ávila, John of the Cross, Ignatius of "
                "Loyola and Francis de Sales; the hidden Christians of Japan, who kept "
                "praying for two hundred and fifty years, most of them without a priest; Lancelot "
                "Andrewes, George Herbert, Richard Sibbes, Richard Baxter and John Bunyan; "
                "Brother Lawrence among the pots and pans; and the Anabaptist martyrs.</p>"
                "<p>Every chapter tells its story from the oldest sources, says plainly "
                "where legend takes over, and is fair to every church. It quotes the "
                "witnesses word for word from their books in the library where it can, and "
                "ends with three key insights, a word for today, a practice to try, a "
                "closing prayer and questions for reflection. Two appendices gather every "
                "insight by theme and every Scripture in Bible order. Scripture is quoted "
                "from the Open Word Bible (OWB), Balanced edition, which is dedicated to the "
                "public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is A Mighty Fortress about?",
                    "answer": "How believers prayed in the age of the Reformation, from about 1500 to 1650: seventeen short chapters on Protestant reformers, Catholic renewal, Anglican and Puritan pastors, the hidden Christians of Japan and the Anabaptist martyrs, from Martin Luther and Teresa of Ávila to John Bunyan and Brother Lawrence.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first five volumes follow prayer in the Old Testament, the teaching of Jesus, the first church, the martyrs and desert fathers, and the monks, mystics and missionaries of the Middle Ages. This sixth volume follows the age of the Reformation, and later volumes follow the praying men and women of every century and every part of the world.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Does the book take sides between Protestants and Catholics?",
                    "answer": "It tells the history honestly, including the harm Christians did to one another in that age, and listens to praying believers on every side. Where churches still differ, it describes their practice simply and keeps its focus on what every believer can learn about prayer.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes seventeen days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    7: {
        "slug": "the-fire-on-the-altar",
        "book": {
            "publication_year": 2026,
            "title": "The Fire on the Altar",
            "subtitle": "Pietists, Moravians and the Great Awakenings",
            "cover_url": "/covers/art/the-fire-on-the-altar.jpg",
            "cover_color": covers.ink_safe("#25416c"),  # a bright morning blue
            "description": (
                "Seventeen short chapters on prayer in the age of revival, from about 1650 "
                "to 1800: Jeanne Guyon, the Pietists' small groups, Francke's orphanage, "
                "the Moravian prayer watch and missions, Susanna and John Wesley, "
                "Whitefield, Jonathan Edwards's concert of prayer, David Brainerd, "
                "Cambuslang, Marie Durand, John Newton, Richard Allen and Absalom Jones, "
                "Samson Occom, the Prayer Call of 1784 and William Carey."
            ),
            "about_html": (
                "<p>After a century of religious wars, many churches in Europe had settled "
                "into right belief and good order, and it was easy to belong to a church "
                "without knowing Christ. Then, in small prayer groups, in a refugee village "
                "and in fields where thousands gathered to hear the gospel, a fire was lit. "
                "This book follows the praying people of the Pietist, Moravian and "
                "evangelical awakenings, from about 1650 to 1800. It is Volume 7 of A Cloud "
                "of Praying Witnesses, an Ochorus series that follows the people of God at "
                "prayer from the Old Testament to the church around the world today.</p>"
                "<p>Its seventeen chapters follow Jeanne Guyon, Philipp Spener's little "
                "churches within the church and August Hermann Francke's orphanage; the "
                "Moravians at Herrnhut, whose prayer watch ran night and day, and their "
                "missionaries; Susanna and John Wesley, George Whitefield and Jonathan "
                "Edwards; David Brainerd praying in the snow, the Cambuslang revival and "
                "Marie Durand in her prison tower; John Newton and the Olney prayer "
                "meeting; Richard Allen and Absalom Jones, Samson Occom, and the prayer "
                "meetings that sent William Carey to India.</p>"
                "<p>Every chapter tells its story from the oldest sources, says plainly "
                "where legend takes over, and is honest about the shadows of the age as well "
                "as its fire. It quotes the witnesses word for word from their books in the "
                "library where it can, and ends with three key insights, a word for today, a "
                "practice to try, a closing prayer and questions for reflection. Two "
                "appendices gather every insight by theme and every Scripture in Bible "
                "order. Scripture is quoted from the Open Word Bible (OWB), Balanced "
                "edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is The Fire on the Altar about?",
                    "answer": "How believers prayed in the age of the Pietist, Moravian and evangelical awakenings, from about 1650 to 1800: seventeen short chapters from Jeanne Guyon and the Moravian prayer watch to John Wesley, Jonathan Edwards, David Brainerd, Richard Allen and William Carey.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first six volumes follow prayer from the Old Testament to the Reformation. This seventh volume follows the age of revival, and later volumes follow the praying men and women of every century and every part of the world.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Why is it called The Fire on the Altar?",
                    "answer": "The title comes from Leviticus 6:13, where God commands that the fire on the altar must be kept burning and never go out. The Moravians at Herrnhut are remembered for taking that verse as a picture of the prayer watch they kept night and day, and it fits the whole age of revival this book describes.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes seventeen days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    8: {
        "slug": "open-your-mouth-wide",
        "book": {
            "publication_year": 2026,
            "title": "Open Your Mouth Wide",
            "subtitle": "The Great Century of Prayer",
            "cover_url": "/covers/art/open-your-mouth-wide.jpg",
            "cover_color": covers.ink_safe("#2a4c7e"),  # a late-morning blue
            "description": (
                "Twenty short chapters on prayer in the great century of missions, from "
                "about 1800 to 1900: the Haystack meeting, Finney and Father Nash, "
                "Christmas Evans, M'Cheyne, George Müller, the Russian pilgrim, Seraphim of "
                "Sarov, the Fulton Street noon prayer meeting, the Ulster revival, "
                "Spurgeon, Hudson Taylor, Pastor Hsi, Moody, the Booths, Amanda Berry Smith, "
                "Samuel Ajayi Crowther, Andrew Murray, Mary Slessor, Thérèse of Lisieux and "
                "E. M. Bounds."
            ),
            "about_html": (
                "<p>In the 1800s the church prayed and the gospel went out as never before. "
                "Students prayed under a haystack and the first American missionaries "
                "sailed; a few young men prayed in a village schoolhouse and a revival swept "
                "a province; a man in Bristol fed thousands of orphans by asking no one but "
                "God. Believers in Africa and Asia rose up as preachers, bishops and "
                "evangelists in their own right. This book follows the praying people of "
                "that great century. It is Volume 8 of A Cloud of Praying Witnesses, an "
                "Ochorus series that follows the people of God at prayer from the Old "
                "Testament to the church around the world today.</p>"
                "<p>Its twenty chapters follow the Haystack prayer meeting, Daniel Nash and "
                "Charles Finney, Christmas Evans, Robert Murray M'Cheyne and George Müller; "
                "the Russian pilgrim learning to pray without ceasing and Seraphim of Sarov; "
                "the noon prayer meeting of 1857 and the Ulster revival of 1859; Charles "
                "Spurgeon, Hudson Taylor and Pastor Hsi of China; D. L. Moody, William and "
                "Catherine Booth, Amanda Berry Smith and Samuel Ajayi Crowther; and Andrew "
                "Murray, Mary Slessor, Thérèse of Lisieux and E. M. Bounds.</p>"
                "<p>Every chapter tells its story from the oldest sources and says plainly "
                "where legend takes over. It quotes the witnesses word for word from their "
                "books in the library where it can, and ends with three key insights, a "
                "word for today, a practice to try, a closing prayer and questions for "
                "reflection. Two appendices gather every insight by theme and every "
                "Scripture in Bible order. Scripture is quoted from the Open Word Bible "
                "(OWB), Balanced edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Open Your Mouth Wide about?",
                    "answer": "How believers prayed in the great century of missions, from about 1800 to 1900: twenty short chapters from the Haystack prayer meeting and George Müller to Hudson Taylor, Pastor Hsi, Amanda Berry Smith, Samuel Ajayi Crowther, Mary Slessor and E. M. Bounds.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first seven volumes follow prayer from the Old Testament to the age of revival. This eighth volume follows the nineteenth century, and later volumes follow the praying men and women of the twentieth century and the church around the world today.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Why is it called Open Your Mouth Wide?",
                    "answer": "The title comes from Psalm 81:10, where God promises to fill the mouth of anyone who opens it wide. George Müller took that verse as God's invitation to ask for great things when he began his orphan houses, and it fits a century when the church asked God for the nations.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes twenty days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    9: {
        "slug": "revival-fires",
        "book": {
            "publication_year": 2026,
            "title": "Revival Fires",
            "subtitle": "Prayer and Awakening",
            "cover_url": "/covers/art/revival-fires.jpg",
            "cover_color": covers.ink_safe("#2e5a8f"),  # a midday blue
            "description": (
                "Twenty short chapters on prayer and revival from about 1900 to 1950: "
                "Evan Roberts and Wales, Pandita Ramabai, Azusa Street, Pyongyang and "
                "Korean dawn prayer, Praying Hyde, Sadhu Sundar Singh, Amy Carmichael, "
                "Smith Wigglesworth, Rees Howells, Dora Yu, John Sung, Watchman Nee, "
                "Dietrich Bonhoeffer, Corrie ten Boom, Gladys Aylward, the East African "
                "revival, the Hebrides, Billy Graham and A. W. Tozer."
            ),
            "about_html": (
                "<p>The twentieth century began with revival. In a Welsh chapel, an Indian "
                "women's home, a run-down building in Los Angeles and a church in "
                "Pyongyang, ordinary believers prayed, confessed their sins and saw God "
                "move. Then came two world wars, revolution and the end of empires, and the "
                "church learned to pray in prison camps, in hiding and on the road. This "
                "book follows the praying people of those fifty years. It is Volume 9 of A "
                "Cloud of Praying Witnesses, an Ochorus series that follows the people of "
                "God at prayer from the Old Testament to the church around the world "
                "today.</p>"
                "<p>Its twenty chapters follow Evan Roberts and the Welsh revival, Pandita "
                "Ramabai and the women of Mukti, William Seymour on Azusa Street, the "
                "praying churches of Korea, Praying Hyde, Sadhu Sundar Singh and Amy "
                "Carmichael; Smith Wigglesworth, Rees Howells, Dora Yu, John Sung and "
                "Watchman Nee; Dietrich Bonhoeffer, Corrie ten Boom and Gladys Aylward; and "
                "the East African revival, the two sisters who prayed for the Isle of "
                "Lewis, the men who prayed for Charlotte, Billy Graham and A. W. "
                "Tozer.</p>"
                "<p>Every chapter tells its story from the best sources it can, says "
                "plainly where a story has grown in the telling, and is fair to readers who "
                "differ. It quotes the witnesses word for word where their words are free "
                "to share, and ends with three key insights, a word for today, a practice "
                "to try, a closing prayer and questions for reflection. Two appendices "
                "gather every insight by theme and every Scripture in Bible order. "
                "Scripture is quoted from the Open Word Bible (OWB), Balanced edition, "
                "which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Revival Fires about?",
                    "answer": "How believers prayed in the revivals and the wars of the first half of the twentieth century, from about 1900 to 1950: twenty short chapters from Evan Roberts and Pandita Ramabai to Korea's dawn prayer, Corrie ten Boom, the East African revival and A. W. Tozer.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first eight volumes follow prayer from the Old Testament to the great missionary century. This ninth volume follows the first half of the twentieth century, and the last volumes follow the church around the world to today.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Does the book take sides on revivals and spiritual gifts?",
                    "answer": "It tells what happened from the best sources and describes the revivals warmly and fairly, including the ones that began new movements such as Pentecostalism. Where churches still differ, it keeps its focus on what every believer can learn about prayer.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes twenty days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    10: {
        "slug": "every-tribe-and-tongue",
        "book": {
            "publication_year": 2026,
            "title": "Every Tribe and Tongue",
            "subtitle": "The Global Praying Church",
            "cover_url": "/covers/art/every-tribe-and-tongue.jpg",
            "cover_color": covers.ink_safe("#325f95"),  # an afternoon blue
            "description": (
                "Twenty short chapters on the praying church around the world from 1950 to "
                "today: Jim and Elisabeth Elliot, Helen Roseveare, Brother Andrew, Taizé, "
                "Mother Teresa, Korea's prayer mountains, Festo Kivengere and Janani Luwum, "
                "Evelyn Christenson, China's house churches, prayer and fasting, YWAM, the "
                "Brooklyn Tabernacle, the 10/40 Window, Argentina, 24-7 Prayer, the Global "
                "Day of Prayer, Africa's all-night vigils, Helen Berhane, Iran's house "
                "churches and Tim Keller."
            ),
            "about_html": (
                "<p>Since 1950 the church has become, for the first time, truly a church of "
                "every tribe and tongue. Most Christians now live in Africa, Asia and Latin "
                "America, and some of the most faithful praying in the world happens in "
                "places where believers are watched, arrested or killed for their faith. "
                "This book follows the praying people of these decades, many of them still "
                "living. It is Volume 10 of A Cloud of Praying Witnesses, an Ochorus series "
                "that follows the people of God at prayer from the Old Testament to the "
                "church around the world today.</p>"
                "<p>Its twenty chapters follow missionaries who gave their lives and those "
                "who stayed, from the Elliots and Helen Roseveare to Brother Andrew; "
                "communities of prayer such as Taizé, Mother Teresa's sisters and Korea's "
                "prayer mountains; African bishops who blessed their persecutors; women who "
                "learned to pray together; the house churches of China and Iran; prayer and "
                "fasting, listening prayer and a Brooklyn prayer meeting; movements that "
                "prayed for the nations and for whole cities; a prayer room that never "
                "closed; Africa's all-night vigils; a singer who prayed in a shipping "
                "container; and a pastor who wrote of awe and intimacy with God.</p>"
                "<p>Every chapter tells its story from public sources, says plainly where "
                "accounts differ, and takes care to protect believers who are still at risk. "
                "Because these stories are recent, they are told in the book's own words, "
                "with voices from the classics quoted word for word from the library. Each "
                "chapter ends with three key insights, a word for today, a practice to try, "
                "a closing prayer and questions for reflection. Two appendices gather every "
                "insight by theme and every Scripture in Bible order. Scripture is quoted "
                "from the Open Word Bible (OWB), Balanced edition, which is dedicated to the "
                "public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Every Tribe and Tongue about?",
                    "answer": "How the worldwide church has prayed from 1950 to today: twenty short chapters from Jim and Elisabeth Elliot and Helen Roseveare to Korea's prayer mountains, the house churches of China and Iran, Africa's all-night vigils and 24-7 Prayer.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first nine volumes follow prayer from the Old Testament to the revivals of the early twentieth century. This tenth volume follows the global church from 1950 to today, and the final volume gathers what the whole cloud of witnesses teaches.",
                },
                {
                    "question": "Do I need to read the volumes in order?",
                    "answer": "No. Each volume stands on its own. Reading them in order follows the story from Abraham to today, but you can begin with any volume.",
                },
                {
                    "question": "Does the book name believers in countries where they are persecuted?",
                    "answer": "Only people who have already told their own stories in public, or whose cases have been widely reported. It describes house churches and prayer movements in persecuted countries in general terms, so that no one is put at risk.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a day takes twenty days on your own, and with a group one or two chapters a week works well. The questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
    11: {
        "slug": "golden-bowls",
        "book": {
            "publication_year": 2026,
            "title": "Golden Bowls",
            "subtitle": "Your Place in the Prayer Meeting",
            "cover_url": "/covers/art/golden-bowls.jpg",
            "cover_color": covers.ink_safe("#232a56"),  # an evening indigo
            "description": (
                "The last volume of A Cloud of Praying Witnesses: twelve short chapters that "
                "gather what the praying church has learned from Abraham to today, on praying "
                "the Scriptures, fasting, praying alone and together, waiting, unanswered "
                "prayer, the nations, revival, prayer at home and a rhythm of prayer for your "
                "own life."
            ),
            "about_html": (
                "<p>In the throne room of heaven, John saw golden bowls full of incense, "
                "\"the prayers of God's holy people\" (Revelation 5:8). This book asks what "
                "the whole cloud of witnesses, from Abraham to the praying church of our own "
                "day, teaches about prayer, and how you can take your own place among them. "
                "It is Volume 11, the last, of A Cloud of Praying Witnesses, an Ochorus series "
                "that follows the people of God at prayer from the Old Testament to the "
                "church around the world today.</p>"
                "<p>Its twelve chapters each take one theme: the prayer meeting that has "
                "lasted for thousands of years, what the witnesses agree on, praying the "
                "Scriptures, fasting, praying alone and with others, waiting on the Lord, "
                "unanswered prayer, intercession for the nations, prayer for revival, prayer "
                "in the home, building your own rhythm of prayer, and the church's last "
                "prayer, \"Come, Lord Jesus.\" Each opens with a scene from a witness met "
                "earlier in the series and follows the thread through the centuries.</p>"
                "<p>Every chapter ends with three key insights, a word for today, a simple "
                "practice that can be done anywhere, a closing prayer and questions for "
                "reflection. Five appendices gather the whole series: every key insight by "
                "theme, a Scripture index from Genesis to Revelation, a timeline of every "
                "witness, a toolkit of ways to pray, and the books on Ochorus where you can "
                "keep reading. Scripture is quoted from the Open Word Bible (OWB), Balanced "
                "edition, which is dedicated to the public domain.</p>"
            ),
            "qa": [
                {
                    "question": "What is Golden Bowls about?",
                    "answer": "What the whole history of the praying church teaches about your own life of prayer: twelve themed chapters on praying the Scriptures, fasting, praying alone and together, waiting, unanswered prayer, the nations, revival, prayer at home and a daily rhythm of prayer.",
                },
                {
                    "question": "What is A Cloud of Praying Witnesses?",
                    "answer": "A series of books on prayer through the whole story of the church, named for Hebrews 12:1. The first ten volumes follow prayer from the Old Testament to the global church of today. This eleventh and last volume gathers what the whole cloud of witnesses teaches.",
                },
                {
                    "question": "Do I need to read the earlier volumes first?",
                    "answer": "No. Each chapter tells you enough of every story to stand on its own, and points to the volume where the full story is told if you want to read more.",
                },
                {
                    "question": "What are the appendices at the end of the book?",
                    "answer": "Five appendices for the whole series: every key insight from all eleven volumes by theme, a Scripture index from Genesis to Revelation, a timeline of every person and movement, a toolkit of simple ways to pray, and the books on Ochorus where you can keep reading.",
                },
                {
                    "question": "Can I read it with a small group?",
                    "answer": "Yes. One chapter a week gives time to practise each chapter's suggestion before the next meeting, and the questions at the end of every chapter are written to start a conversation.",
                },
                {
                    "question": "Which Bible translation does it use?",
                    "answer": "Every Scripture is quoted from the Open Word Bible (OWB), Balanced edition, a new translation from the Hebrew and Greek that is dedicated to the public domain.",
                },
            ],
        },
    },
}


# ── The generated appendices ────────────────────────────────────────────────


def _label(index: int, last: int, title: str) -> str:
    """How the section at ``index`` (of ``0..last``) is named in an index line."""
    if index == 0:
        return "Introduction"
    if index == last:
        return "Conclusion"
    return f"Chapter {index}, *{title}*"


# A chapter's "Three key insights" list: each item opens on its insight in bold.
_INSIGHTS = re.compile(r"<h2>Three key insights</h2><ol>(.*?)</ol>")
_INSIGHT = re.compile(r"<li><strong>(.*?)</strong>")


def _span(ref: str) -> tuple[int, int] | None:
    """A reference's first and last verse ids, or None when it is not one."""
    ids = scripture.reference_verse_ids(ref)
    return (min(ids), max(ids)) if ids else None


def _gather(sections, entries, label, by_theme, refs) -> None:
    """Add one volume's key insights (by theme) and Scripture citations to the
    running indexes; ``label(i, title)`` names a section in an index line."""
    if [title for title, _ in sections] != [e["title"] for e in entries]:
        raise CommandError("volume's chapters.json titles do not match the manuscript's ## headings, in order")
    for i, ((title, body), e) in enumerate(zip(sections, entries, strict=True)):
        name = label(i, title)
        found = _INSIGHTS.search(body)
        insights = [html.unescape(x) for x in _INSIGHT.findall(found.group(1))] if found else []
        if len(insights) != len(e["themes"]):
            raise CommandError(f"{title!r}: {len(insights)} key insights in the prose, {len(e['themes'])} themes in chapters.json")
        for text, theme in zip(insights, e["themes"], strict=True):
            if theme not in by_theme:
                raise CommandError(f"{title!r}: unknown theme {theme!r}; add it to THEMES")
            by_theme[theme].append(f"- **{text}** {name} ({e['anchor']})")
        anchor = _span(e["anchor"])
        cited = {(c["start"], c["end"]): c["ref"] for c in scripture.extract_citations(body)}
        if anchor not in cited:
            raise CommandError(f"{title!r}: its key verse {e['anchor']!r} is not cited in the chapter")
        for span, ref in cited.items():
            r = refs.setdefault(span, {"ref": ref, "chapters": []})
            r["chapters"].append(name + (" (key verse)" if span == anchor else ""))


def _insights_md(heading: str, intro: str, by_theme: dict[str, list[str]]) -> list[str]:
    out = [heading, "", intro]
    for theme in THEMES:
        if by_theme[theme]:
            out += ["", f"### {theme}", "", *by_theme[theme]]
    return out


def _scripture_md(heading: str, intro: str, refs: dict) -> list[str]:
    out = [heading, "", intro]
    book_heading = None
    for _, r in sorted(refs.items()):
        if (book := scripture.book_of(r["ref"])) is None:
            raise CommandError(f"{r['ref']!r} names no book of the Bible")
        if book[0] != book_heading:
            book_heading = book[0]
            out += ["", f"### {book_heading}", ""]
        out.append(f"- **{r['ref']}**: {'; '.join(r['chapters'])}")
    return out


def appendices(sections: list[tuple[str, str]], entries: list[dict]) -> str:
    """Both appendices for a volume from its parsed ``(title, html)`` sections."""
    last = len(entries) - 1
    by_theme: dict[str, list[str]] = {t: [] for t in THEMES}
    refs: dict[tuple[int, int], dict] = {}
    _gather(sections, entries, lambda i, title: _label(i, last, title), by_theme, refs)
    out = _insights_md(
        "## Appendix 1: Key Insights",
        "Every chapter of this book closes with three key insights. Here they are "
        "gathered by theme, each pointing back to the chapter where it is taught "
        "and to that chapter's key verse.",
        by_theme,
    )
    out += ["", "---", ""]
    out += _scripture_md(
        "## Appendix 2: Scripture Index",
        "Every passage of Scripture quoted or referred to in this book, in Bible "
        'order, with the chapters where it appears. "Key verse" marks the '
        "Scripture a chapter is built on.",
        refs,
    )
    return "\n".join(out) + "\n"


# ── The series appendices (the last volume only) ────────────────────────────

# The last volume closes the series: in place of its own two appendices it
# carries five for the whole series. A, B, C and E are generated from every
# volume's manuscript and records; D, the methods toolkit, is written by hand.
FINAL_VOLUME = 11
TOOLKIT = SERIES_DIR / "series-toolkit.md"

_YEAR = re.compile(r"\d+")


def era_year(era: str) -> int:
    """A sortable year for a record's ``era``: its first number, negative when
    the era is BC; "today" and the like sort last."""
    found = _YEAR.search(era)
    if not found:
        return 10_000
    year = int(found.group())
    return -year if "BC" in era[found.end():] else year


def _series_label(volume: int, last: int):
    def label(i: int, title: str) -> str:
        if i == 0:
            return f"Vol. {volume}, Introduction"
        if i == last:
            return f"Vol. {volume}, Conclusion"
        return f"Vol. {volume}, ch. {i}, *{title}*"

    return label


def _book_titles() -> dict[str, str]:
    """``slug -> "*Title*, Author"`` for every English book the reading list may name."""
    from library.content_fixtures import BOOKS_DIR

    authors = {
        r["fields"]["slug"]: r["fields"]["name"]
        for r in json.loads((BOOKS_DIR.parent / "authors.json").read_text())
    }
    titles = {}
    for path in BOOKS_DIR.glob("*.en.json"):
        book = json.loads(path.read_text())[0]["fields"]
        titles[path.name[: -len(".en.json")]] = f"*{book['title']}*, {authors.get(book['author'][0], '')}".rstrip(", ")
    return titles


def series_appendices(volumes: dict[int, tuple[list[tuple[str, str]], list[dict]]]) -> str:
    """The series appendices A to E from every volume's ``(sections, entries)``."""
    by_theme: dict[str, list[str]] = {t: [] for t in THEMES}
    refs: dict[tuple[int, int], dict] = {}
    for volume, (sections, entries) in sorted(volumes.items()):
        _gather(sections, entries, _series_label(volume, len(entries) - 1), by_theme, refs)
    out = _insights_md(
        "## Appendix A: Key Insights from the Whole Series",
        "Every chapter of every volume closes with three key insights. Here they are "
        "all gathered by theme, each pointing back to its volume and chapter and to "
        "that chapter's key verse.",
        by_theme,
    )
    out += ["", "---", ""]
    out += _scripture_md(
        "## Appendix B: Scripture Index to the Whole Series",
        "Every passage of Scripture quoted or referred to in the eleven volumes, in "
        'Bible order, with the volumes and chapters where it appears. "Key verse" '
        "marks the Scripture a chapter is built on.",
        refs,
    )

    lives = []
    for volume, (sections, entries) in sorted(volumes.items()):
        if volume == FINAL_VOLUME:
            continue
        for i, e in enumerate(entries[1:-1], start=1):
            lives.append((era_year(e["era"]), volume, i, e))
    out += [
        "",
        "---",
        "",
        "## Appendix C: Timeline",
        "",
        "Every person and movement in the series on one line, in the order of their "
        "times. Dates are as each chapter gives them, most of them approximate.",
        "",
    ]
    for _, volume, i, e in sorted(lives, key=lambda x: x[:3]):
        out.append(f"- **{e['era']}**: {e['person']}, {e['region']}. Vol. {volume}, ch. {i}, *{e['title']}*")

    out += ["", "---", "", TOOLKIT.read_text().strip(), "", "---", ""]

    titles = _book_titles()
    out += [
        "## Appendix E: Keep Reading on Ochorus",
        "",
        "The books in the Ochorus library that each chapter recommends, volume by "
        "volume, so that you can go on listening to the witnesses in their own words.",
    ]
    for volume, (sections, entries) in sorted(volumes.items()):
        out += ["", f"### Volume {volume}", ""]
        for i, e in enumerate(entries[1:-1], start=1):
            books = [titles[s] for s in e.get("read_more", []) if s in titles]
            if books:
                out.append(f"- **Ch. {i}, *{e['title']}***: {'; '.join(books)}")
    return "\n".join(out) + "\n"


def chapter_rows(volume: int) -> tuple[list[tuple[str, str]], str]:
    """A volume's chapters as they are stored, ``(title, body_html)`` with the
    appendices last, through the same cleaning every Original's text takes; and
    the generated appendices' Markdown."""
    sections, generated = volume_text(volume)
    check_shape(sections)
    rows = []
    for order, (title, body) in enumerate(sections + parse(generated), start=1):
        body, _ = convert(clean_fragment(body), outer_guillemets=False)
        title, _ = convert(title, outer_guillemets=False)
        rows.append((title, settled_chapter_body(VOLUMES[volume]["slug"], order, body)))
    return rows, generated


def volume_text(volume: int) -> tuple[list[tuple[str, str]], str]:
    """A volume's parsed manuscript sections and its generated appendices."""
    sections, entries = _volume_records(volume)
    if volume != FINAL_VOLUME:
        return sections, appendices(sections, entries)
    return sections, series_appendices({v: _volume_records(v) for v in sorted(VOLUMES)})


def _volume_records(volume: int) -> tuple[list[tuple[str, str]], list[dict]]:
    """A volume's parsed manuscript sections and its chapter records."""
    stem = SERIES_DIR / f"volume-{volume:02d}"
    return parse(stem.with_suffix(".md").read_text()), json.loads(stem.with_suffix(".chapters.json").read_text())


# ── The book ────────────────────────────────────────────────────────────────


def check_shape(sections: list[tuple[str, str]]) -> None:
    """Introduction, the chapters, Conclusion — each chapter in full shape."""
    titles = [title for title, _ in sections]
    if not titles[0].startswith("Introduction") or not titles[-1].startswith("Conclusion"):
        raise CommandError(f"manuscript is not Introduction, chapters, Conclusion: {titles}")
    for title, body in sections[1:-1]:
        missing = [label for label in REQUIRED if f"<h2>{label}</h2>" not in body]
        if missing:
            raise CommandError(f"{title!r}: missing {missing}.")


class Command(BaseCommand):
    help = "Build a volume of A Cloud of Praying Witnesses (and its appendices) from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int, choices=sorted(VOLUMES))

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        meta = VOLUMES[volume]
        slug = meta["slug"]
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc
        try:
            series = Series.objects.get(slug=SERIES_SLUG)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {SERIES_SLUG!r} not found — load series.json first.") from exc

        rows, generated = chapter_rows(volume)
        (SERIES_DIR / f"volume-{volume:02d}.appendices.md").write_text(generated)

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series,
            "series_position": volume,
            **meta["book"],
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": book_sort_order(slug),
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(rows, start=1):
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order}: {title[:56]:56} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
