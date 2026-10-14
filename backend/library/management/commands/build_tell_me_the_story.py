"""Build a volume of *Tell Me the Story* — Bible stories for children — from its manuscript.

A house-written storybook Bible for readers aged 6–10, in three parts (Old
Testament Stories, The Life of Jesus, New Testament Stories) across eight
books. Each volume is an Introduction and then the stories, every one short
enough to read aloud at bedtime: an opening BSB verse, the story, a "Looking
ahead to Jesus" line where the New Testament itself makes the link, "Read it
in your Bible", a closing prayer, and three questions to talk about together.
It sits below *The Big Story* (the whole Bible for ages 13–17) and beside
*Brave for God* (true lives for ages 8–12).

The prose is committed as Markdown under
``data/tell-me-the-story/tell-me-the-story-<n>.md`` (Ochorus's own writing,
nothing fetched; ``OUTLINE.md`` beside it holds the stance and the plan) in the
closed Markdown subset of ``build_rooted.parse``, plus one block of its own: a
story's ``### Talk about it together`` section of ``- Q:`` / ``  A:`` pairs,
which is lifted out of the body into ``Chapter.study_questions`` — the reader
folds the answers for the grown-up, and read-aloud speaks only the questions.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/tell-me-the-story-<n>.en.json``. Idempotent. The
series row itself lives in ``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_tell_me_the_story 1
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import (
    AUTHOR_SLUG,
    DATA_DIR,
    _single_marks,
    parse,
)
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES = "tell-me-the-story"
QUESTIONS_HEADING = "### Talk about it together"
QUESTIONS = 3
# About four minutes read aloud at the children's gentle 0.9× speed. Under
# this a story is a summary; over it, it is no longer a bedtime story.
MIN_STORY_WORDS, MAX_STORY_WORDS = 350, 800

ATTRIBUTION = (
    "© Ochorus. An Ochorus Original, written for children, free to read and "
    "share. The stories are the Bible's own, retold in simple words. Scripture "
    "quotations are from the Berean Standard Bible (BSB), which is in the "
    "public domain."
)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 1: In the Beginning",
        "subtitle": "Old Testament Stories from Genesis",
        "cover_url": "/covers/art/tell-me-the-story-1.jpg",
        "cover_color": covers.ink_safe("#2f6f8f"),  # a first-morning sky
        "description": (
            "Twenty-one Bible stories from Genesis for children aged 6 to 10, "
            "each short enough to read aloud at bedtime: God making the world, "
            "the snake's trick, Noah and the rainbow, Abraham counting the "
            "stars, Jacob's stairway to heaven, and Joseph from his colourful "
            "robe to “I am Joseph!” Every story ends with a prayer and "
            "three questions to talk about together. The first book of Tell Me "
            "the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "Its name comes from Katherine Hankey’s hymn “Tell Me the "
            "Old, Old Story”. God is the hero of every story, and the "
            "whole Bible is one story that leads to Jesus.</p>"
            "<p>Book 1, “In the Beginning”, tells twenty-one stories "
            "from Genesis, from creation to Joseph forgiving his brothers. Each "
            "takes about four minutes to read aloud. It opens with a verse from "
            "the Bible and ends with a short prayer. Where the New Testament "
            "itself links a story to Jesus, as John 1:51 does with Jacob’s "
            "stairway, a line says so.</p>"
            "<p>The stories stay close to what the Bible says, and the people "
            "in them say what the Bible says they said, in simple words. Hard "
            "stories, like Cain and Abel, the flood and Abraham on the mountain, "
            "are told honestly but gently. Under each story are three questions "
            "to talk about together, with answers for the grown-up reading "
            "along, and the passage to find in your own Bible.</p>"
        ),
        "qa": [
            {
                "question": "What is Tell Me the Story?",
                "answer": "A storybook Bible for children aged 6 to 10, in eight books: three of Old Testament Stories, three on the life of Jesus, and two of New Testament Stories. Each story is short enough to read aloud at bedtime and ends with a prayer and three questions to talk about together.",
            },
            {
                "question": "Which stories are in Book 1?",
                "answer": "Twenty-one stories from Genesis: creation, the garden, the snake's trick, Cain and Abel, Noah, the rainbow, the tower of Babel, Abram setting out, counting the stars, Sarah laughing, Hagar and the God who sees, Abraham on the mountain, Rebekah at the well, Jacob and Esau, Jacob's stairway, Jacob wrestling, and five stories of Joseph.",
            },
            {
                "question": "Does it change what the Bible says?",
                "answer": "No. The stories are retold in simple words, but they add no events, characters or speeches the Bible doesn't give. Every verse quoted with its reference is word for word from the Berean Standard Bible.",
            },
            {
                "question": "Are the hard stories suitable for young children?",
                "answer": "They are told honestly but gently, without frightening detail. Cain and Abel, the flood and Abraham on the mountain are each told in a sentence or two, and then the story turns to what God did. The questions help a grown-up talk them through.",
            },
            {
                "question": "How does it point to Jesus?",
                "answer": "Where the New Testament itself links an Old Testament story to Jesus, such as Jacob's stairway (John 1:51) or the lamb God provided (John 1:29), the story ends with a short \"Looking ahead to Jesus\" line. Where the New Testament makes no link, the story doesn't force one.",
            },
            {
                "question": "Can it be read aloud?",
                "answer": "Yes, that is what it is written for. Each story takes about four minutes to read aloud. Each chapter also has a Listen button that reads the story at a gentle speed and then asks the three questions.",
            },
        ],
    },
    2: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 2: Out of Egypt",
        "subtitle": "Old Testament Stories from Exodus to Ruth",
        "cover_url": "/covers/art/tell-me-the-story-2.jpg",
        "cover_color": covers.ink_safe("#8a5a2b"),  # desert sand at dusk
        "description": (
            "Twenty-one Bible stories from Exodus to Ruth for children aged 6 "
            "to 10, each short enough to read aloud at bedtime: the baby in the "
            "basket, the burning bush, the Passover, the path through the sea, "
            "bread from heaven, the walls of Jericho, Deborah, Gideon's three "
            "hundred, and Ruth and Boaz. Every story ends with a prayer and "
            "three questions to talk about together. The second book of Tell "
            "Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 2, “Out of Egypt”, tells twenty-one stories from Exodus, "
            "Numbers, Joshua, Judges and Ruth: how God rescued His people from "
            "slavery, fed them in the desert, gave them His commandments and "
            "brought them into the promised land. It meets brave women like "
            "Rahab, Deborah and Ruth, and ends with the birth of King David’s "
            "grandfather. Where the New Testament itself links a story to "
            "Jesus, as John 3:14 does with the bronze snake, a line says so.</p>"
            "<p>The stories stay close to what the Bible says, and the people "
            "in them say what the Bible says they said, in simple words. Hard "
            "stories, like the Passover night, the golden calf, Jericho and "
            "Samson, are told honestly but gently. Each takes about four minutes "
            "to read aloud, and under each are three questions to talk about "
            "together, with answers for the grown-up reading along. Book 1 is "
            "not required.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 2 of Tell Me the Story?",
                "answer": "Twenty-one stories from Exodus to Ruth: baby Moses, the burning bush, the plagues, the Passover, the path through the sea, manna, Moses' tired arms, the Ten Commandments, the golden calf, the tabernacle, the twelve spies, the bronze snake, Balaam's donkey, Rahab, crossing the Jordan, Jericho, Deborah, Gideon, Samson, and two stories of Ruth.",
            },
            {
                "question": "Do I need to read Book 1 first?",
                "answer": "No. Each book stands on its own. Book 2 begins with a short introduction that picks up the story from Joseph's family in Egypt.",
            },
            {
                "question": "How are hard stories like the Passover and Jericho told?",
                "answer": "Honestly but gently. The Passover night, Jericho and Samson's death are each told in a sentence or two without frightening detail, and the questions help a grown-up talk them through.",
            },
            {
                "question": "How does it point to Jesus?",
                "answer": "Where the New Testament itself links a story to Jesus, a short \"Looking ahead to Jesus\" line says so: the Passover lamb (1 Corinthians 5:7), the manna (John 6:35), the rock (1 Corinthians 10:4), the tabernacle (John 1:14), the bronze snake (John 3:14), and Rahab and Ruth in Jesus' family tree (Matthew 1:5).",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
            {
                "question": "Can it be read aloud at bedtime?",
                "answer": "Yes, that is what it is written for. Each story takes about four minutes to read aloud, and each chapter has a Listen button that reads it at a gentle speed and then asks the three questions.",
            },
        ],
    },
    3: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 3: Kings and Prophets",
        "subtitle": "Old Testament Stories from Samuel to Nehemiah",
        "cover_url": "/covers/art/tell-me-the-story-3.jpg",
        "cover_color": covers.ink_safe("#5b3f86"),  # royal purple
        "description": (
            "Twenty-two Bible stories from Samuel to Nehemiah for children aged "
            "6 to 10, each short enough to read aloud at bedtime: Hannah's "
            "prayer, the boy Samuel, David and Goliath, Elijah and the fire, "
            "Naaman, Jonah, Isaiah's promise of a child, the fiery furnace, "
            "Daniel and the lions, Queen Esther and Nehemiah's wall. Every "
            "story ends with a prayer and three questions to talk about "
            "together. The third book of Tell Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 3, “Kings and Prophets”, is the last of the Old Testament "
            "Stories. It tells twenty-two stories from 1 Samuel to Nehemiah: "
            "the kings God gave His people, from Saul and David to the boy "
            "king Josiah; the prophets He sent, from Samuel and Elijah to Jonah "
            "and Isaiah; and the brave ones who stayed faithful far from home, "
            "like Daniel and Queen Esther. It ends with the people waiting for "
            "the King God promised. Where the New Testament itself links a "
            "story to Jesus, as Matthew 12:40 does with Jonah, a line says "
            "so.</p>"
            "<p>The stories stay close to what the Bible says, and the people "
            "in them say what the Bible says they said, in simple words. Hard "
            "stories, like David’s sin, Mount Carmel and the lions’ den, are "
            "told honestly but gently. Each takes about four minutes to read "
            "aloud, and under each are three questions to talk about together, "
            "with answers for the grown-up reading along. The earlier books are "
            "not required.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 3 of Tell Me the Story?",
                "answer": "Twenty-two stories from 1 Samuel to Nehemiah: Hannah, Samuel hearing God, David chosen, David and Goliath, David and Jonathan, David sparing Saul, Mephibosheth, Nathan's story of the lamb, Solomon's wisdom, Elijah and the ravens, the fire on Mount Carmel, the still small voice, Naaman, the chariots of fire, Josiah, two stories of Jonah, Isaiah's promise, the fiery furnace, Daniel and the lions, Esther and Nehemiah.",
            },
            {
                "question": "Do I need to read Books 1 and 2 first?",
                "answer": "No. Each book stands on its own. Book 3 begins with a short introduction that explains what kings and prophets are.",
            },
            {
                "question": "How is David's sin with Bathsheba told?",
                "answer": "Simply and gently: David wanted another man's wife and had her husband killed in battle. The story then turns to Nathan's parable of the little lamb, David's confession and God's forgiveness, with Psalm 51. A note for the grown-up says no more needs explaining than a child asks.",
            },
            {
                "question": "How does it point to Jesus?",
                "answer": "Where the New Testament itself links a story to Jesus, a short \"Looking ahead to Jesus\" line says so: David's city of Bethlehem (Luke 2:11), One greater than Solomon (Matthew 12:42), Elijah's widow and Naaman in Jesus' own sermon (Luke 4:26–27), Jonah's three days (Matthew 12:40–41), and Isaiah's promises fulfilled (Matthew 1:23).",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
            {
                "question": "Can it be read aloud at bedtime?",
                "answer": "Yes, that is what it is written for. Each story takes about four minutes to read aloud, and each chapter has a Listen button that reads it at a gentle speed and then asks the three questions.",
            },
        ],
    },
    4: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 4: The King Is Born",
        "subtitle": "The Life of Jesus, from His Birth to the First Disciples",
        "cover_url": "/covers/art/tell-me-the-story-4.jpg",
        "cover_color": covers.ink_safe("#1f4f6e"),  # a starlit night
        "description": (
            "Twenty-one Bible stories for children aged 6 to 10 that begin the "
            "Life of Jesus, each short enough to read aloud at bedtime: the angel "
            "in the temple, Mary's yes, the birth in Bethlehem, the shepherds, "
            "the wise men, the boy in the temple, Jesus' baptism, water into wine, "
            "the woman at the well and the first fishermen. Every story ends with "
            "a prayer and three questions to talk about together. The fourth book "
            "of Tell Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 4, “The King Is Born”, begins the Life of Jesus. It tells "
            "twenty-one stories from Matthew, Luke and John: the births of John "
            "and Jesus, the shepherds and the wise men, Simeon and Anna, the boy "
            "Jesus in the temple, His baptism and testing, and the beginning of "
            "His work, from the wedding at Cana and the woman at the well to "
            "the fishermen who left their nets. Where the Gospels themselves say "
            "an Old Testament promise came true, as Matthew 2:6 does with "
            "Bethlehem, a line called “The promise kept” says so.</p>"
            "<p>The stories stay close to what the Bible says, and the people in "
            "them say what the Bible says they said, in simple words. Each takes "
            "about four minutes to read aloud, and under each are three questions "
            "to talk about together, with answers for the grown-up reading along. "
            "Its Christmas stories, with Old Testament promise stories from Books "
            "1 to 3, make up the Advent reading plan “Tell Me the Christmas "
            "Story”.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 4 of Tell Me the Story?",
                "answer": "Twenty-one stories from the Gospels: Zechariah in the temple, Mary and the angel, Mary visits Elizabeth, John's birth, Joseph's dream, Jesus born in Bethlehem, the shepherds, Simeon and Anna, the wise men, the escape to Egypt, the boy in the temple, John the Baptist, Jesus' baptism, the testing in the desert, the first disciples, water into wine, Nicodemus, the woman at the well, the official's son, Jesus in Nazareth, and the fishermen.",
            },
            {
                "question": "Is it good for reading at Christmas?",
                "answer": "Yes. The first eight stories tell the Christmas story from the angel's visit to Zechariah to Simeon and Anna, and the wise men follow. With promise stories from the earlier books they make up a 25-day Advent reading plan, Tell Me the Christmas Story, for 1 to 25 December.",
            },
            {
                "question": "Does it add things the Bible doesn't say, like a donkey or a stable?",
                "answer": "No. The stories keep to the Gospels, which mention a manger and no room in the inn, but no stable, donkey or innkeeper. The wise men visit a house some time later, and the Bible doesn't say how many there were. Notes for the grown-up point these out where a nativity play might have taught otherwise.",
            },
            {
                "question": "What is \"The promise kept\"?",
                "answer": "In the Life of Jesus books, a short line under some stories shows where the Gospels themselves say an Old Testament promise came true: Isaiah's Immanuel (Matthew 1:23), Micah's Bethlehem (Matthew 2:6), Hosea's \"Out of Egypt\" (Matthew 2:15), Isaiah's voice in the wilderness (Matthew 3:3), and others.",
            },
            {
                "question": "Do I need to read Books 1 to 3 first?",
                "answer": "No. Each book stands on its own, and Book 4's introduction recalls the promises from the Old Testament books. Children who have read them will spot the links, like Jacob's stairway and the bronze snake, which Jesus Himself points back to.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
        ],
    },
    5: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 5: Wonders and Stories",
        "subtitle": "The Life of Jesus: His Miracles and His Parables",
        "cover_url": "/covers/art/tell-me-the-story-5.jpg",
        "cover_color": covers.ink_safe("#2e6a4f"),  # Galilee hills
        "description": (
            "Twenty-one Bible stories for children aged 6 to 10 of the wonders "
            "Jesus did and the stories He told, each short enough to read aloud at "
            "bedtime: the man let down through the roof, the storm stilled, "
            "Jairus's daughter, five loaves and two fish, the good Samaritan, the "
            "lost sheep and the lost son, Zacchaeus, and Lazarus raised. Every "
            "story ends with a prayer and three questions to talk about together. "
            "The fifth book of Tell Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 5, “Wonders and Stories”, is the middle book of the Life of "
            "Jesus. It tells twenty-one stories from the Gospels: miracles that "
            "only God could do, from calming a storm to raising the dead, and the "
            "parables Jesus told about seeds, builders, sheep, coins and a son who "
            "came home, along with the Sermon on the Mount and the Lord’s Prayer. "
            "It asks the question the crowds asked, “Who is this?”, and ends with "
            "Lazarus, which leads into the last week of Jesus’ life. Where the "
            "Gospels themselves say an Old Testament promise came true, a line "
            "called “The promise kept” says so.</p>"
            "<p>The stories stay close to what the Bible says, and the people in "
            "them say what the Bible says they said, in simple words. Each takes "
            "about four minutes to read aloud, and under each are three questions "
            "to talk about together, with answers for the grown-up reading along. "
            "The earlier books are not required.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 5 of Tell Me the Story?",
                "answer": "Twenty-one stories from the Gospels: the man through the roof, Matthew the tax collector, the Beatitudes, the Lord's Prayer and the birds, the wise and foolish builders, the centurion's servant, the widow's son at Nain, the storm on the lake, the farmer and the seeds, Jairus's daughter, the five loaves, walking on water, the good Samaritan, Mary and Martha, the lost sheep and coin, the lost son, the ten lepers, Jesus and the children, Bartimaeus, Zacchaeus and Lazarus.",
            },
            {
                "question": "Does it include Jesus' parables as well as His miracles?",
                "answer": "Yes. Alongside the miracles it tells the parables of the wise and foolish builders, the farmer and the seeds, the good Samaritan, the lost sheep, the lost coin and the lost son, each with what it teaches about God.",
            },
            {
                "question": "Is the Lord's Prayer in it?",
                "answer": "Yes, in the story \"Look at the Birds\", with a simple explanation of what its lines mean, alongside Jesus' words about not worrying.",
            },
            {
                "question": "How are the stories about death told?",
                "answer": "Gently and with hope. The widow's son, Jairus's daughter and Lazarus each show that Jesus is stronger than death, and the questions for the grown-up suggest talking gently with a child who has lost someone.",
            },
            {
                "question": "Do I need to read the earlier books first?",
                "answer": "No. Each book stands on its own. Book 5 begins with a short introduction, and children who have read Book 4 will know the disciples already.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
        ],
    },
    6: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 6: The Greatest Rescue",
        "subtitle": "The Life of Jesus: His Last Week, His Death and His Rising Again",
        "cover_url": "/covers/art/tell-me-the-story-6.jpg",
        "cover_color": covers.ink_safe("#7a3b2e"),  # Easter dawn
        "description": (
            "Twenty-two Bible stories for children aged 6 to 10 that finish the "
            "Life of Jesus, each short enough to read aloud: the shining mountain, "
            "Palm Sunday, the Last Supper, the garden, the cross, the empty tomb, "
            "Mary in the garden, the road to Emmaus, Thomas, breakfast on the "
            "beach and the ascension. Told honestly and gently, with a prayer and "
            "three questions to talk about after every story. The sixth book of "
            "Tell Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 6, “The Greatest Rescue”, is the last book of the Life of "
            "Jesus and the heart of the whole series. It tells twenty-two stories "
            "from the Gospels and Acts: the Transfiguration, Jesus’ last week in "
            "Jerusalem, His arrest, trial, death and burial, and His rising again, "
            "from the empty tomb to breakfast on the beach, the Great Commission "
            "and the ascension. Where the Gospels themselves say an Old Testament "
            "promise came true, as they do with the donkey, the dividing of His "
            "clothes and the cry from the cross, a line called “The promise kept” "
            "says so.</p>"
            "<p>The cross is told plainly and without graphic detail, and the "
            "questions for the grown-up help a child talk it through. Each story "
            "takes about four minutes to read aloud, and under each are three "
            "questions to talk about together, with answers for the grown-up "
            "reading along. It reads well through Holy Week and Easter.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 6 of Tell Me the Story?",
                "answer": "Twenty-two stories: the shining mountain, Mary's perfume, Palm Sunday, the children singing in the temple, the widow's two coins, Jesus washing feet, the Last Supper, the garden of Gethsemane, the arrest, Peter's denials, Jesus and Pilate, the cross, \"It is finished\", the burial, the empty tomb, Mary in the garden, the road to Emmaus, Jesus appearing to the disciples, Thomas, breakfast on the beach, the Great Commission and the ascension.",
            },
            {
                "question": "How is the crucifixion told for young children?",
                "answer": "Plainly and gently. The story says that Jesus was whipped, crowned with thorns and nailed to a cross, without dwelling on the details. It focuses on what Jesus said and did: forgiving the soldiers, promising paradise to the thief, caring for His mother, and \"It is finished.\" The grown-up notes suggest letting a child ask whatever they need to.",
            },
            {
                "question": "Is it good for reading at Easter?",
                "answer": "Yes. Its stories follow the days of Holy Week, from Palm Sunday and the Last Supper to Good Friday and the empty tomb on Easter Sunday, and then the appearances of the risen Jesus.",
            },
            {
                "question": "What is \"The promise kept\"?",
                "answer": "A short line under some stories, used only where the Gospels themselves say an Old Testament promise came true: Zechariah's King on a donkey (Matthew 21:5), Psalm 8's children's praise (Matthew 21:16), Psalm 22's divided clothes and cry (John 19:24; Matthew 27:46), the Passover lamb (1 Corinthians 5:7), and the whole Scripture explained on the road to Emmaus (Luke 24:27).",
            },
            {
                "question": "Do I need to read Books 4 and 5 first?",
                "answer": "No. Each book stands on its own, and Book 6 begins with a short introduction. Children who have read the earlier books will recognise Peter, Mary and Martha, Nicodemus, and the Old Testament stories that the road to Emmaus brings together.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
        ],
    },
    7: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 7: The Church Begins",
        "subtitle": "New Testament Stories from Acts 1–13",
        "cover_url": "/covers/art/tell-me-the-story-7.jpg",
        "cover_color": covers.ink_safe("#9a4a1c"),  # Pentecost flame
        "description": (
            "Twenty Bible stories from Acts for children aged 6 to 10, each short "
            "enough to read aloud at bedtime: wind and fire at Pentecost, the man "
            "at the Beautiful Gate, prison doors opened in the night, brave "
            "Stephen, Philip and the man from Ethiopia, Saul on the Damascus road, "
            "Dorcas, Peter's dream, Rhoda at the gate and Barnabas and Saul sent "
            "out. Every story ends with a prayer and three questions to talk about "
            "together. The seventh book of Tell Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 7, “The Church Begins”, opens the New Testament Stories. It "
            "tells twenty stories from Acts 1–13: the Holy Spirit coming at "
            "Pentecost, the first church sharing everything, the apostles who "
            "could not stop speaking about Jesus, Stephen, Philip, Saul’s "
            "turning on the Damascus road, Dorcas, Peter and Cornelius, and the "
            "church at Antioch sending Barnabas and Saul out to the world. Where "
            "Acts itself says an Old Testament promise came true, as it does with "
            "Joel’s promise of the Spirit, a line called “The promise kept” says "
            "so.</p>"
            "<p>The stories stay close to what the Bible says, in simple words. "
            "Stephen’s death and the killing of James are told honestly and "
            "gently. Each story takes about four minutes to read aloud, and under "
            "each are three questions to talk about together, with answers for "
            "the grown-up reading along. The earlier books are not required.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 7 of Tell Me the Story?",
                "answer": "Twenty stories from Acts: Pentecost, Peter's sermon, the first church sharing, the man at the Beautiful Gate, the apostles before the council, the prison doors opened, the seven helpers, Stephen, Philip in Samaria, Philip and the Ethiopian, Saul's conversion, Ananias, the escape in a basket, Dorcas, Peter's dream, Cornelius, the first Christians at Antioch, Peter in prison, Rhoda at the gate, and Barnabas and Saul sent out.",
            },
            {
                "question": "How is Stephen's death told for young children?",
                "answer": "Honestly and gently, in a few sentences. The story dwells on Stephen seeing Jesus standing to welcome him and on his prayer of forgiveness for the people throwing stones, just like Jesus on the cross. The grown-up notes suggest letting a child ask about it.",
            },
            {
                "question": "Does it include Saul's conversion?",
                "answer": "Yes, in three stories: the light on the Damascus road, brave Ananias who called his enemy \"Brother Saul\", and the escape over the wall in a basket, with Barnabas standing up for him in Jerusalem. The book ends with Barnabas and Saul being sent out, which leads into Book 8.",
            },
            {
                "question": "What is \"The promise kept\"?",
                "answer": "A short line under some stories, used only where Acts itself says an Old Testament promise came true: Joel's promise of the Spirit (Acts 2:16), the rejected cornerstone of Psalm 118 (Acts 4:11), Isaiah 53 read by the Ethiopian (Acts 8:32–35), and the prophets' witness to forgiveness (Acts 10:43).",
            },
            {
                "question": "Do I need to read the earlier books first?",
                "answer": "No. Each book stands on its own, and Book 7 begins with a short introduction that picks up from Jesus going back to heaven. Children who have read the earlier books will recognise Peter, the tower of Babel, and Joseph's \"God meant it for good\".",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
        ],
    },
    8: {
        "publication_year": 2026,
        "title": "Tell Me the Story – Book 8: To the Ends of the Earth",
        "subtitle": "New Testament Stories from Acts 13 to Revelation",
        "cover_url": "/covers/art/tell-me-the-story-8.jpg",
        "cover_color": covers.ink_safe("#1f6a5a"),  # sea and new earth
        "description": (
            "Twenty-one Bible stories for children aged 6 to 10 that finish the "
            "series, each short enough to read aloud at bedtime: Lydia by the "
            "river, Paul and Silas singing in prison, the altar to an unknown god, "
            "Paul's brave nephew, the storm and the shipwreck, the snake on Malta, "
            "Timothy, Onesimus, the armour of God and John's vision of all things "
            "made new. Every story ends with a prayer and three questions to talk "
            "about together. The eighth book of Tell Me the Story."
        ),
        "about_html": (
            "<p>Tell Me the Story is an original Ochorus storybook Bible for "
            "children aged 6 to 10, in eight books and three parts: Old "
            "Testament Stories, The Life of Jesus, and New Testament Stories. "
            "God is the hero of every story, and the whole Bible is one story "
            "that leads to Jesus.</p>"
            "<p>Book 8, “To the Ends of the Earth”, is the last book of the "
            "series. It follows Paul from Lystra to Rome through Acts 13–28, "
            "with its riots, prisons, storm and shipwreck; opens four of the "
            "letters, to Timothy, to Philemon about the runaway Onesimus, on what "
            "love is like and on the armour of God; and ends with John’s vision "
            "in Revelation of a new heaven and a new earth, where the tree of "
            "life from the first garden stands again by the river of life.</p>"
            "<p>The stories stay close to what the Bible says, in simple words. "
            "Paul’s beatings and stoning are told gently, and Revelation is kept "
            "to its plain heart: Jesus is King, and God will make all things new. "
            "Each story takes about four minutes to read aloud, and under each "
            "are three questions to talk about together, with answers for the "
            "grown-up reading along. The earlier books are not required.</p>"
        ),
        "qa": [
            {
                "question": "Which stories are in Book 8 of Tell Me the Story?",
                "answer": "Twenty-one stories: Paul and Barnabas mistaken for gods, Lydia, Paul and Silas singing in prison, the unknown god in Athens, Priscilla and Aquila, the riot at Ephesus, Eutychus, goodbye at Miletus, Paul seized in the temple, Paul's nephew, Paul before King Agrippa, the storm, the shipwreck, the snake on Malta, Rome, Timothy, Onesimus, what love is like, the armour of God, John on Patmos, and all things new.",
            },
            {
                "question": "Is this the last book of Tell Me the Story?",
                "answer": "Yes. It finishes the New Testament Stories and the whole series. Its last story, from Revelation 21–22, ends where the first book began: with God and His people together, and the tree of life from the garden standing again in the city of God.",
            },
            {
                "question": "Does it include any of Paul's letters?",
                "answer": "Yes, four of them, each told as a story: Paul's letters to young Timothy, his letter to Philemon about the runaway slave Onesimus, his words on love in 1 Corinthians 13, and the armour of God in Ephesians 6.",
            },
            {
                "question": "How is the book of Revelation told for young children?",
                "answer": "Simply, keeping to its plain heart. One story tells of John seeing the risen Jesus on Patmos, and the other of the new heaven and new earth, with no more tears, death or pain. The book says that parts of Revelation are mysterious and full of pictures, and does not try to explain them.",
            },
            {
                "question": "Do I need to read the earlier books first?",
                "answer": "No. Each book stands on its own, and Book 8 begins with a short introduction. Children who have read the whole series will see the last story tie back to the first: the garden, the curse and the tree of life.",
            },
            {
                "question": "Which Bible translation does it use?",
                "answer": "Every verse quoted with its reference is word for word from the Berean Standard Bible (BSB), which is in the public domain.",
            },
        ],
    },
}

_QUESTION = re.compile(r"^- Q: (.+)$")
_ANSWER = re.compile(r"^  A: (.+)$")


def split_questions(manuscript: str) -> tuple[str, dict[str, list[dict[str, str]]]]:
    """The manuscript without its question blocks, and each story's questions
    keyed by its ``##`` title. A question block runs from its heading to the
    next ``##`` chapter; anything in it but ``- Q:`` / ``  A:`` pairs is an
    error, not a guess."""
    kept: list[str] = []
    questions: dict[str, list[dict[str, str]]] = {}
    title, in_block = None, False
    seen: set[str] = set()
    for line in manuscript.splitlines():
        if line.startswith("## "):
            # Keyed as ``parse`` titles the chapter, curly apostrophes and all.
            title, in_block = _single_marks(line[3:].strip()), False
            if title in seen:
                raise CommandError(f"two chapters are titled {title!r}: their questions would merge")
            seen.add(title)
        elif line.strip() == QUESTIONS_HEADING:
            if title is None:
                raise CommandError("a questions block comes before the first chapter")
            in_block = True
            questions[title] = []
            continue
        if not in_block:
            kept.append(line)
            continue
        if not line.strip():
            continue
        if m := _QUESTION.match(line):
            questions[title].append({"question": _single_marks(m.group(1).strip()), "answer": ""})
        elif (m := _ANSWER.match(line)) and questions[title] and not questions[title][-1]["answer"]:
            questions[title][-1]["answer"] = _single_marks(m.group(1).strip())
        else:
            raise CommandError(f"{title!r}: unexpected line in its questions: {line!r}")
    return "\n".join(kept) + "\n", questions


def check_shape(chapters: list[tuple[str, str]], questions: dict[str, list[dict[str, str]]]) -> None:
    """Introduction, then the stories, each in the young-reader shape and every
    chapter with its questions (the reader wants them on all or none) — checked
    before anything is written, so one bad story never half-rebuilds a volume."""
    titles = [title for title, _ in chapters]
    if len(titles) < 2 or not titles[0].startswith("Introduction"):
        raise CommandError(f"manuscript is not Introduction + stories: {titles}")
    problems = []
    for title, _ in chapters:
        qs = questions.get(title, [])
        if len(qs) != QUESTIONS or not all(q["answer"] for q in qs):
            problems.append(f"{title!r}: needs {QUESTIONS} answered questions, has {len(qs)}")
    for title, body in chapters[1:]:
        wc = word_count(body)
        if not MIN_STORY_WORDS <= wc <= MAX_STORY_WORDS:
            problems.append(f"{title!r}: {wc} words, outside {MIN_STORY_WORDS}–{MAX_STORY_WORDS}")
        if not body.startswith("<blockquote>"):
            problems.append(f"{title!r}: does not open with its verse")
        if "Read it in your Bible:" not in body:
            problems.append(f"{title!r}: no “Read it in your Bible”")
        # The reader's prayer card: a last paragraph that is one <em> and nothing else.
        if not re.search(r"<p><em>(?:(?!</em>).)*Amen\.</em></p>$", body):
            problems.append(f"{title!r}: does not end with its prayer")
    if problems:
        raise CommandError("manuscript shape:\n  " + "\n  ".join(problems))


class Command(BaseCommand):
    help = "Build a volume of Tell Me the Story (Bible stories for children) from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int)

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        if volume not in VOLUMES:
            raise CommandError(f"{SERIES} has no volume {volume}; known: {sorted(VOLUMES)}")
        slug = f"{SERIES}-{volume}"
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc
        try:
            series_row = Series.objects.get(slug=SERIES)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {SERIES!r} not found — load series.json first.") from exc

        manuscript, questions = split_questions((DATA_DIR / SERIES / f"{slug}.md").read_text())
        chapters = parse(manuscript)
        check_shape(chapters, questions)

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series_row,
            "series_position": volume,
            "cover_title": "Tell Me the Story",
            "sort_order": book_sort_order(slug),
            **VOLUMES[volume],
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
            qs = [
                {key: convert(text, outer_guillemets=False)[0] for key, text in qa.items()}
                for qa in questions.get(title, [])
            ]
            title, _ = convert(title, outer_guillemets=False)
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body, study_questions=qs)
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>4} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
