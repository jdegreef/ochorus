"""Curated quotations, by author — the sourced half of the quote pages.

Quote pages are the only page type on this site with no primary text underneath
them: a chapter page is 1,900 words of Bunyan whatever else it carries, but a
quote page IS its furniture. That is the shape search engines classify as a
doorway when it is mass-produced, and the risk is not confined to the quote
pages — scaled thin content is judged against a domain. The pilot shipped ONE
author (Spurgeon) and waited; this is the considered scale-up to ten, chosen
for depth of shelf and quotability, not a blanket rollout of all forty.
Amy Carmichael was a fourth candidate, held back: her aphorisms live in *If*,
which is not published, and a quote may only cite a live page.

HOW THESE WERE CHOSEN, and what that does and does not amount to. A mechanical
pass over each author's on-site English works shortlisted self-contained
sentences of 12-34 words, dropping dangling openers, mid-sentence citations,
quotation marks, parentheticals and sentences about the book rather than about
the faith; a scoring pass favoured contrast, brevity and a recognisable subject;
then a person read the shortlist and chose. Every chosen sentence was confirmed
to appear VERBATIM in exactly one served paragraph of the source — the builder
refused anything it could not find, which is what caught a reworded line that
had crept in.

That last pass is judgement, and it is not the same thing as a human being
saying "yes, print this under his name". Every row therefore seeds
`reviewed=False` and NOTHING reaches a reader until its author is in `APPROVED`.
The public serializer filters on the flag; the page renders only what has been
signed off. This mirrors how AI translations are gated, and for the same reason.

`paragraph` is the 0-INDEXED position of the quote's block among the body's
top-level children AS SERVED — the exact index the reader jumps to
(`body.children[p]`). Counted against the serialized HTML, not the stored
`body_html`, and gated by `tests_quotes` so a value that does not resolve to a
block containing its own text can never ship (the pilot had no such gate, and
eighteen of the sixty Spurgeon rows were off by one until it was added).

Registered in `content_sources.json`, so editing this file rebuilds the reader.
"""

from __future__ import annotations

#: Authors whose quotations a PERSON has read and signed off, recorded here so
#: the decision lives in version control rather than only in a production
#: database — where a rebuild would silently lose it, the way an imported
#: author's stub bio used to outlive every correction (see author_sync.py).
#:
#: charles-h-spurgeon    — approved 2026-08-28, sixty;
#:                         and 2026-09-02, twenty more from Gleanings Among the Sheaves;
#:                         and 2026-09-03, seventeen more from Gleanings — ninety-seven.
#: thomas-a-kempis       — approved 2026-08-30, thirty-six;
#:                          eighteen more 2026-09-07 (fifty-four).
#: andrew-murray         — approved 2026-08-30, twenty-seven;
#:                         and 2026-09-02, twenty-three more (the four new books);
#:                         and 2026-09-23, twenty-five more (With Christ in the School
#:                         of Prayer, lessons 5–31) — seventy-five.
#: e-m-bounds            — approved 2026-08-30, twenty-eight;
#:                          twenty-seven more 2026-09-02 (fifty-five).
#: augustine-of-hippo    — approved 2026-08-30, thirteen;
#:                         and 2026-09-02, six more (Confessions);
#:                         and 2026-09-02, sixteen more (The Enchiridion) — thirty-five;
#:                         and 2026-09-08, fifteen more (Confessions) — fifty.
#: jonathan-edwards      — approved 2026-08-30, eleven;
#:                         and 2026-09-02, ten more (Selected Sermons) — twenty-one;
#:                         and 2026-09-11, twenty-nine more (Religious Affections,
#:                         Selected Sermons, standalone sermons, Freedom of the Will) — fifty.
#: john-wesley           — approved 2026-08-30, eighteen;
#:                         and 2026-09-02, thirteen more (Sermons on Several Occasions) — thirty-one;
#:                         and 2026-09-08, twenty-three more (Sermons on Several Occasions) — fifty-four.
#: george-muller         — approved 2026-08-30, eleven;
#:                         and 2026-09-02, four more (The Life of Trust);
#:                         and 2026-09-02, sixteen more (The Life of Trust) — thirty-one;
#:                         and 2026-09-09, nineteen more (The Life of Trust, Answers to Prayer) — fifty.
#: hudson-taylor         — approved 2026-08-30, ten;
#:                         and 2026-09-02, ten more (Separation and Service);
#:                         and 2026-09-03, thirteen more (Union and Communion, Separation and Service) — thirty-three;
#:                         and 2026-09-08, thirteen more (A Retrospect + four sermons) — forty-six;
#:                         and 2026-09-08, six more (A Ribband of Blue studies) — fifty-two.
#: gareth-evans          — approved 2026-08-30, twenty-two;
#:                          four more 2026-08-31 (twenty-six).
#: richard-allen         — approved 2026-09-02, six (The Life, Experience, and
#:                          Gospel Labours — his antislavery address and his
#:                          address on Christian charity).
#: amanda-berry-smith    — approved 2026-09-02, fifteen (An Autobiography).
#:
#: THIS ONLY EVER PUBLISHES, AT CREATION. `seed_quotes` reads it when it creates
#: a row and never again, which is the same rule `is_published` and
#: `source_type` follow in seed_books: the live database owns TAKEDOWN. Someone
#: who clears `reviewed` on a quotation — a misattribution spotted, a complaint
#: — must not have that undone by the next deploy, so removing an author from
#: this set prevents future publication but does not retract a live one. To pull
#: a published quotation, clear the flag in the database AND drop it here, which
#: is the same two-sided rule authors.json already documents for a portrait.
APPROVED = frozenset(
    {
        "charles-h-spurgeon",
        "thomas-a-kempis",
        "andrew-murray",
        "e-m-bounds",
        "augustine-of-hippo",
        "jonathan-edwards",
        "john-wesley",
        "george-muller",
        "hudson-taylor",
        "gareth-evans",
        "richard-allen",
        "amanda-berry-smith",
    }
)

#: The devotional themes a quotation can be filed under — the vocabulary behind
#: the "Quotes on Prayer" pages (one row per author-theme underneath, e.g.
#: "Andrew Murray Quotes on Prayer"). A SEPARATE vocabulary from the work-topic
#: shelves in `topic_seed.py`: a quote theme is finer and more numerous than a
#: book shelf, and reusing `Topic` would strand themes that hold no books as
#: empty rows on `/topics`. Membership is `TOPIC_MEMBERS` below.
#:
#: `title` is the standalone label ("Prayer", "The Holy Spirit"); the page
#: composes "Quotes on …" from it. The Scripture epigraph is public-domain (KJV)
#: wording, the same furniture the work-topic pages carry. `sort_order` is the
#: list order here.
#:
#: (slug, title, blurb, scripture_ref, scripture_text)
QUOTE_TOPICS = [
    (
        "prayer",
        "Prayer",
        "The classic writers on the life of prayer — the secret place, "
        "persevering intercession, and prayer that prevails.",
        "1 Thessalonians 5:17",
        "Pray without ceasing.",
    ),
    (
        "faith",
        "Faith",
        "Lines on believing God — resting on his promises, and walking by "
        "faith and not by sight.",
        "Hebrews 11:1",
        "Now faith is the substance of things hoped for, the evidence of things not seen.",
    ),
    (
        "grace",
        "Grace",
        "The free favour of God to the undeserving — grace to save, and grace "
        "to keep.",
        "2 Corinthians 12:9",
        "My grace is sufficient for thee: for my strength is made perfect in weakness.",
    ),
    (
        "holy-spirit",
        "The Holy Spirit",
        "The Spirit's indwelling, filling and power — the promised presence for "
        "the Christian life.",
        "Acts 1:8",
        "But ye shall receive power, after that the Holy Ghost is come upon you.",
    ),
    (
        "love-of-god",
        "The Love of God",
        "The love that sought us first, and the love it kindles in return.",
        "1 John 4:10",
        "Herein is love, not that we loved God, but that he loved us.",
    ),
    (
        "humility",
        "Humility",
        "The lowliness that makes room for grace — dying to self, and taking the "
        "lowest place.",
        "1 Peter 5:5",
        "God resisteth the proud, and giveth grace unto the humble.",
    ),
    (
        "suffering",
        "Suffering & Trials",
        "Comfort and counsel for the hard road — affliction, sorrow, and the "
        "glory it works.",
        "2 Corinthians 4:17",
        "For our light affliction, which is but for a moment, worketh for us a far "
        "more exceeding and eternal weight of glory.",
    ),
    (
        "holiness",
        "Holiness",
        "The pursuit of a clean heart and a set-apart life — sanctification, and "
        "the beauty of holiness.",
        "Hebrews 12:14",
        "Follow peace with all men, and holiness, without which no man shall see the Lord.",
    ),
    (
        "the-cross",
        "The Cross of Christ",
        "The atoning death of Jesus — the blood that cleanses, and the glory of "
        "the cross.",
        "Galatians 6:14",
        "But God forbid that I should glory, save in the cross of our Lord Jesus Christ.",
    ),
    (
        "trusting-god",
        "Trusting God",
        "Resting in the providence and faithfulness of God when the way is dark.",
        "Proverbs 3:5",
        "Trust in the LORD with all thine heart; and lean not unto thine own understanding.",
    ),
    (
        "joy",
        "Joy",
        "The gladness that is not built on circumstances — joy in the Lord, and "
        "the joy set before us.",
        "Nehemiah 8:10",
        "The joy of the LORD is your strength.",
    ),
    (
        "hope",
        "Hope",
        "The anchor of the soul — hope that does not disappoint, and looks beyond "
        "the grave.",
        "Hebrews 6:19",
        "Which hope we have as an anchor of the soul, both sure and stedfast.",
    ),
    (
        "peace",
        "Peace",
        "Peace with God, and the peace of God — the quiet mind stayed on him.",
        "Isaiah 26:3",
        "Thou wilt keep him in perfect peace, whose mind is stayed on thee.",
    ),
    (
        "repentance",
        "Repentance",
        "The turning of the heart from sin to God — godly sorrow, and the "
        "contrite spirit he will not despise.",
        "Psalm 51:17",
        "A broken and a contrite heart, O God, thou wilt not despise.",
    ),
    (
        "scripture",
        "The Word of God",
        "The Bible as lamp and food — reading, loving and living by the Word.",
        "Psalm 119:105",
        "Thy word is a lamp unto my feet, and a light unto my path.",
    ),
    (
        "salvation",
        "Salvation & the Gospel",
        "The good news of Christ crucified and risen — saved by grace through "
        "faith, the gift of God.",
        "Ephesians 2:8",
        "For by grace are ye saved through faith; and that not of yourselves: it is "
        "the gift of God.",
    ),
    (
        "heaven",
        "Heaven & Eternity",
        "The hope of glory — the Father's house, the life to come, and living in "
        "view of eternity.",
        "John 14:2",
        "In my Father's house are many mansions: … I go to prepare a place for you.",
    ),
    (
        "surrender",
        "Surrender & Obedience",
        "The consecrated life — presenting ourselves to God, and following where "
        "he leads.",
        "Romans 12:1",
        "I beseech you therefore, brethren, … that ye present your bodies a living sacrifice.",
    ),
    (
        "sin-and-temptation",
        "Sin & Temptation",
        "Honest words on the sin that entangles, and the God who is faithful in "
        "the hour of temptation.",
        "1 Corinthians 10:13",
        "There hath no temptation taken you but such as is common to man: but God is faithful.",
    ),
    (
        "contentment",
        "Contentment",
        "The rare and learned art of being content — godliness with contentment "
        "is great gain.",
        "Philippians 4:11",
        "I have learned, in whatsoever state I am, therewith to be content.",
    ),
]

#: The slug set, for validation (a tag must name a topic that exists here).
QUOTE_TOPIC_SLUGS = frozenset(slug for slug, *_ in QUOTE_TOPICS)

#: (author slug, quotations). Source is a ("book-slug", chapter_order) pair or a
#: sermon slug — exactly one of the two.
SPURGEON = [
    {
        "slug": "charles-h-spurgeon-8b8e88db",
        "text": "We are not going to talk about law, and duty, and punishment, but about love, and goodness, and forgiveness, and mercy, and eternal life.",
        "chapter": ("all-of-grace", 2),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-2f75a3c1",
        "text": "Jesus Christ himself came not to call the righteous, and I am not going to do what He did not do.",
        "chapter": ("all-of-grace", 3),
        "paragraph": 11,
    },
    {
        "slug": "charles-h-spurgeon-bda51fda",
        "text": "Our Lord Jesus did not die for imaginary sins, but His heart's blood was spilt to wash out deep crimson stains, which nothing else can remove.",
        "chapter": ("all-of-grace", 3),
        "paragraph": 15,
    },
    {
        "slug": "charles-h-spurgeon-af63b79e",
        "text": "Jesus Christ, made sin for me, was what I saw, and that sight gave me rest.",
        "chapter": ("all-of-grace", 4),
        "paragraph": 17,
    },
    {
        "slug": "charles-h-spurgeon-1fe6c2ed",
        "text": "The Lord cannot read our pardon written in the blood of His own Son, and then smite us.",
        "chapter": ("all-of-grace", 5),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-94833965",
        "text": "The righteousness of faith is not the moral excellence of faith, but the righteousness of Jesus Christ which faith grasps and appropriates.",
        "chapter": ("all-of-grace", 7),
        "paragraph": 5,
    },
    {
        "slug": "charles-h-spurgeon-91fc01a4",
        "text": "The Lord's salvation can come to us though we have only faith as a grain of mustard seed.",
        "chapter": ("all-of-grace", 7),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-cb3665e4",
        "text": "Jesus Christ is to them a Saviour strong and mighty, a Rock immovable and immutable; they cling to him for dear life, and this clinging saves them.",
        "chapter": ("all-of-grace", 9),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-a4fd540c",
        "text": "Faith which refuses to obey the commands of the Saviour is a mere pretence, and will never save the soul.",
        "chapter": ("all-of-grace", 9),
        "paragraph": 14,
    },
    {
        "slug": "charles-h-spurgeon-e60e0d86",
        "text": "You need not, therefore, despair: that which is necessary to salvation is not continuous thought, but a simple reliance upon Jesus.",
        "chapter": ("all-of-grace", 11),
        "paragraph": 7,
    },
    {
        "slug": "charles-h-spurgeon-76d1edd6",
        "text": "Jesus did not die for our righteousness, but He died for our sins.",
        "chapter": ("all-of-grace", 11),
        "paragraph": 8,
    },
    {
        "slug": "charles-h-spurgeon-e83563c7",
        "text": "Jesus has nothing which He will not use for a sinner's salvation, and He is nothing which He will not display in the aboundings of His grace.",
        "chapter": ("all-of-grace", 14),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-5096795d",
        "text": "Faith is as much the gift of God as is the Saviour upon whom that faith relies.",
        "chapter": ("all-of-grace", 15),
        "paragraph": 15,
    },
    {
        "slug": "charles-h-spurgeon-ddf56c92",
        "text": "Jesus is exalted on high, that through the virtue of His intercession repentance may have a place before God.",
        "chapter": ("all-of-grace", 16),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-116882b5",
        "text": "The Lord's mercy often rides to the door of our hearts on the black horse of affliction.",
        "chapter": ("all-of-grace", 16),
        "paragraph": 3,
    },
    {
        "slug": "charles-h-spurgeon-5bc6762f",
        "text": "The Lord is able, not only to save us from hell, but to keep us from falling.",
        "chapter": ("all-of-grace", 18),
        "paragraph": 4,
    },
    {
        "slug": "charles-h-spurgeon-1f40aadf",
        "text": "Christ and the believing sinner are in the same boat: unless Jesus sinks, the believer will never drown.",
        "chapter": ("all-of-grace", 19),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-d22c535f",
        "text": "Our awakenings are not to help the Saviour, but to help us to the Saviour.",
        "chapter": ("around-the-wicket-gate", 1),
        "paragraph": 2,
    },
    {
        "slug": "charles-h-spurgeon-499c8b72",
        "text": "Salvation is not by our knowing our own ruin, but by fully grasping the deliverance provided in Christ Jesus.",
        "chapter": ("around-the-wicket-gate", 1),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-3b972466",
        "text": "Faith saves us because it makes us cling to Christ Jesus, and he is one with God, and thus brings us into connection with God.",
        "chapter": ("around-the-wicket-gate", 2),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-38eab6a5",
        "text": "Trust Christ, and by that trust you grasp salvation and eternal life.",
        "chapter": ("around-the-wicket-gate", 4),
        "paragraph": 8,
    },
    {
        "slug": "charles-h-spurgeon-f7378bd5",
        "text": "Come by faith to Jesus, for without him you perish for ever.",
        "chapter": ("around-the-wicket-gate", 5),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-158e253e",
        "text": "Faith is the linen which binds the plaster of Christ's reconciliation to the sore of our sin.",
        "chapter": ("around-the-wicket-gate", 7),
        "paragraph": 5,
    },
    {
        "slug": "charles-h-spurgeon-74197e8f",
        "text": "The Lord Jesus has come to save us from sinning; and if we are resolved to go on sinning, Christ and our souls will never agree.",
        "chapter": ("around-the-wicket-gate", 8),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-b0f71ee3",
        "text": "Come to Jesus, by quitting every other hope, by thinking of Him, believing God's testimony about Him, and trusting everything with Him.",
        "chapter": ("cheque-book", 2),
        "paragraph": 74,
    },
    {
        "slug": "charles-h-spurgeon-c918a184",
        "text": "The Lord may not give gold, but He will give grace: He may not give gain, but He will give grace.",
        "chapter": ("cheque-book", 4),
        "paragraph": 107,
    },
    {
        "slug": "charles-h-spurgeon-c3d3a367",
        "text": "Let us be humble that we may not need to be humbled, but may be exalted by the grace of God.",
        "chapter": ("cheque-book", 4),
        "paragraph": 125,
    },
    {
        "slug": "charles-h-spurgeon-cd259808",
        "text": "Our faithful God will never run back from His word, nor will He leave it unfulfilled; yet He loves to be enquired of by His people, and put in mind of His promise.",
        "chapter": ("cheque-book", 6),
        "paragraph": 150,
    },
    {
        "slug": "charles-h-spurgeon-2734034c",
        "text": "We view our God no more as Baal, our tyrant lord and mighty master, for we are not under law, but under grace.",
        "chapter": ("cheque-book", 8),
        "paragraph": 147,
    },
    {
        "slug": "charles-h-spurgeon-cb6b8059",
        "text": "Not for confession, nor for reformation, but in connection with them we find pardon by faith in the blood of Jesus.",
        "chapter": ("cheque-book", 9),
        "paragraph": 88,
    },
    {
        "slug": "charles-h-spurgeon-a2c17461",
        "text": "God does not break the lock, but He opens it by a master-key which He alone can handle.",
        "chapter": ("cheque-book", 10),
        "paragraph": 118,
    },
    {
        "slug": "charles-h-spurgeon-c1353dff",
        "text": "The Holy Ghost Himself cannot better glorify the Lord Jesus than by showing to us Christ's own things.",
        "chapter": ("cheque-book", 10),
        "paragraph": 167,
    },
    {
        "slug": "charles-h-spurgeon-1c6a10ba",
        "text": "Come, my heart, be thou no more sick and sorry, Jesus bids thee be strong, and walk with God in holy contemplation.",
        "chapter": ("cheque-book", 11),
        "paragraph": 65,
    },
    {
        "slug": "charles-h-spurgeon-68366e72",
        "text": "Come, my soul, pluck up courage, and put down thy feet in the blood-marked footprints which thy Lord has left thee.",
        "chapter": ("cheque-book", 13),
        "paragraph": 45,
    },
    {
        "slug": "charles-h-spurgeon-63de5d24",
        "text": "Trust not thyself nor any born of woman, beyond due bounds; but trust thou only and wholly in the Lord.",
        "chapter": ("cheque-book", 13),
        "paragraph": 155,
    },
    {
        "slug": "charles-h-spurgeon-96d23369",
        "text": "God will not lead you into temptation, but you may lead yourself.",
        "chapter": ("talks-to-the-farmer", 2),
        "paragraph": 47,
    },
    {
        "slug": "charles-h-spurgeon-c464d76e",
        "text": "Our duty is not determined by the character of our hearers but by the command of our God.",
        "chapter": ("talks-to-the-farmer", 7),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-3eea1a98",
        "text": "Believe in the Lord Jesus Christ, and you, even you, will be saved.",
        "chapter": ("talks-to-the-farmer", 7),
        "paragraph": 54,
    },
    {
        "slug": "charles-h-spurgeon-0886b0fe",
        "text": "Jesus Christ is the bread by which our soul’s best life is sustained.",
        "chapter": ("talks-to-the-farmer", 8),
        "paragraph": 3,
    },
    {
        "slug": "charles-h-spurgeon-92fc517e",
        "text": "Whether faith is large or small, whether you can do much or little for Christ, salvation depends not on what you are but on what Jesus Christ is.",
        "chapter": ("talks-to-the-farmer", 9),
        "paragraph": 20,
    },
    {
        "slug": "charles-h-spurgeon-c84751da",
        "text": "Salvation does not come from the preacher’s authority, but through the hearer’s personal conviction, personal faith, and personal love.",
        "chapter": ("talks-to-the-farmer", 11),
        "paragraph": 18,
    },
    {
        "slug": "charles-h-spurgeon-d6d84bd3",
        "text": "Beloved, the Lord’s workers have sauce with their bread: not merely doctrines, but the holy joy that accompanies them.",
        "chapter": ("talks-to-the-farmer", 15),
        "paragraph": 42,
    },
    {
        "slug": "charles-h-spurgeon-b8b46bcf",
        "text": "Not only does God bear with sin, but in the person of his Son, he bore and removed it.",
        "chapter": ("talks-to-the-farmer", 16),
        "paragraph": 40,
    },
    {
        "slug": "charles-h-spurgeon-3f56a9f6",
        "text": "The Lord Jesus was unto us a covering for sin, and so a covert from wrath.",
        "chapter": ("till-he-come", 3),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-ca2d8572",
        "text": "Look on the drops of grace, and remember that they distil from the Head, Christ Jesus.",
        "chapter": ("till-he-come", 8),
        "paragraph": 45,
    },
    {
        "slug": "charles-h-spurgeon-d0fcbb43",
        "text": "Christ Jesus is the only escape for a sinner pursued by the fiery wrath of God, and we would have the believer remember this.",
        "chapter": ("till-he-come", 8),
        "paragraph": 51,
    },
    {
        "slug": "charles-h-spurgeon-52ff0174",
        "text": "Jesus identified Himself with His people, and therefore their sin was laid upon Him, and the sword of the Lord awoke against Him.",
        "chapter": ("till-he-come", 10),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-72801c84",
        "text": "O soul, seek not a settlement by learning of men; but come and learn of Jesus, and thou shalt find rest!",
        "chapter": ("till-he-come", 13),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-b11a33f8",
        "text": "Come utterly ruined and undone, for in Jesus Christ there is the strength and salvation which thy case requires.",
        "chapter": ("till-he-come", 16),
        "paragraph": 14,
    },
    {
        "slug": "charles-h-spurgeon-a11d6733",
        "text": "Christ’s word of grace is very near you, it is on your tongue; let it go down into your inmost soul.",
        "chapter": ("till-he-come", 20),
        "paragraph": 32,
    },
    {
        "slug": "charles-h-spurgeon-f5498610",
        "text": "Our Lord Jesus did not handle sin with the golden tongs, but He bore it on His own shoulders.",
        "chapter": ("till-he-come", 21),
        "paragraph": 21,
    },
    {
        "slug": "charles-h-spurgeon-49c2e393",
        "text": "Ah! what a mercy it is that it is not your hold of Christ that saves you, but his hold of you!",
        "sermon": "christ-crucified",
        "paragraph": 43,
    },
    {
        "slug": "charles-h-spurgeon-99faf780",
        "text": "Pardon is a good thing—who will not say so?—ay, but we are pardoned through the precious blood of Jesus.",
        "sermon": "christ-precious-to-believers",
        "paragraph": 14,
    },
    {
        "slug": "charles-h-spurgeon-bb0e39fc",
        "text": "To be preserved—is not that a precious thing?—ay; but we are preserved in Christ Jesus, and kept by his power even to the end.",
        "sermon": "christ-precious-to-believers",
        "paragraph": 14,
    },
    {
        "slug": "charles-h-spurgeon-c3773b2e",
        "text": "Our first business has not to do with faith, but with Christ.",
        "sermon": "compel-them-to-come-in",
        "paragraph": 27,
    },
    {
        "slug": "charles-h-spurgeon-99ebcd5e",
        "text": "God has given to his servants not the power of regeneration, but he has given them something akin to it.",
        "sermon": "compel-them-to-come-in",
        "paragraph": 30,
    },
    {
        "slug": "charles-h-spurgeon-e96bbdf6",
        "text": "God give us to be much in the holy art of arguing with God in prayer.",
        "sermon": "order-and-argument-in-prayer",
        "paragraph": 15,
    },
    {
        "slug": "charles-h-spurgeon-813295f9",
        "text": "The Lord give you large mouths in prayer, great potency, not in the use of language, but in employing arguments.",
        "sermon": "order-and-argument-in-prayer",
        "paragraph": 26,
    },
    {
        "slug": "charles-h-spurgeon-22f0858c",
        "text": "One prayer coming from the soul is better than a myriad cold readings.",
        "sermon": "pauls-first-prayer",
        "paragraph": 15,
    },
    {
        "slug": "charles-h-spurgeon-f259f382",
        "text": "God’s Spirit is teaching you how to wrestle and agonize in prayer.",
        "sermon": "the-sweet-uses-of-adversity",
        "paragraph": 20,
    },
    {
        "slug": "charles-h-spurgeon-7faf8f59",
        "text": "Christ in the heart, means Christ believed in, Christ beloved, Christ trusted, Christ espoused, Christ communed with, Christ as our daily food, and ourselves as the temple and palace wherein Jesus Christ daily walks.",
        "chapter": ("gleanings-among-the-sheaves", 12),
        "paragraph": 7,
    },
    {
        "slug": "charles-h-spurgeon-3abc20c9",
        "text": "Let a man truly know the grace of our Lord Jesus Christ, and he will be a happy man; and the deeper he drinks into the Spirit of Christ, the happier will he become.",
        "chapter": ("gleanings-among-the-sheaves", 10),
        "paragraph": 7,
    },
    {
        "slug": "charles-h-spurgeon-d59a45ab",
        "text": "There never yet was a heavenly thought, a hallowed deed, or a consecrated act, acceptable to God by Jesus Christ, which was not worked in us by the Holy Spirit.",
        "chapter": ("gleanings-among-the-sheaves", 19),
        "paragraph": 3,
    },
    {
        "slug": "charles-h-spurgeon-cfdd6903",
        "text": "The love of Christ casts not out the love of relatives, but it sanctifies our creature love, and makes it sweeter far.",
        "chapter": ("gleanings-among-the-sheaves", 7),
        "paragraph": 14,
    },
    {
        "slug": "charles-h-spurgeon-ab484f68",
        "text": "Little faith will get very great mercies, but great faith still greater.",
        "chapter": ("gleanings-among-the-sheaves", 11),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-36a701d9",
        "text": "Faith was Peter's life-buoy—it kept him up; but unbelief sent him down.",
        "chapter": ("gleanings-among-the-sheaves", 2),
        "paragraph": 2,
    },
    {
        "slug": "charles-h-spurgeon-5fcb15f8",
        "text": "The gospel is not a scheme of giving to God, but of receiving from God.",
        "chapter": ("gleanings-among-the-sheaves", 8),
        "paragraph": 13,
    },
    {
        "slug": "charles-h-spurgeon-4389b884",
        "text": "He who delights in the possession of the Lord Jesus hath all that heart can wish.",
        "chapter": ("gleanings-among-the-sheaves", 6),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-2daf7b58",
        "text": "You will never perceive God in nature, until you have learned to see God in grace.",
        "chapter": ("gleanings-among-the-sheaves", 12),
        "paragraph": 15,
    },
    {
        "slug": "charles-h-spurgeon-f28139b1",
        "text": "Believers are not only to be with Christ, and to behold His glory, but they are to be like Christ, and to be glorified with Him.",
        "chapter": ("gleanings-among-the-sheaves", 16),
        "paragraph": 13,
    },
    {
        "slug": "charles-h-spurgeon-870f2640",
        "text": "It is ours to ask for a blessing, but not to define what the blessing shall be.",
        "chapter": ("gleanings-among-the-sheaves", 11),
        "paragraph": 10,
    },
    {
        "slug": "charles-h-spurgeon-57735f38",
        "text": "We are saved by faith, and not by feeling; yet there is a relation between holy faith and hallowed feeling like that between the root and the flower.",
        "chapter": ("gleanings-among-the-sheaves", 2),
        "paragraph": 10,
    },
    {
        "slug": "charles-h-spurgeon-0c53a2aa",
        "text": "As the Lord hath but one family, written in one register, redeemed with one blood, quickened by one Spirit, so this whole household abides in one habitation evermore.",
        "chapter": ("gleanings-among-the-sheaves", 20),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-d25d6079",
        "text": "Grace is always grace, but it never seems so gracious as when we see it brought to our unworthy selves.",
        "chapter": ("gleanings-among-the-sheaves", 8),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-f0f5f775",
        "text": "The Christian's life is one of daily dependence on the grace and strength of God.",
        "chapter": ("gleanings-among-the-sheaves", 5),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-8e8ecc65",
        "text": "It is the distinguishing mark of God's people that they know the love of Christ.",
        "chapter": ("gleanings-among-the-sheaves", 7),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-4b7afe02",
        "text": "The prayer that this morning you offered, Christ is now offering before His Father's throne.",
        "chapter": ("gleanings-among-the-sheaves", 9),
        "paragraph": 5,
    },
    {
        "slug": "charles-h-spurgeon-f87efc94",
        "text": "We are not trees by ourselves, but we are branches fixed on the Living Vine.",
        "chapter": ("gleanings-among-the-sheaves", 18),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-18e34bba",
        "text": "There are some sciences that may be learned by the head, but the science of Christ crucified can only be learned by the heart.",
        "chapter": ("gleanings-among-the-sheaves", 17),
        "paragraph": 5,
    },
    {
        "slug": "charles-h-spurgeon-010273ba",
        "text": "Unless the heart be kept peaceable, the life will not be happy.",
        "chapter": ("gleanings-among-the-sheaves", 15),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-31ec3990",
        "text": "God's people are often chastened, and the Lord's hand lieth heavy upon them; yet there is paternal goodness in their chastenings, and infinite lovingkindness in their tribulations.",
        "chapter": ("gleanings-among-the-sheaves", 3),
        "paragraph": 26,
    },
    {
        "slug": "charles-h-spurgeon-f34cdb2a",
        "text": "Though they know a little about Christ on Calvary, they know nothing about Christ in the heart.",
        "chapter": ("gleanings-among-the-sheaves", 12),
        "paragraph": 7,
    },
    {
        "slug": "charles-h-spurgeon-c3eec6ac",
        "text": "Let us ever remember that Christ on the cross is of no value to us apart from the Holy Spirit in us.",
        "chapter": ("gleanings-among-the-sheaves", 19),
        "paragraph": 3,
    },
    {
        "slug": "charles-h-spurgeon-f90f1753",
        "text": "Little-faith was bought with the blood of Christ; ay, and he cost as much as Great-faith.",
        "chapter": ("gleanings-among-the-sheaves", 2),
        "paragraph": 14,
    },
    {
        "slug": "charles-h-spurgeon-756e08e3",
        "text": "Not one sin is to be spared, but against the whole is to be proclaimed an utter and entire war of extermination.",
        "chapter": ("gleanings-among-the-sheaves", 4),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-2c1ff73f",
        "text": "Seek that you may keep your conversation always holy; that your course may be like the shining light which tarries not, but burns brighter and brighter until the fulness of the day.",
        "chapter": ("gleanings-among-the-sheaves", 4),
        "paragraph": 12,
    },
    {
        "slug": "charles-h-spurgeon-49d53581",
        "text": "Do you think that we are forever to be the drudges and the slaves of sin, sighing for freedom, and yet never able to escape from its bondage?",
        "chapter": ("gleanings-among-the-sheaves", 4),
        "paragraph": 16,
    },
    {
        "slug": "charles-h-spurgeon-e48554af",
        "text": "If we have grown in grace, it is absolutely certain that we shall have advanced in our knowledge and reciprocation of the love of Christ.",
        "chapter": ("gleanings-among-the-sheaves", 7),
        "paragraph": 4,
    },
    {
        "slug": "charles-h-spurgeon-4bdec927",
        "text": "Our court-dress in heaven, and our garment of sanctification for daily wear, are the condescending gifts of Christ's love.",
        "chapter": ("gleanings-among-the-sheaves", 8),
        "paragraph": 3,
    },
    {
        "slug": "charles-h-spurgeon-d1598ff5",
        "text": "Not only must the heart be kept pure, but it must also be kept full.",
        "chapter": ("gleanings-among-the-sheaves", 10),
        "paragraph": 4,
    },
    {
        "slug": "charles-h-spurgeon-242c0cc9",
        "text": "Christ, when He blesses, blesses not in word only, but in deed.",
        "chapter": ("gleanings-among-the-sheaves", 10),
        "paragraph": 17,
    },
    {
        "slug": "charles-h-spurgeon-825c2f8b",
        "text": "How careful God is of His people; how anxious He is concerning them, not only for their life, but for their comfort.",
        "chapter": ("gleanings-among-the-sheaves", 14),
        "paragraph": 11,
    },
    {
        "slug": "charles-h-spurgeon-c96dd1a1",
        "text": "The believer enjoys, in favored seasons, such an intimacy with the Lord Jesus, as fills his heart with an overflowing peace.",
        "chapter": ("gleanings-among-the-sheaves", 15),
        "paragraph": 3,
    },
    {
        "slug": "charles-h-spurgeon-1b7df6d3",
        "text": "If thou wouldst find thy way to God's bright throne, find first thy way to Jesus' cross; if thou wouldst know the way to happiness, tread in that path of misery which Jesus trod.",
        "chapter": ("gleanings-among-the-sheaves", 16),
        "paragraph": 11,
    },
    {
        "slug": "charles-h-spurgeon-14b10a83",
        "text": "You may read the Bible continuously, and yet never learn anything by it, unless it is illuminated by the Spirit; and then the words shine forth like stars.",
        "chapter": ("gleanings-among-the-sheaves", 17),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-62f2db13",
        "text": "Your business is to seek Christ crucified for yourselves, not to take the representation of another man concerning the power of grace to subdue corruption and to sanctify the heart.",
        "chapter": ("gleanings-among-the-sheaves", 12),
        "paragraph": 1,
    },
    {
        "slug": "charles-h-spurgeon-0a553264",
        "text": "The Lord Jesus has led captivity captive, and now sits at the right hand of God, forever making intercession for us.",
        "chapter": ("gleanings-among-the-sheaves", 9),
        "paragraph": 5,
    },
]

THOMAS_A_KEMPIS = [
    {
        "slug": "thomas-a-kempis-d0edf151",
        "text": "God does well in giving the grace of consolation, but man does evil in not returning everything gratefully to God.",
        "chapter": ("the-imitation-of-christ", 36),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-aa58e7e7",
        "text": "Nothing is more acceptable to God, nothing more helpful for you on this earth than to suffer willingly for Christ.",
        "chapter": ("the-imitation-of-christ", 38),
        "paragraph": 18,
    },
    {
        "slug": "thomas-a-kempis-65308598",
        "text": "Love is never self-seeking, for in whatever a person seeks himself there he falls from love.",
        "chapter": ("the-imitation-of-christ", 43),
        "paragraph": 9,
    },
    {
        "slug": "thomas-a-kempis-da0dc871",
        "text": "The pure, simple, and steadfast spirit is not distracted by many labors, for he does them all for the honor of God.",
        "chapter": ("the-imitation-of-christ", 4),
        "paragraph": 5,
    },
    {
        "slug": "thomas-a-kempis-7b8c9527",
        "text": "Nothing so mars and defiles the heart of man as impure attachment to created things.",
        "chapter": ("the-imitation-of-christ", 27),
        "paragraph": 14,
    },
    {
        "slug": "thomas-a-kempis-8a6df7db",
        "text": "God alone, the eternal and infinite, satisfies all, bringing comfort to the soul and true joy to the body.",
        "chapter": ("the-imitation-of-christ", 31),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-90b0ce53",
        "text": "The man who lives without Jesus is the poorest of the poor, whereas no one is so rich as the man who lives in His grace.",
        "chapter": ("the-imitation-of-christ", 34),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-553acf8a",
        "text": "Let all things be loved for the sake of Jesus, but Jesus for His own sake.",
        "chapter": ("the-imitation-of-christ", 34),
        "paragraph": 4,
    },
    {
        "slug": "thomas-a-kempis-3f91c46d",
        "text": "A man must fight long and bravely against himself before he learns to master himself fully and to direct all his affections toward God.",
        "chapter": ("the-imitation-of-christ", 35),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-7acdee79",
        "text": "Love tends upward; it will not be held down by anything low.",
        "chapter": ("the-imitation-of-christ", 43),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-4a380367",
        "text": "Let me love You more than myself, and let me not love myself except for Your sake.",
        "chapter": ("the-imitation-of-christ", 43),
        "paragraph": 8,
    },
    {
        "slug": "thomas-a-kempis-be6f13f2",
        "text": "The wise lover regards not so much the gift of Him Who loves as the love of Him Who gives.",
        "chapter": ("the-imitation-of-christ", 44),
        "paragraph": 6,
    },
    {
        "slug": "thomas-a-kempis-9c75ee06",
        "text": "Man draws nearer to God in proportion as he withdraws farther from all earthly comfort.",
        "chapter": ("the-imitation-of-christ", 80),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-9a6d1484",
        "text": "Grace does not consider what is useful and advantageous to herself, but rather what is profitable to many.",
        "chapter": ("the-imitation-of-christ", 92),
        "paragraph": 4,
    },
    {
        "slug": "thomas-a-kempis-75fd349d",
        "text": "Grace brings all things back to God in Whom they have their source.",
        "chapter": ("the-imitation-of-christ", 92),
        "paragraph": 12,
    },
    {
        "slug": "thomas-a-kempis-62c7429e",
        "text": "To trust in You above all things is the strongest comfort of Your servants.",
        "chapter": ("the-imitation-of-christ", 97),
        "paragraph": 4,
    },
    {
        "slug": "thomas-a-kempis-b2579c20",
        "text": "Faith is required of you, and a sincere life, not a lofty intellect nor a delving into the mysteries of God.",
        "chapter": ("the-imitation-of-christ", 115),
        "paragraph": 4,
    },
    {
        "slug": "thomas-a-kempis-543d5a45",
        "text": "The man who casts aside the fear of God cannot continue long in goodness but will quickly fall into the snares of the devil.",
        "chapter": ("the-imitation-of-christ", 25),
        "paragraph": 13,
    },
    {
        "slug": "thomas-a-kempis-4aef1a9f",
        "text": "To glory in adversity is not hard for the man who loves, for this is to glory in the cross of the Lord.",
        "chapter": ("the-imitation-of-christ", 32),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-dc7909dc",
        "text": "Grace is always given to him who is duly grateful, and what is wont to be given the humble will be taken away from the proud.",
        "chapter": ("the-imitation-of-christ", 36),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-73cdb0bb",
        "text": "No one understands the passion of Christ so thoroughly or heartily as the man whose lot it is to suffer the like himself.",
        "chapter": ("the-imitation-of-christ", 38),
        "paragraph": 4,
    },
    {
        "slug": "thomas-a-kempis-35828f2d",
        "text": "No man is fit to enjoy heaven unless he has resigned himself to suffer hardship for Christ.",
        "chapter": ("the-imitation-of-christ", 38),
        "paragraph": 18,
    },
    {
        "slug": "thomas-a-kempis-3462f9c8",
        "text": "The teaching of Christ is more excellent than all the advice of the saints, and he who has His spirit will find in it a hidden manna.",
        "chapter": ("the-imitation-of-christ", 2),
        "paragraph": 1,
    },
    {
        "slug": "thomas-a-kempis-8ea5438f",
        "text": "The humble live in continuous peace, while in the hearts of the proud are envy and frequent anger.",
        "chapter": ("the-imitation-of-christ", 8),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-c2ab9d85",
        "text": "No man is safe in speaking unless he loves to be silent.",
        "chapter": ("the-imitation-of-christ", 21),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-23ece4d7",
        "text": "No man commands safely unless he has learned well how to obey.",
        "chapter": ("the-imitation-of-christ", 21),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-6ff5eb6f",
        "text": "No man deserves the consolation of heaven unless he persistently arouses himself to holy contrition.",
        "chapter": ("the-imitation-of-christ", 21),
        "paragraph": 6,
    },
    {
        "slug": "thomas-a-kempis-e5643ba2",
        "text": "The present is very precious; these are the days of salvation; now is the acceptable time.",
        "chapter": ("the-imitation-of-christ", 24),
        "paragraph": 7,
    },
    {
        "slug": "thomas-a-kempis-69ad2257",
        "text": "Place all your trust in God; let Him be your fear and your love.",
        "chapter": ("the-imitation-of-christ", 27),
        "paragraph": 5,
    },
    {
        "slug": "thomas-a-kempis-4df3c1a3",
        "text": "Consider nothing great, nothing high, nothing pleasing, nothing acceptable, except God Himself or that which is of God.",
        "chapter": ("the-imitation-of-christ", 31),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-4db2ea01",
        "text": "Every day the interior man is reformed by new visitations according to the image of God.",
        "chapter": ("the-imitation-of-christ", 92),
        "paragraph": 15,
    },
    {
        "slug": "thomas-a-kempis-1e51f540",
        "text": "The man who is at perfect ease is never suspicious, but the disturbed and discontented spirit is upset by many a suspicion.",
        "chapter": ("the-imitation-of-christ", 29),
        "paragraph": 1,
    },
    {
        "slug": "thomas-a-kempis-8ce859d9",
        "text": "Let the eternal truth please you above all things, and let your extreme unworthiness always displease you.",
        "chapter": ("the-imitation-of-christ", 42),
        "paragraph": 5,
    },
    {
        "slug": "thomas-a-kempis-574029fa",
        "text": "The one often errs, the other trusts in God and is not deceived.",
        "chapter": ("the-imitation-of-christ", 69),
        "paragraph": 8,
    },
    {
        "slug": "thomas-a-kempis-7ab2c082",
        "text": "Christ will come to you offering His consolation, if you prepare a fit dwelling for Him in your heart, whose beauty and glory, wherein He takes delight, are all from within.",
        "chapter": ("the-imitation-of-christ", 27),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-8e7b6b00",
        "text": "Jesus Christ must be loved alone with a special love for He alone, of all friends, is good and faithful.",
        "chapter": ("the-imitation-of-christ", 34),
        "paragraph": 5,
    },
    {
        "slug": "thomas-a-kempis-9de70a18",
        "text": "Whatever is not God is nothing and must be accounted as nothing.",
        "chapter": ("the-imitation-of-christ", 69),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-85bd98b1",
        "text": "Seek true peace, not on earth but in heaven; not in men or in other creatures but in God alone.",
        "chapter": ("the-imitation-of-christ", 73),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-6f280cbb",
        "text": "Affection for creatures is deceitful and inconstant, but the love of Jesus is true and enduring.",
        "chapter": ("the-imitation-of-christ", 33),
        "paragraph": 1,
    },
    {
        "slug": "thomas-a-kempis-043d2543",
        "text": "No man rejoices safely unless he has within him the testimony of a good conscience.",
        "chapter": ("the-imitation-of-christ", 21),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-32dc0a68",
        "text": "Man’s happiness does not consist in the possession of abundant goods; a very little is enough.",
        "chapter": ("the-imitation-of-christ", 23),
        "paragraph": 1,
    },
    {
        "slug": "thomas-a-kempis-77d5e620",
        "text": "A man’s true progress consists in denying himself, and the man who has denied himself is truly free and secure.",
        "chapter": ("the-imitation-of-christ", 77),
        "paragraph": 6,
    },
    {
        "slug": "thomas-a-kempis-21a0bdf5",
        "text": "One who is in love flies, runs, and rejoices; he is free, not bound.",
        "chapter": ("the-imitation-of-christ", 43),
        "paragraph": 5,
    },
    {
        "slug": "thomas-a-kempis-1383b3ad",
        "text": "All men desire peace but all do not care for the things that go to make true peace.",
        "chapter": ("the-imitation-of-christ", 63),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-ce999abc",
        "text": "Many words do not satisfy the soul; but a good life eases the mind and a clean conscience inspires great trust in God.",
        "chapter": ("the-imitation-of-christ", 3),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-c07353e9",
        "text": "Do not think yourself better than others lest, perhaps, you be accounted worse before God Who knows what is in man.",
        "chapter": ("the-imitation-of-christ", 8),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-e72afb6e",
        "text": "To walk with God interiorly, to be free from any external affection—this is the state of the inward man.",
        "chapter": ("the-imitation-of-christ", 32),
        "paragraph": 8,
    },
    {
        "slug": "thomas-a-kempis-79341ddc",
        "text": "The whole world will not make him proud whom truth has subjected to itself.",
        "chapter": ("the-imitation-of-christ", 52),
        "paragraph": 5,
    },
    {
        "slug": "thomas-a-kempis-47fd3784",
        "text": "Happy is the man who can throw off the weight of every care and recollect himself in holy contrition.",
        "chapter": ("the-imitation-of-christ", 22),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-bd12b144",
        "text": "A spiritual man quickly recollects himself because he has never wasted his attention upon externals.",
        "chapter": ("the-imitation-of-christ", 27),
        "paragraph": 13,
    },
    {
        "slug": "thomas-a-kempis-f4303a94",
        "text": "Just men depend on the grace of God rather than on their own wisdom in keeping their resolutions.",
        "chapter": ("the-imitation-of-christ", 20),
        "paragraph": 3,
    },
    {
        "slug": "thomas-a-kempis-72fe1814",
        "text": "Not every desire is from the Holy Spirit, even though it may seem right and good.",
        "chapter": ("the-imitation-of-christ", 53),
        "paragraph": 2,
    },
    {
        "slug": "thomas-a-kempis-a34c6521",
        "text": "True peace of heart, then, is found in resisting passions, not in satisfying them.",
        "chapter": ("the-imitation-of-christ", 7),
        "paragraph": 1,
    },
    {
        "slug": "thomas-a-kempis-5e7c6a28",
        "text": "Humble knowledge of self is a surer path to God than the ardent pursuit of learning.",
        "chapter": ("the-imitation-of-christ", 4),
        "paragraph": 7,
    },
]

ANDREW_MURRAY = [
    {
        "slug": "andrew-murray-544f0576",
        "text": "Pride and self are all of man, till man has all from Christ.",
        "chapter": ("humility-2", 2),
        "paragraph": 18,
    },
    {
        "slug": "andrew-murray-d02a0de2",
        "text": "Faith seeks the glory that comes from God, and it only comes where God is all.",
        "chapter": ("humility-2", 9),
        "paragraph": 3,
    },
    {
        "slug": "andrew-murray-723db96f",
        "text": "Nothing but this fellowship can satisfy the heart of either man or God.",
        "chapter": ("the-inner-chamber", 2),
        "paragraph": 3,
    },
    {
        "slug": "andrew-murray-1b021ab8",
        "text": "Every believer has the right and calling, to stand in direct communication with God.",
        "chapter": ("the-inner-chamber", 20),
        "paragraph": 2,
    },
    {
        "slug": "andrew-murray-b4a4d4f8",
        "text": "God only asks of us to yield, to consent, to wait upon Him, and He will do it all.",
        "chapter": ("waiting-on-god", 4),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-ecbf3f59",
        "text": "God always meets His children where they are, howsoever weak they may be.",
        "chapter": ("divine-healing", 6),
        "paragraph": 2,
    },
    {
        "slug": "andrew-murray-3e731043",
        "text": "The part of faith is always to lay hold on just that which appears impossible or strange to human eyes.",
        "chapter": ("divine-healing", 6),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-32b8b61a",
        "text": "Nothing can be our redemption but the restoration of the lost humility, the original and only true relation of the creature to its God.",
        "chapter": ("humility-2", 1),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-ba743e80",
        "text": "The truth is this, pride may die in you or nothing of heaven can live in you.",
        "chapter": ("humility-2", 1),
        "paragraph": 15,
    },
    {
        "slug": "andrew-murray-307dbdae",
        "text": "Humility before God is nothing if not proved in humility before men.",
        "chapter": ("humility-2", 6),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-40bac55a",
        "text": "Nothing but the presence of God can reveal and expel the self.",
        "chapter": ("humility-2", 11),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-27946bb4",
        "text": "The highest glory of the creature is in being only a vessel, to receive and enjoy and show forth the glory of God.",
        "chapter": ("humility-2", 12),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-87d9f1d8",
        "text": "To know how to speak to God is more than knowing how to speak to man.",
        "chapter": ("lord-teach-us-to-pray-2", 1),
        "paragraph": 13,
    },
    {
        "slug": "andrew-murray-7bc3e383",
        "text": "The knowledge of God's Father love is the first and simplest, but also the last and highest lesson in the school of prayer.",
        "chapter": ("lord-teach-us-to-pray-2", 4),
        "paragraph": 3,
    },
    {
        "slug": "andrew-murray-4e3ad077",
        "text": "Let us beware of the prayer for forgiveness becoming a formality: only what is really confessed is really forgiven.",
        "chapter": ("lord-teach-us-to-pray-2", 4),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-622d4639",
        "text": "The word is nothing if it is not kept, obeyed, or done.",
        "chapter": ("the-inner-chamber", 9),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-03547f54",
        "text": "The only way to know God, to taste His blessedness, is through the doing of His will.",
        "chapter": ("the-inner-chamber", 10),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-bdffda15",
        "text": "Man was to have the joy of receiving every moment out of the fulness of God.",
        "chapter": ("waiting-on-god", 3),
        "paragraph": 3,
    },
    {
        "slug": "andrew-murray-cdf11ae9",
        "text": "The rest, the silence, the stillness, and the patient waiting, all find their strength and joy in God Himself.",
        "chapter": ("waiting-on-god", 13),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-74ee7679",
        "text": "The only means by which this unseen enemy can be conquered is faith.",
        "chapter": ("divine-healing", 15),
        "paragraph": 1,
    },
    {
        "slug": "andrew-murray-2097ba81",
        "text": "Christ longs to reveal Himself, but He cannot on account of our unbelief.",
        "chapter": ("jesus-himself-2", 1),
        "paragraph": 28,
    },
    {
        "slug": "andrew-murray-7c3c7408",
        "text": "The blessing is often superficial or transitory because they do not open the way for God to be all.",
        "chapter": ("humility-2", 9),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-f67288c6",
        "text": "Christ is nowhere but in these virtues; when they are there, He is in His own kingdom.",
        "chapter": ("humility-2", 10),
        "paragraph": 20,
    },
    {
        "slug": "andrew-murray-e8346b82",
        "text": "A man does not get converted without having the conviction of sin.",
        "chapter": ("the-masters-indwelling", 1),
        "paragraph": 31,
    },
    {
        "slug": "andrew-murray-0c0c3156",
        "text": "Every thought of God's Word, instead of drawing him off from God, leads him to fellowship with God.",
        "chapter": ("the-inner-chamber", 30),
        "paragraph": 9,
    },
    {
        "slug": "andrew-murray-ee7711d2",
        "text": "God is a spirit: He is the Everlasting and Unchangeable One; what He is, He is always and in truth.",
        "chapter": ("lord-teach-us-to-pray-2", 2),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-25892082",
        "text": "The effect of the word on the heart is in most cases not immediate.",
        "chapter": ("the-inner-chamber", 8),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-3272b680",
        "text": "Faith in Jesus is the secret of a holy life: all holy conduct, all really holy deeds, are the fruit of faith in Jesus as our holiness.",
        "chapter": ("holy-in-christ", 19),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-6fe1dfa3",
        "text": "As that holy will enters man’s will, as man’s will accepts and unites itself with God’s will, he becomes holy.",
        "chapter": ("holy-in-christ", 8),
        "paragraph": 2,
    },
    {
        "slug": "andrew-murray-7866a702",
        "text": "Let obedience, the listening to and the doing the will of God, be the joy and the glory of your life; it will give you access unto the Holiness of God.",
        "chapter": ("holy-in-christ", 8),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-29a39898",
        "text": "Chastisement is bringing your heart into unity with God’s Will, God’s Son, God’s Love.",
        "chapter": ("holy-in-christ", 30),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-54e28ba2",
        "text": "God is not only holy, but makes holy: in the revelation of the Three Persons we have the revelation of the way in which God makes holy.",
        "chapter": ("holy-in-christ", 13),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-ba80b140",
        "text": "The spirit of separation is the spirit of self-sacrifice, of surrender to the love of God; the truly separate one will be the most loving and love-winning, given up to serve God and man.",
        "chapter": ("holy-in-christ", 11),
        "paragraph": 21,
    },
    {
        "slug": "andrew-murray-77a4141f",
        "text": "It is the New Life that is the holy life: the full apprehension of it in faith, the full surrender to it in conduct, will be the highway of holiness.",
        "chapter": ("holy-in-christ", 20),
        "paragraph": 8,
    },
    {
        "slug": "andrew-murray-71f58011",
        "text": "In the beginning of the faith-life, faith is struggling; but as long as faith is struggling, faith has not attained its strength.",
        "chapter": ("absolute-surrender", 8),
        "paragraph": 59,
    },
    {
        "slug": "andrew-murray-c28b985e",
        "text": "God alone, who gave us the Holy Spirit, can restore the Holy Spirit in power into our life.",
        "chapter": ("absolute-surrender", 7),
        "paragraph": 48,
    },
    {
        "slug": "andrew-murray-3279a07e",
        "text": "The Holy Spirit is the life of the heavenly Vine, and what you must get from Christ is nothing less than a strong inflow of the Holy Spirit.",
        "chapter": ("absolute-surrender", 9),
        "paragraph": 36,
    },
    {
        "slug": "andrew-murray-9222df6d",
        "text": "Let us seek to understand that the life of the branch is a life of much fruit, because it is a life rooted in Christ, the living, heavenly Vine.",
        "chapter": ("absolute-surrender", 9),
        "paragraph": 37,
    },
    {
        "slug": "andrew-murray-c38b33cb",
        "text": "If the love of God is in your heart you will love your brother.",
        "chapter": ("absolute-surrender", 2),
        "paragraph": 45,
    },
    {
        "slug": "andrew-murray-7f00de09",
        "text": "Christ’s life and work, His suffering and death—it was all prayer, all dependence on God, trust in God, receiving from God, surrender to God.",
        "chapter": ("ministry-of-intercession", 13),
        "paragraph": 10,
    },
    {
        "slug": "andrew-murray-ceef792c",
        "text": "It is the life abiding wholly in Christ that can pray the effectual prayer in the name of Christ.",
        "chapter": ("ministry-of-intercession", 7),
        "paragraph": 7,
    },
    {
        "slug": "andrew-murray-be6e77d9",
        "text": "Intercession is the most perfect form of prayer: it is the prayer Christ ever liveth to pray on His throne.",
        "chapter": ("ministry-of-intercession", 5),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-3450b45b",
        "text": "Blessed the man who is not staggered by God’s delay, or silence, or apparent refusal, but is strong in faith, giving glory to God.",
        "chapter": ("ministry-of-intercession", 5),
        "paragraph": 16,
    },
    {
        "slug": "andrew-murray-75191679",
        "text": "Throughout Scripture, in the life of every saint, of God’s own Son, throughout the history of God’s Church, God is, first of all, a prayer-hearing God.",
        "chapter": ("ministry-of-intercession", 2),
        "paragraph": 8,
    },
    {
        "slug": "andrew-murray-13b9ac31",
        "text": "It is the branch-life, existing solely for the Vine, that will have the power to pray aright.",
        "chapter": ("ministry-of-intercession", 7),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-d736c7c7",
        "text": "It was by obedience Christ as Vine honored the Father as Husbandman; it is by obedience the believer as branch honors Christ as Vine.",
        "chapter": ("true-vine", 23),
        "paragraph": 1,
    },
    {
        "slug": "andrew-murray-20077327",
        "text": "It is as our life abides in Christ, as we abide in Him, that the fruit we bear will abide.",
        "chapter": ("true-vine", 31),
        "paragraph": 2,
    },
    {
        "slug": "andrew-murray-def0eaf2",
        "text": "The life of abiding and obedience, of love and joy, of cleansing and fruit-bearing, will surely lead to the power of prevailing prayer.",
        "chapter": ("true-vine", 32),
        "paragraph": 2,
    },
    {
        "slug": "andrew-murray-716ef8a0",
        "text": "To be a branch means not only bearing fruit on earth, but power in prayer to bring down blessing from Heaven.",
        "chapter": ("true-vine", 16),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-53a45df8",
        "text": "Ever stand before God, in Christ; ever wait for all grace from God, in Christ; ever yield yourself to bear the more fruit the Husbandman asks, in Christ.",
        "chapter": ("true-vine", 11),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-f1456932",
        "text": "The child who only wants to know the love of the father when he has something to ask, will be disappointed.",
        "chapter": ("school-of-prayer", 7),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-4fd4375c",
        "text": "The Lord does not demand of us a perfect fulfilment of the law; no, but only the childlike and whole-hearted surrender to live as a child with Him in obedience and truth.",
        "chapter": ("school-of-prayer", 7),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-2f3cd850",
        "text": "The one thing by which man can honour and enjoy his God is faith.",
        "chapter": ("school-of-prayer", 9),
        "paragraph": 7,
    },
    {
        "slug": "andrew-murray-21b2f5b3",
        "text": "Our prayers must not be a vague appeal to His mercy, an indefinite cry for blessing, but the distinct expression of definite need.",
        "chapter": ("school-of-prayer", 11),
        "paragraph": 2,
    },
    {
        "slug": "andrew-murray-0bdab1a3",
        "text": "Many a one wishes to be saved, but perishes because he does not will it.",
        "chapter": ("school-of-prayer", 11),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-3f9c18d7",
        "text": "In one aspect there must be faith before there can be prayer; in another the faith is the outcome and the growth of prayer.",
        "chapter": ("school-of-prayer", 12),
        "paragraph": 3,
    },
    {
        "slug": "andrew-murray-363d5b2b",
        "text": "Faith in the promise is the fruit of faith in the promiser: the prayer of faith is rooted in the life of faith.",
        "chapter": ("school-of-prayer", 13),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-20f246b8",
        "text": "A heart full of God has power for the prayer of faith.",
        "chapter": ("school-of-prayer", 13),
        "paragraph": 9,
    },
    {
        "slug": "andrew-murray-3a68d90a",
        "text": "Faith can only live by feeding on what is Divine, on God Himself.",
        "chapter": ("school-of-prayer", 14),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-3f0a513b",
        "text": "Not according to what I try to be when praying, but what I am when not praying, is my prayer dealt with by God.",
        "chapter": ("school-of-prayer", 15),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-b8b0d6bf",
        "text": "A prayer meeting without recognised answer to prayer ought to be an anomaly.",
        "chapter": ("school-of-prayer", 16),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-8f923be4",
        "text": "God will not delay one moment longer than is absolutely necessary; He will do all in His power to hasten and speed the answer.",
        "chapter": ("school-of-prayer", 17),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-9a33edf0",
        "text": "Man was created, and has now again been redeemed, to pray, and by his prayer to have dominion.",
        "chapter": ("school-of-prayer", 19),
        "paragraph": 9,
    },
    {
        "slug": "andrew-murray-377c0454",
        "text": "Give yourself, and live, to do the works of Christ and you will learn to pray so as to obtain wonderful answers to prayer.",
        "chapter": ("school-of-prayer", 20),
        "paragraph": 9,
    },
    {
        "slug": "andrew-murray-bb9d377b",
        "text": "With our whole being consciously yielded to the inspiration of the Word and Spirit, our desires will be no longer ours but His; their chief end the glory of God.",
        "chapter": ("school-of-prayer", 21),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-54521d6f",
        "text": "Faith is obedience at home and looking to the Master: obedience is faith going out to do His will.",
        "chapter": ("school-of-prayer", 22),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-254d7f38",
        "text": "The chief thing is, not to know what God has said we must do, but that God Himself says it to us.",
        "chapter": ("school-of-prayer", 23),
        "paragraph": 7,
    },
    {
        "slug": "andrew-murray-6b7ccf7f",
        "text": "Obedience is the only path that leads to the glory of God.",
        "chapter": ("school-of-prayer", 24),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-6862a329",
        "text": "The name and the power of asking go together: when the Name of Jesus has become the power that rules my life, its power in prayer with God will be seen too.",
        "chapter": ("school-of-prayer", 25),
        "paragraph": 8,
    },
    {
        "slug": "andrew-murray-022ae1f5",
        "text": "To pray in the Name of Jesus is to pray in unity, in sympathy with Him.",
        "chapter": ("school-of-prayer", 28),
        "paragraph": 4,
    },
    {
        "slug": "andrew-murray-2196a38c",
        "text": "Every believer ought to pray much that the unity of the Church, not in external organizations, but in spirit and in truth, may be made manifest.",
        "chapter": ("school-of-prayer", 28),
        "paragraph": 8,
    },
    {
        "slug": "andrew-murray-ac9e4831",
        "text": "Our priestly power with God depends on our personal life and walk.",
        "chapter": ("school-of-prayer", 31),
        "paragraph": 6,
    },
    {
        "slug": "andrew-murray-7d56611c",
        "text": "God needs, greatly needs, priests who can draw near to Him, who live in His presence, and by their intercession draw down the blessings of His grace on others.",
        "chapter": ("school-of-prayer", 31),
        "paragraph": 11,
    },
    {
        "slug": "andrew-murray-0865b7b0",
        "text": "Christ is all, the life and the strength too for a never-ceasing prayer-life.",
        "chapter": ("school-of-prayer", 32),
        "paragraph": 5,
    },
    {
        "slug": "andrew-murray-b1464290",
        "text": "Not in God, not in His secret will, not in the limitations of His promises, but in us, in ourselves is the hindrance; we are not what we should be to obtain the promise.",
        "chapter": ("school-of-prayer", 32),
        "paragraph": 3,
    },
]


E_M_BOUNDS = [
    {
        "slug": "e-m-bounds-3b245347",
        "text": "Faith does the impossible because it brings God to undertake for us, and nothing is impossible with God.",
        "chapter": ("necessity-of-prayer", 2),
        "paragraph": 2,
    },
    {
        "slug": "e-m-bounds-b174257b",
        "text": "Christ holds Himself ready to supply exactly, and fully, all the demands of faith and prayer.",
        "chapter": ("necessity-of-prayer", 3),
        "paragraph": 7,
    },
    {
        "slug": "e-m-bounds-6b8891e3",
        "text": "Nothing distinguishes the children of God so clearly and strongly as prayer.",
        "chapter": ("necessity-of-prayer", 7),
        "paragraph": 4,
    },
    {
        "slug": "e-m-bounds-49d3b925",
        "text": "Nothing is too hard for prayer because nothing is too hard for God.",
        "chapter": ("prayer-and-praying-men", 3),
        "paragraph": 6,
    },
    {
        "slug": "e-m-bounds-52b568c0",
        "text": "The story of every great Christian achievement is the history of answered prayer.",
        "chapter": ("purpose-in-prayer", 2),
        "paragraph": 26,
    },
    {
        "slug": "e-m-bounds-6e68a441",
        "text": "No person is a soul-winner who is not an adept in the ministry of prayer.",
        "chapter": ("purpose-in-prayer", 7),
        "paragraph": 10,
    },
    {
        "slug": "e-m-bounds-1f61d2a7",
        "text": "The closet cannot be made holy to God when the life has not been holy to God.",
        "chapter": ("purpose-in-prayer", 10),
        "paragraph": 30,
    },
    {
        "slug": "e-m-bounds-456fba5b",
        "text": "Prayer is mighty in its operations, and God never disappoints those who put their trust and confidence in Him.",
        "chapter": ("purpose-in-prayer", 11),
        "paragraph": 14,
    },
    {
        "slug": "e-m-bounds-b26355f0",
        "text": "Every revival of which we have any record has been bathed in prayer.",
        "chapter": ("purpose-in-prayer", 12),
        "paragraph": 17,
    },
    {
        "slug": "e-m-bounds-38b0ca28",
        "text": "Faith in Christ is the basis of all working, and of all praying.",
        "chapter": ("necessity-of-prayer", 2),
        "paragraph": 29,
    },
    {
        "slug": "e-m-bounds-170e43be",
        "text": "Faith is not an aimless act of the soul, but a looking to God and a resting upon His promises.",
        "chapter": ("necessity-of-prayer", 3),
        "paragraph": 9,
    },
    {
        "slug": "e-m-bounds-cc849a69",
        "text": "Faith is not believing just anything; it is believing God, resting in Him, trusting His Word.",
        "chapter": ("necessity-of-prayer", 3),
        "paragraph": 9,
    },
    {
        "slug": "e-m-bounds-d44f9cee",
        "text": "To see God, to know God, and to live for God -- these form the objective of all true praying.",
        "chapter": ("necessity-of-prayer", 5),
        "paragraph": 33,
    },
    {
        "slug": "e-m-bounds-ab7864b0",
        "text": "The difficulty in prayer is not with faith, but with obedience, which is faith's foundation.",
        "chapter": ("necessity-of-prayer", 11),
        "paragraph": 14,
    },
    {
        "slug": "e-m-bounds-7894b850",
        "text": "No man can pray -- really pray -- who does not obey.",
        "chapter": ("necessity-of-prayer", 11),
        "paragraph": 16,
    },
    {
        "slug": "e-m-bounds-ca009ef5",
        "text": "The will must be surrendered to God as a primary condition of all successful praying.",
        "chapter": ("necessity-of-prayer", 11),
        "paragraph": 17,
    },
    {
        "slug": "e-m-bounds-aac43fc2",
        "text": "Prayer is not simply to get things from God, but to make those things holy, which already have been received from Him.",
        "chapter": ("necessity-of-prayer", 13),
        "paragraph": 31,
    },
    {
        "slug": "e-m-bounds-927b8825",
        "text": "The past has not exhausted the possibilities nor the demands for doing great things for God.",
        "chapter": ("power-through-prayer", 20),
        "paragraph": 8,
    },
    {
        "slug": "e-m-bounds-07331d8e",
        "text": "The name and honor of Jesus Christ, the advance of his cause, must be all in all.",
        "chapter": ("power-through-prayer", 10),
        "paragraph": 4,
    },
    {
        "slug": "e-m-bounds-054f2705",
        "text": "The number and efficiency of the labourers in God’s vineyard in all lands is dependent on the men of prayer.",
        "chapter": ("purpose-in-prayer", 8),
        "paragraph": 15,
    },
    {
        "slug": "e-m-bounds-01f9f8d8",
        "text": "Prayer is not a mere form of words; it is not just calling upon a Name.",
        "chapter": ("necessity-of-prayer", 11),
        "paragraph": 9,
    },
    {
        "slug": "e-m-bounds-af08081e",
        "text": "The one prominent characteristic of the experience into which believers are brought through prayer, is not a life of works, but of faith.",
        "chapter": ("necessity-of-prayer", 3),
        "paragraph": 30,
    },
    {
        "slug": "e-m-bounds-bef0ccaf",
        "text": "Love of ease, spiritual indolence, religious slothfulness, all operate against this type of petitioning.",
        "chapter": ("necessity-of-prayer", 8),
        "paragraph": 16,
    },
    {
        "slug": "e-m-bounds-da0bf2bc",
        "text": "To do God's will without demur, is the joy as it is the privilege of the successful praying-man.",
        "chapter": ("necessity-of-prayer", 10),
        "paragraph": 30,
    },
    {
        "slug": "e-m-bounds-4945fb19",
        "text": "The spirit which prompts a man to break one commandment is the spirit which may move him to break them all.",
        "chapter": ("necessity-of-prayer", 10),
        "paragraph": 12,
    },
    {
        "slug": "e-m-bounds-2b2db6e0",
        "text": "The Christian soldier is to pray at all seasons, and under all circumstances.",
        "chapter": ("necessity-of-prayer", 12),
        "paragraph": 18,
    },
    {
        "slug": "e-m-bounds-aaca3882",
        "text": "The entire life of a Christian soldier -- its being, intention, implication and action -- are all dependent on its being a life of prayer.",
        "chapter": ("necessity-of-prayer", 12),
        "paragraph": 30,
    },
    {
        "slug": "e-m-bounds-056461e2",
        "text": "Nothing short of being red hot for God, can keep the glow of heaven in our hearts, these chilly days.",
        "chapter": ("necessity-of-prayer", 5),
        "paragraph": 19,
    },
    {
        "slug": "e-m-bounds-019df67e",
        "text": "God is so concerned that men pray that He has promised to answer prayer.",
        "chapter": ("reality-of-prayer", 1),
        "paragraph": 17,
    },
    {
        "slug": "e-m-bounds-5c98ee06",
        "text": "Prayer is the seeking of God’s great and greatest good, which will not come if we do not pray.",
        "chapter": ("reality-of-prayer", 2),
        "paragraph": 9,
    },
    {
        "slug": "e-m-bounds-fa8348c7",
        "text": "Prayer is the child’s request, not to the winds nor to the world, but to the Father.",
        "chapter": ("reality-of-prayer", 2),
        "paragraph": 9,
    },
    {
        "slug": "e-m-bounds-81aa80b3",
        "text": "Prayer is God’s plan to supply man’s great and continuous need with God’s great and continuous abundance.",
        "chapter": ("reality-of-prayer", 2),
        "paragraph": 13,
    },
    {
        "slug": "e-m-bounds-31dfd977",
        "text": "God has everything to do with prayer, as well as everything to do with the one who prays.",
        "chapter": ("reality-of-prayer", 4),
        "paragraph": 5,
    },
    {
        "slug": "e-m-bounds-cac9217a",
        "text": "God’s Gospel has always waited more on prayer than on anything else for its successes.",
        "chapter": ("reality-of-prayer", 16),
        "paragraph": 6,
    },
    {
        "slug": "e-m-bounds-eaa3a1c9",
        "text": "Prayer is the only element in which the Holy Spirit can live and work.",
        "chapter": ("reality-of-prayer", 16),
        "paragraph": 9,
    },
    {
        "slug": "e-m-bounds-b95b2a8f",
        "text": "Jesus Christ was always a busy man with His work, but never too busy to pray.",
        "chapter": ("reality-of-prayer", 7),
        "paragraph": 25,
    },
    {
        "slug": "e-m-bounds-3aad54a5",
        "text": "Prayer does not interpret God’s providences, but it does justify them and recognise God in them.",
        "chapter": ("essentials-of-prayer", 5),
        "paragraph": 22,
    },
    {
        "slug": "e-m-bounds-7b379a07",
        "text": "Prayer without fervour is as a sun without light or heat, or as a flower without beauty or fragrance.",
        "chapter": ("essentials-of-prayer", 3),
        "paragraph": 16,
    },
    {
        "slug": "e-m-bounds-20b5210a",
        "text": "God can afford to commit Himself in prayer to those who have fully committed themselves to God.",
        "chapter": ("essentials-of-prayer", 8),
        "paragraph": 16,
    },
    {
        "slug": "e-m-bounds-1ce791ff",
        "text": "Prayer holds earth to heaven and brings heaven in close contact with earth.",
        "chapter": ("essentials-of-prayer", 12),
        "paragraph": 25,
    },
    {
        "slug": "e-m-bounds-3de95408",
        "text": "Prayer is intended for all men, because all men need God and need what God has and what prayer only can secure.",
        "chapter": ("essentials-of-prayer", 12),
        "paragraph": 2,
    },
    {
        "slug": "e-m-bounds-552c19f1",
        "text": "Prayer so prepares the heart that it softens under the disciplining hand of God.",
        "chapter": ("essentials-of-prayer", 5),
        "paragraph": 33,
    },
    {
        "slug": "e-m-bounds-55b9917c",
        "text": "The prayer life is the direct fruit of entire consecration to God.",
        "chapter": ("essentials-of-prayer", 9),
        "paragraph": 16,
    },
    {
        "slug": "e-m-bounds-4d0e283e",
        "text": "God wants consecrated men because they can pray and will pray.",
        "chapter": ("essentials-of-prayer", 8),
        "paragraph": 20,
    },
    {
        "slug": "e-m-bounds-ec80b3c8",
        "text": "Prayer promotes the spirit of devotion, while devotion is favourable to the best praying.",
        "chapter": ("essentials-of-prayer", 3),
        "paragraph": 4,
    },
    {
        "slug": "e-m-bounds-ad66c674",
        "text": "Prayer is natural and almost spontaneous when compassion is begotten in the heart.",
        "chapter": ("essentials-of-prayer", 10),
        "paragraph": 3,
    },
    {
        "slug": "e-m-bounds-132bf8cd",
        "text": "The prayer is made to God and the issue is with God.",
        "chapter": ("prayer-and-praying-men", 6),
        "paragraph": 19,
    },
    {
        "slug": "e-m-bounds-541d3401",
        "text": "God’s people were always safe when their princes were princes in prayer.",
        "chapter": ("prayer-and-praying-men", 7),
        "paragraph": 12,
    },
    {
        "slug": "e-m-bounds-f89a467a",
        "text": "Nothing is clearer than that prayer has its only worth and significance in the great fact that God hears and answers prayer.",
        "chapter": ("prayer-and-praying-men", 3),
        "paragraph": 8,
    },
    {
        "slug": "e-m-bounds-bb90e88c",
        "text": "Prayer breaks all bars, dissolves all chains, opens all prisons and widens all straits by which God’s saints have been holden.",
        "chapter": ("prayer-and-praying-men", 7),
        "paragraph": 46,
    },
    {
        "slug": "e-m-bounds-d8c4a388",
        "text": "Prayer unites with the purposes of God and lays itself out to secure those purposes.",
        "chapter": ("prayer-and-praying-men", 5),
        "paragraph": 1,
    },
    {
        "slug": "e-m-bounds-d3d581c6",
        "text": "Prayer makes the man; prayer makes the preacher; prayer makes the pastor.",
        "chapter": ("power-through-prayer", 1),
        "paragraph": 10,
    },
    {
        "slug": "e-m-bounds-d4c5d477",
        "text": "Prayer puts the preacher’s heart into the preacher’s sermon; prayer puts the preacher’s sermon into the preacher’s heart.",
        "chapter": ("power-through-prayer", 12),
        "paragraph": 5,
    },
    {
        "slug": "e-m-bounds-d464b8c2",
        "text": "God’s true preachers have been distinguished by one great feature: they were men of prayer.",
        "chapter": ("power-through-prayer", 6),
        "paragraph": 4,
    },
    {
        "slug": "e-m-bounds-b99a6740",
        "text": "Prayer which is felt as a mighty force is the mediate or immediate product of much time spent with God.",
        "chapter": ("power-through-prayer", 7),
        "paragraph": 1,
    },
]

AUGUSTINE = [
    {
        "slug": "augustine-of-hippo-01e56d20",
        "text": "Thou awakest us to delight in Thy praise; for Thou madest us for Thyself, and our heart is restless, until it repose in Thee.",
        "chapter": ("confessions", 1),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-71005631",
        "text": "Too late loved I Thee, O Thou Beauty of ancient days, yet ever new!",
        "chapter": ("confessions", 10),
        "paragraph": 64,
    },
    {
        "slug": "augustine-of-hippo-c389620c",
        "text": "Thou enjoinest continency: give me what Thou enjoinest, and enjoin what Thou wilt.",
        "chapter": ("confessions", 10),
        "paragraph": 68,
    },
    {
        "slug": "augustine-of-hippo-88e28a03",
        "text": "By continency verily are we bound up and brought back into One, whence we were dissipated into many.",
        "chapter": ("confessions", 10),
        "paragraph": 68,
    },
    {
        "slug": "augustine-of-hippo-6e758fea",
        "text": "The mind commands the body, and it obeys instantly; the mind commands itself, and is resisted.",
        "chapter": ("confessions", 8),
        "paragraph": 32,
    },
    {
        "slug": "augustine-of-hippo-5bdf6944",
        "text": "Man himself is a great deep, whose very hairs Thou numberest, O Lord, and they fall not to the ground without Thee.",
        "chapter": ("confessions", 4),
        "paragraph": 36,
    },
    {
        "slug": "augustine-of-hippo-28a0d308",
        "text": "Let the restless, the godless, depart and flee from Thee; yet Thou seest them, and dividest the darkness.",
        "chapter": ("confessions", 5),
        "paragraph": 3,
    },
    {
        "slug": "augustine-of-hippo-f39c2fe5",
        "text": "The Way, the Saviour Himself, well pleased me, but as yet I shrunk from going through its straitness.",
        "chapter": ("confessions", 8),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-b4abaa5a",
        "text": "Nothing then of Thy Word doth give place or replace, because It is truly immortal and eternal.",
        "chapter": ("confessions", 11),
        "paragraph": 15,
    },
    {
        "slug": "augustine-of-hippo-ae703f88",
        "text": "When out of their order, they are restless; restored to order, they are at rest.",
        "chapter": ("confessions", 13),
        "paragraph": 18,
    },
    {
        "slug": "augustine-of-hippo-74654bbf",
        "text": "Let me know Thee, O Lord, who knowest me: let me know Thee, as I am known.",
        "chapter": ("confessions", 10),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-c210876c",
        "text": "To Thy grace I ascribe it, and to Thy mercy, that Thou hast melted away my sins as it were ice.",
        "chapter": ("confessions", 2),
        "paragraph": 21,
    },
    {
        "slug": "augustine-of-hippo-8a53adb9",
        "text": "Let my soul cleave unto Thee, now that Thou hast freed it from that fast-holding birdlime of death.",
        "chapter": ("confessions", 6),
        "paragraph": 14,
    },
    {
        "slug": "augustine-of-hippo-2be5d987",
        "text": "I will now call to mind my past foulness, and the carnal corruptions of my soul; not because I love them, but that I may love Thee, O my God.",
        "chapter": ("confessions", 2),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-42c3e683",
        "text": "Not with doubting, but with assured consciousness, do I love Thee, Lord.",
        "chapter": ("confessions", 10),
        "paragraph": 13,
    },
    {
        "slug": "augustine-of-hippo-6218667a",
        "text": "He is within the very heart, yet hath the heart strayed from Him.",
        "chapter": ("confessions", 4),
        "paragraph": 30,
    },
    {
        "slug": "augustine-of-hippo-babac59e",
        "text": "The mind commands the mind, its own self, to will, and yet it doth not.",
        "chapter": ("confessions", 8),
        "paragraph": 32,
    },
    {
        "slug": "augustine-of-hippo-5d965455",
        "text": "All consult Thee on what they will, though they hear not always what they will.",
        "chapter": ("confessions", 10),
        "paragraph": 62,
    },
    {
        "slug": "augustine-of-hippo-cd00fc05",
        "text": "What then do I love, when I love my God? who is He above the head of my soul?",
        "chapter": ("confessions", 10),
        "paragraph": 17,
    },
    {
        "slug": "augustine-of-hippo-f80a2bf6",
        "text": "In these two you have those three graces exemplified: faith believes, hope and love pray.",
        "chapter": ("enchiridion", 1),
        "paragraph": 13,
    },
    {
        "slug": "augustine-of-hippo-87986dcb",
        "text": "The fact that we do not see either what we believe or what we hope for, is all that is common to faith and hope.",
        "chapter": ("enchiridion", 1),
        "paragraph": 15,
    },
    {
        "slug": "augustine-of-hippo-78996a5d",
        "text": "Although, therefore, evil, in so far as it is evil, is not a good; yet the fact that evil as well as good exists, is a good.",
        "chapter": ("enchiridion", 8),
        "paragraph": 25,
    },
    {
        "slug": "augustine-of-hippo-a64a90a8",
        "text": "From what is good, then, evils arose, and except in what is good they do not exist; nor was there any other source from which any evil nature could arise.",
        "chapter": ("enchiridion", 2),
        "paragraph": 11,
    },
    {
        "slug": "augustine-of-hippo-f4cae61f",
        "text": "To me, however, it seems certain that every lie is a sin, though it makes a great difference with what intention and on what subject one lies.",
        "chapter": ("enchiridion", 2),
        "paragraph": 19,
    },
    {
        "slug": "augustine-of-hippo-567e0947",
        "text": "No one, of course, is to be condemned as a liar who says what is false, believing it to be true, because such an one does not consciously deceive, but rather is himself deceived.",
        "chapter": ("enchiridion", 2),
        "paragraph": 19,
    },
    {
        "slug": "augustine-of-hippo-1d48b0f6",
        "text": "After the fall, however, a more abundant exercise of God’s mercy was required, because the will itself had to be freed from the bondage in which it was held by sin and death.",
        "chapter": ("enchiridion", 9),
        "paragraph": 19,
    },
    {
        "slug": "augustine-of-hippo-f72c34ba",
        "text": "As, then, the soul even now finds it impossible to desire unhappiness, so in future it shall be wholly impossible for it to desire sin.",
        "chapter": ("enchiridion", 9),
        "paragraph": 17,
    },
    {
        "slug": "augustine-of-hippo-a1a3aac4",
        "text": "Man, therefore, was thus made upright that, though unable to remain in his uprightness without divine help, he could of his own mere will depart from it.",
        "chapter": ("enchiridion", 9),
        "paragraph": 21,
    },
    {
        "slug": "augustine-of-hippo-196b5d19",
        "text": "No one, then, need hope that after he is dead he shall obtain merit with God which he has neglected to secure here.",
        "chapter": ("enchiridion", 9),
        "paragraph": 27,
    },
    {
        "slug": "augustine-of-hippo-111df642",
        "text": "What goodness of will, what goodness of desire and intention, what good works, had gone before, which made this man worthy to become one person with God?",
        "chapter": ("enchiridion", 4),
        "paragraph": 7,
    },
    {
        "slug": "augustine-of-hippo-d1100b98",
        "text": "The man whom the thunder of this warning does not awaken is not asleep, but dead; and yet so powerful is that voice, that it can awaken even the dead.",
        "chapter": ("enchiridion", 7),
        "paragraph": 15,
    },
    {
        "slug": "augustine-of-hippo-daf2b4a0",
        "text": "For when there is a question as to whether a man is good, one does not ask what he believes, or what he hopes, but what he loves.",
        "chapter": ("enchiridion", 11),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-e0fb2a79",
        "text": "We love God now by faith, then we shall love Him through sight.",
        "chapter": ("enchiridion", 11),
        "paragraph": 9,
    },
    {
        "slug": "augustine-of-hippo-7df12100",
        "text": "Of these four different stages the first is before the law, the second is under the law, the third is under grace, and the fourth is in full and perfect peace.",
        "chapter": ("enchiridion", 11),
        "paragraph": 3,
    },
    {
        "slug": "augustine-of-hippo-2c5b7319",
        "text": "Now we love even our neighbor by faith; for we who are ourselves mortal know not the hearts of mortal men.",
        "chapter": ("enchiridion", 11),
        "paragraph": 9,
    },
    {
        "slug": "augustine-of-hippo-b15cdf51",
        "text": "Surely unhappy is he who knoweth all these, and knoweth not Thee: but happy whoso knoweth Thee, though he know not these.",
        "chapter": ("confessions", 5),
        "paragraph": 10,
    },
    {
        "slug": "augustine-of-hippo-bd88fc3a",
        "text": "Surely vain are all men who are ignorant of God, and could not out of the good things which are seen, find out Him who is good.",
        "chapter": ("confessions", 8),
        "paragraph": 2,
    },
    {
        "slug": "augustine-of-hippo-1699c301",
        "text": "Thou light of my heart, Thou bread of my inmost soul, Thou Power who givest vigour to my mind, who quickenest my thoughts, I loved Thee not.",
        "chapter": ("confessions", 1),
        "paragraph": 33,
    },
    {
        "slug": "augustine-of-hippo-5176d739",
        "text": "Let not these occupy my soul; let God rather occupy it, who made these things, very good indeed, yet is He my good, not they.",
        "chapter": ("confessions", 10),
        "paragraph": 84,
    },
    {
        "slug": "augustine-of-hippo-c006d51a",
        "text": "I call upon Thee, O my God, my mercy, Who createdst me, and forgottest not me, forgetting Thee.",
        "chapter": ("confessions", 13),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-2fc36ce4",
        "text": "Be not foolish, O my soul, nor become deaf in the ear of thine heart with the tumult of thy folly.",
        "chapter": ("confessions", 4),
        "paragraph": 26,
    },
    {
        "slug": "augustine-of-hippo-109ebfbc",
        "text": "The Word itself calleth thee to return: and there is the place of rest imperturbable, where love is not forsaken, if itself forsaketh not.",
        "chapter": ("confessions", 4),
        "paragraph": 27,
    },
    {
        "slug": "augustine-of-hippo-e35729b7",
        "text": "Let them then be turned, and seek Thee; because not as they have forsaken their Creator, hast Thou forsaken Thy creation.",
        "chapter": ("confessions", 5),
        "paragraph": 3,
    },
    {
        "slug": "augustine-of-hippo-c2f65106",
        "text": "Thou didst rescue my tongue, whence Thou hadst before rescued my heart.",
        "chapter": ("confessions", 9),
        "paragraph": 10,
    },
    {
        "slug": "augustine-of-hippo-6534752e",
        "text": "Let me not be mine own life; from myself I lived ill, death was I to myself; and I revive in Thee.",
        "chapter": ("confessions", 12),
        "paragraph": 19,
    },
    {
        "slug": "augustine-of-hippo-cb389651",
        "text": "Luxury affects to be called plenty and abundance; but Thou art the fulness and never-failing plenteousness of incorruptible pleasures.",
        "chapter": ("confessions", 2),
        "paragraph": 18,
    },
    {
        "slug": "augustine-of-hippo-d10a086f",
        "text": "O Thou Good omnipotent, who so carest for every one of us, as if Thou caredst for him only; and so for all, as if they were but one!",
        "chapter": ("confessions", 3),
        "paragraph": 29,
    },
    {
        "slug": "augustine-of-hippo-88c4ad24",
        "text": "I sought what I might love, in love with loving, and safety I hated, and a way without snares.",
        "chapter": ("confessions", 3),
        "paragraph": 1,
    },
    {
        "slug": "augustine-of-hippo-22d8524d",
        "text": "When, then, we believe that good is about to come, this is nothing else but to hope for it.",
        "chapter": ("enchiridion", 1),
        "paragraph": 15,
    },
    {
        "slug": "augustine-of-hippo-4db0559b",
        "text": "O let the Light, the Truth, the Light of my heart, not mine own darkness, speak unto me.",
        "chapter": ("confessions", 12),
        "paragraph": 19,
    },
]

JONATHAN_EDWARDS = [
    {
        "slug": "jonathan-edwards-028e1a61",
        "text": "Nothing can be invented that is a greater absurdity, than a morose, hard, close, high-spirited, spiteful, true Christian.",
        "chapter": ("religious-affections", 22),
        "paragraph": 18,
    },
    {
        "slug": "jonathan-edwards-32a16695",
        "text": "The kingdom of heaven is not to be taken but by violence.",
        "chapter": ("religious-affections", 26),
        "paragraph": 6,
    },
    {
        "slug": "jonathan-edwards-4daf7d38",
        "text": "The deceitfulness of the heart of man appears in no one thing so much as this of spiritual pride and self-righteousness.",
        "chapter": ("religious-affections", 20),
        "paragraph": 9,
    },
    {
        "slug": "jonathan-edwards-12bd1ec0",
        "text": "Nothing is more manifest in fact, than that the things of religion take hold of men's souls, no further than they affect them.",
        "chapter": ("religious-affections", 2),
        "paragraph": 39,
    },
    {
        "slug": "jonathan-edwards-a32641a0",
        "text": "The soul of a saint, by having something of God opened to sight, is convinced of much more than is seen.",
        "chapter": ("religious-affections", 20),
        "paragraph": 17,
    },
    {
        "slug": "jonathan-edwards-35c8dd47",
        "text": "The former rejoices in himself; self is the first foundation of his joy: the latter rejoices in God.",
        "chapter": ("religious-affections", 16),
        "paragraph": 20,
    },
    {
        "slug": "jonathan-edwards-5d08473b",
        "text": "The true beauty and loveliness of all intelligent beings does primarily and most essentially consist in their moral excellency or holiness.",
        "chapter": ("religious-affections", 17),
        "paragraph": 9,
    },
    {
        "slug": "jonathan-edwards-f0750291",
        "text": "The saint's affections begin with God; and self-love has a hand in these affections consequentially, and secondarily only.",
        "chapter": ("religious-affections", 16),
        "paragraph": 13,
    },
    {
        "slug": "jonathan-edwards-1a52dfe1",
        "text": "God has revealed no certain connection between salvation, and any qualifications in men, but only grace and its fruits.",
        "chapter": ("religious-affections", 10),
        "paragraph": 15,
    },
    {
        "slug": "jonathan-edwards-7617f48e",
        "text": "The saints desire the sincere milk of the word, not so much to testify God's love to them, as that they may grow thereby in holiness.",
        "chapter": ("religious-affections", 25),
        "paragraph": 8,
    },
    {
        "slug": "jonathan-edwards-257aca58",
        "text": "The subtlety of Satan appears in its height, in his managing of persons with respect to this sin.",
        "chapter": ("religious-affections", 20),
        "paragraph": 9,
    },
    {
        "slug": "jonathan-edwards-20cf3293",
        "text": "There is not only a rational belief that God is holy and that holiness is a good thing, but there is a sense of the loveliness of God’s holiness.",
        "chapter": ("selected-sermons-edwards", 3),
        "paragraph": 28,
    },
    {
        "slug": "jonathan-edwards-f9dba01f",
        "text": "Faith abases men and exalts God, it gives all the glory of redemption to God alone.",
        "chapter": ("selected-sermons-edwards", 2),
        "paragraph": 55,
    },
    {
        "slug": "jonathan-edwards-f3a4122f",
        "text": "None that will come to Christ, let his condition be what it will, need to fear but that Christ will provide a place suitable for him in heaven.",
        "chapter": ("selected-sermons-edwards", 5),
        "paragraph": 16,
    },
    {
        "slug": "jonathan-edwards-707150e7",
        "text": "Holiness and happiness are in the fruit, here and hereafter, because God dwells in them, and they in God.",
        "chapter": ("selected-sermons-edwards", 2),
        "paragraph": 42,
    },
    {
        "slug": "jonathan-edwards-278945d4",
        "text": "The sword of divine justice is every moment brandished over their heads, and ’tis nothing but the hand of arbitrary mercy, and God’s mere will, that holds it back.",
        "chapter": ("selected-sermons-edwards", 6),
        "paragraph": 13,
    },
    {
        "slug": "jonathan-edwards-053525a7",
        "text": "It is God that gives us faith whereby we close with Christ.",
        "chapter": ("selected-sermons-edwards", 2),
        "paragraph": 8,
    },
    {
        "slug": "jonathan-edwards-961af03e",
        "text": "The Spirit of God may act upon a creature, and yet not in acting communicate himself.",
        "chapter": ("selected-sermons-edwards", 3),
        "paragraph": 20,
    },
    {
        "slug": "jonathan-edwards-0334dcf6",
        "text": "We may often observe it, that the Holy Spirit who indited the Scriptures, often takes notice of little things, minute occurrences, that do but remotely relate to Jesus Christ.",
        "chapter": ("selected-sermons-edwards", 4),
        "paragraph": 2,
    },
    {
        "slug": "jonathan-edwards-b7680c47",
        "text": "Many that others worship and serve as gods are cruel beings, spirits that seek the ruin of souls; but this is a God that delighteth in mercy; his grace is infinite and endures forever.",
        "chapter": ("selected-sermons-edwards", 4),
        "paragraph": 12,
    },
    {
        "slug": "jonathan-edwards-27f6a365",
        "text": "He does not merely rationally believe that God is glorious, but he has a sense of the gloriousness of God in his heart.",
        "chapter": ("selected-sermons-edwards", 3),
        "paragraph": 28,
    },
    {
        "slug": "jonathan-edwards-193b1c59",
        "text": "Love is an affection, but will any Christian say, men ought not to love God and Jesus Christ in a high degree?",
        "chapter": ("religious-affections", 3),
        "paragraph": 2,
    },
    {
        "slug": "jonathan-edwards-b82be46e",
        "text": "Fear is cast out by the Spirit of God, no other way than by the prevailing of love; nor is it ever maintained by his Spirit but when love is asleep.",
        "chapter": ("religious-affections", 13),
        "paragraph": 17,
    },
    {
        "slug": "jonathan-edwards-4d2570d4",
        "text": "If we would learn what true religion is, we must go where there is true religion, and nothing but true religion, and in its highest perfection, without any defect or mixture.",
        "chapter": ("religious-affections", 2),
        "paragraph": 67,
    },
    {
        "slug": "jonathan-edwards-e429bd29",
        "text": "If we be not in good earnest in religion, and our wills and inclinations be not strongly exercised, we are nothing.",
        "chapter": ("religious-affections", 2),
        "paragraph": 34,
    },
    {
        "slug": "jonathan-edwards-2f3de031",
        "text": "The saints' love to God is the fruit of God's love to them, as it is the gift of that love.",
        "chapter": ("religious-affections", 16),
        "paragraph": 19,
    },
    {
        "slug": "jonathan-edwards-43b90c7e",
        "text": "A spirit of pride of man's own righteousness, morality, holiness, affection, experience, faith, humiliation, or any goodness whatsoever, is a legal spirit.",
        "chapter": ("religious-affections", 20),
        "paragraph": 6,
    },
    {
        "slug": "jonathan-edwards-786db3ae",
        "text": "A proud spirit is a rebellious spirit, but a humble spirit is a yieldable, subject, obediential spirit.",
        "chapter": ("religious-affections", 26),
        "paragraph": 21,
    },
    {
        "slug": "jonathan-edwards-c02f29d7",
        "text": "Godliness consists not in a heart to intend to do the will of God, but in a heart to do it.",
        "chapter": ("religious-affections", 26),
        "paragraph": 65,
    },
    {
        "slug": "jonathan-edwards-b41b9375",
        "text": "What chiefly makes a man, or any creature lovely, is his excellency; and so what chiefly renders God lovely, and must undoubtedly be the chief ground of true love, is his excellency.",
        "chapter": ("religious-affections", 16),
        "paragraph": 6,
    },
    {
        "slug": "jonathan-edwards-90170d1f",
        "text": "A natural principle of self-love may be the foundation of great affections towards God and Christ, without seeing anything of the beauty and glory of the divine nature.",
        "chapter": ("religious-affections", 16),
        "paragraph": 7,
    },
    {
        "slug": "jonathan-edwards-fb6548c8",
        "text": "Herein consists the beauty of the saints, that they are saints, or holy ones; it is the moral image of God in them, which is their beauty; and that is their holiness.",
        "chapter": ("religious-affections", 17),
        "paragraph": 11,
    },
    {
        "slug": "jonathan-edwards-cf2c4824",
        "text": "Conversion is a great and universal change of the man, turning him from sin to God.",
        "chapter": ("religious-affections", 21),
        "paragraph": 3,
    },
    {
        "slug": "jonathan-edwards-39fe77bc",
        "text": "Holy fear is so much the nature of true godliness, that it is called in Scripture by no other name more frequently, than the fear of God.",
        "chapter": ("religious-affections", 23),
        "paragraph": 5,
    },
    {
        "slug": "jonathan-edwards-406773f3",
        "text": "Every dog hath his kennel, every swine hath his swill; and every wicked man his lust.",
        "chapter": ("religious-affections", 26),
        "paragraph": 32,
    },
    {
        "slug": "jonathan-edwards-46a608bf",
        "text": "Holy affections are not heat without light; but evermore arise from the information of the understanding, some spiritual instruction that the mind receives, some light or actual knowledge.",
        "chapter": ("religious-affections", 18),
        "paragraph": 1,
    },
    {
        "slug": "jonathan-edwards-80a1ab38",
        "text": "Persons may seem to have love to God and Christ, yea, to have very strong and violent affections of this nature, and yet have no grace.",
        "chapter": ("religious-affections", 8),
        "paragraph": 3,
    },
    {
        "slug": "jonathan-edwards-c8077ab3",
        "text": "The true saints have not such a spirit of discerning that they can certainly determine who are godly, and who are not.",
        "chapter": ("religious-affections", 14),
        "paragraph": 1,
    },
    {
        "slug": "jonathan-edwards-4a8c058b",
        "text": "All the kings of the earth before God are as grasshoppers; they are nothing, and less than nothing: both their love and their hatred is to be despised.",
        "chapter": ("selected-sermons-edwards", 6),
        "paragraph": 37,
    },
    {
        "slug": "jonathan-edwards-2f83aa62",
        "text": "Man hath now a greater dependence on the grace of God than he had before the fall.",
        "chapter": ("selected-sermons-edwards", 2),
        "paragraph": 24,
    },
    {
        "slug": "jonathan-edwards-fe469383",
        "text": "Wisdom was a thing that the Greeks admired; but Christ is the true light of the world, it is through him alone that true wisdom is imparted to the mind.",
        "chapter": ("selected-sermons-edwards", 2),
        "paragraph": 6,
    },
    {
        "slug": "jonathan-edwards-1adaf802",
        "text": "We are dependent on the power of God to convert us, and give faith in Jesus Christ, and the new nature.",
        "chapter": ("selected-sermons-edwards", 2),
        "paragraph": 28,
    },
    {
        "slug": "jonathan-edwards-88349935",
        "text": "How great is their glory and honor that are admitted to be of the household of God!",
        "chapter": ("selected-sermons-edwards", 5),
        "paragraph": 30,
    },
    {
        "slug": "jonathan-edwards-d990b657",
        "text": "The soul of every man craves a happiness that is equal to the capacity of his nature.",
        "sermon": "safety-fulness-and-sweet-refreshment-in-christ",
        "paragraph": 41,
    },
    {
        "slug": "jonathan-edwards-411b4379",
        "text": "Christ never so eminently appeared for divine justice, and yet never suffered so much from divine Justice, as when he offered up himself a sacrifice for our sins.",
        "sermon": "the-excellency-of-christ",
        "paragraph": 71,
    },
    {
        "slug": "jonathan-edwards-5b3032a3",
        "text": "None are so low or inferior, but Christ's condescension is sufficient to take a gracious notice of them.",
        "sermon": "the-excellency-of-christ",
        "paragraph": 19,
    },
    {
        "slug": "jonathan-edwards-2591b226",
        "text": "Our understandings, if we stretch them never so far, cannot reach up to his divine glory.",
        "sermon": "the-excellency-of-christ",
        "paragraph": 18,
    },
    {
        "slug": "jonathan-edwards-932bdf53",
        "text": "The saint hath spiritual joy and pleasure by a kind of effusion of God on the soul.",
        "sermon": "god-glorified-in-mans-dependence",
        "paragraph": 28,
    },
    {
        "slug": "jonathan-edwards-e8e8a7e6",
        "text": "We are dependent on Christ the Son of God, as he is our wisdom, righteousness, sanctification, and redemption.",
        "sermon": "god-glorified-in-mans-dependence",
        "paragraph": 7,
    },
    {
        "slug": "jonathan-edwards-1481dba4",
        "text": "The reason why it is not dishonorable to be necessarily most holy, is, because holiness in itself is an excellent and honourable thing.",
        "chapter": ("freedom-of-the-will", 32),
        "paragraph": 13,
    },
]

JOHN_WESLEY = [
    {
        "slug": "john-wesley-8c6200bd",
        "text": "Prayer is the lifting up of the heart to God: All words of prayer, without this, are mere hypocrisy.",
        "chapter": ("sermons-on-several-occasions", 27),
        "paragraph": 11,
    },
    {
        "slug": "john-wesley-b0fcf5f2",
        "text": "The way to hell has nothing singular in it; but the way to heaven is singularity all over.",
        "chapter": ("sermons-on-several-occasions", 32),
        "paragraph": 27,
    },
    {
        "slug": "john-wesley-9fddda8a",
        "text": "The righteousness of Christ is the whole and sole foundation of all our hope.",
        "chapter": ("sermons-on-several-occasions", 21),
        "paragraph": 42,
    },
    {
        "slug": "john-wesley-60c79eda",
        "text": "Faith is the condition, and the only condition, of sanctification, exactly as it is of justification.",
        "chapter": ("sermons-on-several-occasions", 44),
        "paragraph": 27,
    },
    {
        "slug": "john-wesley-61081fe1",
        "text": "God can give the end without any means at all; but you have no reason to think He will.",
        "chapter": ("sermons-on-several-occasions", 38),
        "paragraph": 44,
    },
    {
        "slug": "john-wesley-9a985cd4",
        "text": "Let not the thought of receiving more grace to-morrow, make you negligent of to-day.",
        "chapter": ("sermons-on-several-occasions", 43),
        "paragraph": 29,
    },
    {
        "slug": "john-wesley-d93987cf",
        "text": "No works are good, which are not done as God hath willed and commanded them to be done.",
        "chapter": ("sermons-on-several-occasions", 6),
        "paragraph": 32,
    },
    {
        "slug": "john-wesley-cf00ad11",
        "text": "Love has purified his heart from envy, malice, wrath, and every unkind temper.",
        "chapter": ("plain-account-christian-perfection", 2),
        "paragraph": 38,
    },
    {
        "slug": "john-wesley-77e024db",
        "text": "The heart has more heat than the eye; yet it cannot see.",
        "chapter": ("plain-account-christian-perfection", 5),
        "paragraph": 105,
    },
    {
        "slug": "john-wesley-27045827",
        "text": "Every new victory which a soul gains is the effect of a new prayer.",
        "chapter": ("plain-account-christian-perfection", 5),
        "paragraph": 165,
    },
    {
        "slug": "john-wesley-b8fe8d3c",
        "text": "The root of all religion is faith, without which it is impossible to please God.",
        "chapter": ("sermons-on-several-occasions", 109),
        "paragraph": 9,
    },
    {
        "slug": "john-wesley-14ab445e",
        "text": "Every action of a Christian that is good, is sanctified by the word and prayer.",
        "chapter": ("sermons-on-several-occasions", 106),
        "paragraph": 38,
    },
    {
        "slug": "john-wesley-185b43a1",
        "text": "Nothing is higher than this, but Christian love; the love of our neighbour, flowing from the love of God.",
        "chapter": ("sermons-on-several-occasions", 92),
        "paragraph": 24,
    },
    {
        "slug": "john-wesley-3185ddc5",
        "text": "The religion of Christ rises infinitely higher, and lies immensely deeper, than all these.",
        "chapter": ("sermons-on-several-occasions", 8),
        "paragraph": 8,
    },
    {
        "slug": "john-wesley-b2f0969f",
        "text": "A man may be in God’s favour though he feel sin; but not if he yields to it.",
        "chapter": ("sermons-on-several-occasions", 14),
        "paragraph": 54,
    },
    {
        "slug": "john-wesley-0d8ca0c2",
        "text": "The pure love of our neighbour, springing from the love of God, thinketh no evil, believeth and hopeth all things.",
        "chapter": ("plain-account-christian-perfection", 3),
        "paragraph": 246,
    },
    {
        "slug": "john-wesley-f5f83dd2",
        "text": "A man of a truly catholic spirit has not now his religion to seek.",
        "chapter": ("sermons-on-several-occasions", 40),
        "paragraph": 40,
    },
    {
        "slug": "john-wesley-08527d5b",
        "text": "The very same is the case with every soul that truly hungers and thirsts after righteousness.",
        "chapter": ("sermons-on-several-occasions", 23),
        "paragraph": 24,
    },
    {
        "slug": "john-wesley-c2096cd8",
        "text": "We might have loved God the Creator, God the Preserver, God the Governor; but there would have been no place for love to God the Redeemer.",
        "chapter": ("sermons-on-several-occasions", 58),
        "paragraph": 26,
    },
    {
        "slug": "john-wesley-69cc6ec9",
        "text": "God gives this faith; in that moment we are accepted of God; and yet, not for the sake of that faith, but of what Christ has done and suffered for us.",
        "chapter": ("sermons-on-several-occasions", 21),
        "paragraph": 42,
    },
    {
        "slug": "john-wesley-6cc20b2f",
        "text": "If we love Him, we cannot but love one another, as Christ loved us.",
        "chapter": ("sermons-on-several-occasions", 95),
        "paragraph": 11,
    },
    {
        "slug": "john-wesley-17ad2058",
        "text": "We know everyone who has peace with God, through Jesus Christ, has power over all sin.",
        "chapter": ("sermons-on-several-occasions", 47),
        "paragraph": 10,
    },
    {
        "slug": "john-wesley-664808a5",
        "text": "It is love excluding sin; love filling the heart, taking up the whole capacity of the soul.",
        "chapter": ("sermons-on-several-occasions", 44),
        "paragraph": 19,
    },
    {
        "slug": "john-wesley-cf8b3317",
        "text": "No suffering, but that of Christ, has any power to expiate sin; and no fire, but that of love, can purify the soul, either in time or in eternity.",
        "chapter": ("sermons-on-several-occasions", 113),
        "paragraph": 31,
    },
    {
        "slug": "john-wesley-697ed3cb",
        "text": "Reason, however cultivated and improved, cannot produce the love of God; which is plain from hence: It cannot produce either faith or hope; from which alone this love can flow.",
        "chapter": ("sermons-on-several-occasions", 71),
        "paragraph": 51,
    },
    {
        "slug": "john-wesley-9142f92d",
        "text": "We have by nature, not only no love, but no fear of God.",
        "chapter": ("sermons-on-several-occasions", 45),
        "paragraph": 20,
    },
    {
        "slug": "john-wesley-a998de10",
        "text": "Many indeed think of being happy with God in heaven; but the being happy in God on earth never entered into their thoughts.",
        "chapter": ("sermons-on-several-occasions", 115),
        "paragraph": 14,
    },
    {
        "slug": "john-wesley-e2deb11e",
        "text": "What we love we delight in: But no man has naturally any delight in God.",
        "chapter": ("sermons-on-several-occasions", 45),
        "paragraph": 19,
    },
    {
        "slug": "john-wesley-baa7a7a5",
        "text": "The foundation is faith, purifying the heart; the end love, preserving a good conscience.",
        "chapter": ("plain-account-christian-perfection", 5),
        "paragraph": 14,
    },
    {
        "slug": "john-wesley-49a416d8",
        "text": "The fruits of this Spirit must not be mere moral virtues, calculated for the comfort and decency of the present life; but holy dispositions, suitable to the instincts of a superior life already begun.",
        "chapter": ("sermons-on-several-occasions", 142),
        "paragraph": 33,
    },
    {
        "slug": "john-wesley-740b7c0e",
        "text": "Believe in the Lord Jesus; and thou, even thou, art reconciled to God.",
        "chapter": ("sermons-on-several-occasions", 6),
        "paragraph": 46,
    },
    {
        "slug": "john-wesley-98c3db43",
        "text": "Outward religion may be where inward is not; but if there is none without, there can be none within.",
        "chapter": ("sermons-on-several-occasions", 135),
        "paragraph": 31,
    },
    {
        "slug": "john-wesley-bd5633fb",
        "text": "The world is the men that know not God, that neither love nor fear him.",
        "chapter": ("sermons-on-several-occasions", 69),
        "paragraph": 25,
    },
    {
        "slug": "john-wesley-b6d3ae5f",
        "text": "Religion is the love of God and our neighbour; that is, every man under heaven.",
        "chapter": ("sermons-on-several-occasions", 85),
        "paragraph": 47,
    },
    {
        "slug": "john-wesley-2b7968c1",
        "text": "Sin is then overcome, but it is not rooted out; it is conquered, but not destroyed.",
        "chapter": ("sermons-on-several-occasions", 124),
        "paragraph": 39,
    },
    {
        "slug": "john-wesley-24804ca0",
        "text": "God justifieth not the godly, but the ungodly; not those that are holy already, but the unholy.",
        "chapter": ("sermons-on-several-occasions", 6),
        "paragraph": 27,
    },
    {
        "slug": "john-wesley-a392c43e",
        "text": "Christ indeed cannot reign, where sin reigns; neither will he dwell where any sin is allowed.",
        "chapter": ("sermons-on-several-occasions", 14),
        "paragraph": 26,
    },
    {
        "slug": "john-wesley-fbb70206",
        "text": "Abhor sin far more than death or hell; abhor sin itself, far more than the punishment of it.",
        "chapter": ("sermons-on-several-occasions", 35),
        "paragraph": 49,
    },
    {
        "slug": "john-wesley-2ea5c1d3",
        "text": "We think of what we love; but we do not love God; therefore, we think not of him.",
        "chapter": ("sermons-on-several-occasions", 42),
        "paragraph": 12,
    },
    {
        "slug": "john-wesley-1fed3831",
        "text": "With regard to the Most High, man and all the concerns of men are nothing, less than nothing, before Him.",
        "chapter": ("sermons-on-several-occasions", 68),
        "paragraph": 63,
    },
    {
        "slug": "john-wesley-df976f9c",
        "text": "Next to the love of God, there is nothing which Satan so cordially abhors as the love of our neighbour.",
        "chapter": ("sermons-on-several-occasions", 73),
        "paragraph": 30,
    },
    {
        "slug": "john-wesley-c49400e2",
        "text": "You cannot deceive him; for he is infinite wisdom: You cannot fly from him; for he is every where: You cannot bribe him; for he is righteousness itself!",
        "chapter": ("sermons-on-several-occasions", 106),
        "paragraph": 31,
    },
    {
        "slug": "john-wesley-ec09b762",
        "text": "The righteousness of Christ is doubtless necessary for any soul that enters into glory: But so is personal holiness too, for every child of man.",
        "chapter": ("sermons-on-several-occasions", 121),
        "paragraph": 13,
    },
    {
        "slug": "john-wesley-8fc9ccff",
        "text": "Faith worketh by love; faith overcometh the world; faith purifieth the heart; faith, in the smallest measure, removeth mountains.",
        "chapter": ("sermons-on-several-occasions", 130),
        "paragraph": 61,
    },
    {
        "slug": "john-wesley-96fdc970",
        "text": "Christ is not only God above us; which may keep us in awe, but cannot save; but he is Immanuel, God with us, and in us.",
        "chapter": ("sermons-on-several-occasions", 142),
        "paragraph": 25,
    },
    {
        "slug": "john-wesley-cd956c0e",
        "text": "God hath given this honour to love alone: Love is the end of all the commandments of God.",
        "chapter": ("sermons-on-several-occasions", 37),
        "paragraph": 14,
    },
    {
        "slug": "john-wesley-0c62bd4a",
        "text": "May we not be of one heart, though we are not of one opinion?",
        "chapter": ("sermons-on-several-occasions", 40),
        "paragraph": 7,
    },
    {
        "slug": "john-wesley-59d8d274",
        "text": "The body dies when it is separated from the soul; the soul, when it is separated from God.",
        "chapter": ("sermons-on-several-occasions", 46),
        "paragraph": 7,
    },
    {
        "slug": "john-wesley-c8f76836",
        "text": "The love of the creature is changed to the love of the Creator; the love of the world into the love of God.",
        "chapter": ("sermons-on-several-occasions", 84),
        "paragraph": 21,
    },
    {
        "slug": "john-wesley-14f9003f",
        "text": "Whatsoever good is in man, or is done by man, God is the author and doer of it.",
        "chapter": ("sermons-on-several-occasions", 129),
        "paragraph": 12,
    },
    {
        "slug": "john-wesley-8f518f4f",
        "text": "Every child of man is in a thousand mistakes, and is liable to fresh mistakes every moment.",
        "chapter": ("sermons-on-several-occasions", 58),
        "paragraph": 16,
    },
    {
        "slug": "john-wesley-4819ac9b",
        "text": "If you move but one step towards God, you are not as other men are.",
        "chapter": ("sermons-on-several-occasions", 32),
        "paragraph": 27,
    },
    {
        "slug": "john-wesley-168568d9",
        "text": "No man living is entirely destitute of what is vulgarly called natural conscience.",
        "chapter": ("sermons-on-several-occasions", 86),
        "paragraph": 24,
    },
    {
        "slug": "john-wesley-44fac614",
        "text": "As God is love, so man, dwelling in love, dwelt in God, and God in him.",
        "chapter": ("sermons-on-several-occasions", 6),
        "paragraph": 11,
    },
]

GEORGE_MULLER = [
    {
        "slug": "george-muller-5fa461a5",
        "text": "Wherever God has given faith, it is given, among other reasons, for the very purpose of being tried.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 55,
    },
    {
        "slug": "george-muller-6e95f222",
        "text": "Do but stand still in the hour of trial, and you will see the help of God, if you trust in Him.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 53,
    },
    {
        "slug": "george-muller-da2889c3",
        "text": "How great is the blessing which the soul obtains by trusting in God, and by waiting patiently.",
        "chapter": ("answers-to-prayer", 2),
        "paragraph": 11,
    },
    {
        "slug": "george-muller-3c0cd7a5",
        "text": "To this class likewise I desired to show, by a visible proof, that God is unchangeably the same.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 3,
    },
    {
        "slug": "george-muller-71b05b84",
        "text": "Truly, the Lord has wise purposes in allowing us to call so long upon Him for help.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 68,
    },
    {
        "slug": "george-muller-6e80ebdf",
        "text": "Not to believe Him is to make Him both a liar and a perjurer.",
        "chapter": ("answers-to-prayer", 3),
        "paragraph": 157,
    },
    {
        "slug": "george-muller-51145329",
        "text": "Ask God also to enlighten you not merely concerning your state by nature, but especially to reveal the Lord Jesus to your heart.",
        "chapter": ("answers-to-prayer", 3),
        "paragraph": 23,
    },
    {
        "slug": "george-muller-aa940293",
        "text": "Through our natural alienation from God we shrink from Him, and from eternal realities.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 55,
    },
    {
        "slug": "george-muller-0ddfdb70",
        "text": "A flow of joy came into my soul whilst realising thus the unchangeableness of our adorable Lord.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 20,
    },
    {
        "slug": "george-muller-ef40c1e4",
        "text": "God sent Him, that He might bear the punishment, due to us guilty sinners.",
        "chapter": ("answers-to-prayer", 3),
        "paragraph": 23,
    },
    {
        "slug": "george-muller-a1e19e7a",
        "text": "The answer is, believe in the Lord Jesus, trust in Him, depend upon Him alone as it regards the salvation of your soul.",
        "chapter": ("answers-to-prayer", 3),
        "paragraph": 86,
    },
    {
        "slug": "george-muller-5ff82d10",
        "text": "When God gives a spirit of prayer, how easy then to pray!",
        "chapter": ("the-life-of-trust", 12),
        "paragraph": 5,
    },
    {
        "slug": "george-muller-65f3b573",
        "text": "Faith has to do with the word of God,—rests upon the written word of God; but there is no promise that he will pay our debts.",
        "chapter": ("the-life-of-trust", 18),
        "paragraph": 4,
    },
    {
        "slug": "george-muller-4202e1fe",
        "text": "Do but stand still in the hour of trial, and you will see the help of God, if you trust in him.",
        "chapter": ("the-life-of-trust", 17),
        "paragraph": 32,
    },
    {
        "slug": "george-muller-a3309ebd",
        "text": "I do not find the life in connection with this work a trying life, but a very happy one.",
        "chapter": ("the-life-of-trust", 21),
        "paragraph": 34,
    },
    {
        "slug": "george-muller-19668d74",
        "text": "If, after prayer, I feel persuaded that I should, I fix upon it, yet so that I would desire to leave myself open to the Lord to change it if he please.",
        "chapter": ("the-life-of-trust", 7),
        "paragraph": 7,
    },
    {
        "slug": "george-muller-48c5690b",
        "text": "Frequently, too, a fresh answer to prayer, obtained in this way, has been the means of quickening my soul, and filling me with much joy.",
        "chapter": ("the-life-of-trust", 7),
        "paragraph": 32,
    },
    {
        "slug": "george-muller-9ef0f4c9",
        "text": "A hearty desire for the conversion of sinners, and earnest prayer for it to the Lord, is quite scriptural; but it is unscriptural to expect the conversion of the whole world.",
        "chapter": ("the-life-of-trust", 9),
        "paragraph": 5,
    },
    {
        "slug": "george-muller-708ce87e",
        "text": "The lying too long in bed not merely keeps us from giving the most precious part of the day to prayer and meditation, but this sloth leads also to many other evils.",
        "chapter": ("the-life-of-trust", 14),
        "paragraph": 22,
    },
    {
        "slug": "george-muller-a471336a",
        "text": "Truly, we are poorer than ever; but through grace my eyes look not at the empty stores and the empty purse, but to the riches of the Lord only.",
        "chapter": ("the-life-of-trust", 17),
        "paragraph": 12,
    },
    {
        "slug": "george-muller-caed9faa",
        "text": "From my inmost soul I do ascribe it to God alone that he has enabled me to trust in him, and that hitherto he has not suffered my confidence in him to fail.",
        "chapter": ("the-life-of-trust", 17),
        "paragraph": 32,
    },
    {
        "slug": "george-muller-76e31dd8",
        "text": "As the increase of faith is a good gift, it must come from God, and therefore he ought to be asked for this blessing.",
        "chapter": ("the-life-of-trust", 17),
        "paragraph": 33,
    },
    {
        "slug": "george-muller-7716c8c8",
        "text": "Jesus came not to save painted but real sinners; but he has saved us, and will surely make it manifest.",
        "chapter": ("the-life-of-trust", 18),
        "paragraph": 28,
    },
    {
        "slug": "george-muller-46c0a31e",
        "text": "The Lord has indeed manifested his tender care of and his great love towards me in Jesus, in inclining my heart cheerfully to lay all I have hitherto called my own at his feet.",
        "chapter": ("the-life-of-trust", 18),
        "paragraph": 17,
    },
    {
        "slug": "george-muller-ded699a3",
        "text": "In all simplicity have we to tell out our heart before God, and then we have to believe that he will give to us according to our need.",
        "chapter": ("the-life-of-trust", 19),
        "paragraph": 19,
    },
    {
        "slug": "george-muller-74de7829",
        "text": "It is certain that we children of God are so abundantly blessed in Jesus, by the grace of God, that we ought to need no stimulus to good works.",
        "chapter": ("the-life-of-trust", 19),
        "paragraph": 33,
    },
    {
        "slug": "george-muller-a1c9f7be",
        "text": "How I shall be supplied with the means which are yet requisite, and when, I know not; but I am sure that God will help me in his own time and way.",
        "chapter": ("the-life-of-trust", 21),
        "paragraph": 42,
    },
    {
        "slug": "george-muller-dcfed640",
        "text": "A million of tracts may not be the means of converting one single soul; and yet how great, beyond calculation, may be the blessing which results from one single tract.",
        "chapter": ("the-life-of-trust", 25),
        "paragraph": 58,
    },
    {
        "slug": "george-muller-b28e4625",
        "text": "The desires of my heart were, to retain the beloved daughter, if it were the will of God; the means to return her were, to be satisfied with the will of the Lord.",
        "chapter": ("the-life-of-trust", 25),
        "paragraph": 64,
    },
    {
        "slug": "george-muller-ebf7ed77",
        "text": "How good is the Lord to have thus appeared for us, in answer to prayer, and what an encouragement to commit everything to him in prayer!",
        "chapter": ("the-life-of-trust", 8),
        "paragraph": 21,
    },
    {
        "slug": "george-muller-f1d681d8",
        "text": "What a striking confirmation that the Lord will help, though the necessities should increase more and more.",
        "chapter": ("the-life-of-trust", 18),
        "paragraph": 33,
    },
    {
        "slug": "george-muller-dad57ef3",
        "text": "Is it not manifest that it is most precious in every way to depend upon God?",
        "chapter": ("the-life-of-trust", 25),
        "paragraph": 4,
    },
    {
        "slug": "george-muller-2059f3eb",
        "text": "Where should the heart of the disciple of the Lord Jesus be, but in heaven?",
        "chapter": ("the-life-of-trust", 19),
        "paragraph": 8,
    },
    {
        "slug": "george-muller-077854c2",
        "text": "Our motives must be godly: we must not seek any gift of God to consume it upon our lusts.",
        "chapter": ("answers-to-prayer", 3),
        "paragraph": 158,
    },
    {
        "slug": "george-muller-03935dd8",
        "text": "We are straitened in ourselves, and suppose that we are straitened in God.",
        "chapter": ("the-life-of-trust", 3),
        "paragraph": 18,
    },
    {
        "slug": "george-muller-25db2ca7",
        "text": "How great is the blessing which the soul obtains by trusting in God and by waiting patiently.",
        "chapter": ("the-life-of-trust", 21),
        "paragraph": 44,
    },
    {
        "slug": "george-muller-73e19adb",
        "text": "How blessed therefore is it to trust in God, and in him alone, and not in circumstances nor friends!",
        "chapter": ("the-life-of-trust", 23),
        "paragraph": 20,
    },
    {
        "slug": "george-muller-955c302c",
        "text": "How true that word that those that trust in the Lord shall not be confounded!",
        "chapter": ("the-life-of-trust", 22),
        "paragraph": 18,
    },
    {
        "slug": "george-muller-ac311d8d",
        "text": "Do you verily depend upon him alone for the salvation of your soul?",
        "chapter": ("the-life-of-trust", 25),
        "paragraph": 7,
    },
    {
        "slug": "george-muller-06569328",
        "text": "How precious it is, even for this life, to act according to the word of God!",
        "chapter": ("the-life-of-trust", 16),
        "paragraph": 6,
    },
    {
        "slug": "george-muller-37a07bae",
        "text": "Do not men believe that God means what he appears plainly to have asserted?",
        "chapter": ("the-life-of-trust", 3),
        "paragraph": 1,
    },
    {
        "slug": "george-muller-e263c093",
        "text": "The Lord helping us, we would rather suffer privation than contract debts.",
        "chapter": ("the-life-of-trust", 7),
        "paragraph": 36,
    },
    {
        "slug": "george-muller-6a06fd93",
        "text": "The Lord has not laid upon us a burden which is too heavy for us; he is not a hard master.",
        "chapter": ("the-life-of-trust", 11),
        "paragraph": 39,
    },
    {
        "slug": "george-muller-aedac97a",
        "text": "At first, our faith will be tried very little in comparison with what it may be afterwards; for God never lays more upon us than he is willing to enable us to bear.",
        "chapter": ("the-life-of-trust", 17),
        "paragraph": 37,
    },
    {
        "slug": "george-muller-46a167ee",
        "text": "We may therefore profitably meditate, with God’s blessing, though we are ever so weak spiritually; nay, the weaker we are, the more we need meditation for the strengthening of our inner man.",
        "chapter": ("the-life-of-trust", 16),
        "paragraph": 15,
    },
    {
        "slug": "george-muller-80aee326",
        "text": "If the work in which we are engaged is indeed the work of God, then he whose work it is is surely able and willing to provide the means for it.",
        "chapter": ("the-life-of-trust", 18),
        "paragraph": 4,
    },
    {
        "slug": "george-muller-edf32cb6",
        "text": "Remember that the world passeth away, but that the things of God endure forever.",
        "chapter": ("the-life-of-trust", 19),
        "paragraph": 10,
    },
    {
        "slug": "george-muller-5cce5220",
        "text": "Is not that, which alone can make us worthy to receive anything from our Heavenly Father, the righteousness of the Lord Jesus, which is imputed to those who believe in Him?",
        "chapter": ("answers-to-prayer", 3),
        "paragraph": 62,
    },
    {
        "slug": "george-muller-a23700ca",
        "text": "In our natural state we dislike dealing with God alone.",
        "chapter": ("answers-to-prayer", 1),
        "paragraph": 55,
    },
    {
        "slug": "george-muller-d2db737a",
        "text": "Would it have been right to charge God with unfaithfulness?",
        "chapter": ("answers-to-prayer", 2),
        "paragraph": 17,
    },
]

HUDSON_TAYLOR = [
    {
        "slug": "hudson-taylor-0ad5bd76",
        "text": "Union with CHRIST, and abiding in CHRIST, what do they not secure?",
        "chapter": ("union-and-communion", 3),
        "paragraph": 1,
    },
    {
        "slug": "hudson-taylor-cad7f3ed",
        "text": "Despite all the unworthy fears of our poor hearts, Divine love is destined to conquer.",
        "chapter": ("union-and-communion", 4),
        "paragraph": 11,
    },
    {
        "slug": "hudson-taylor-38d234ec",
        "text": "To the soul really rescued by grace, no bribe to forsake GOD’S love will be finally successful.",
        "chapter": ("union-and-communion", 9),
        "paragraph": 33,
    },
    {
        "slug": "hudson-taylor-2d3e6a96",
        "text": "The sin of neglected communion may be forgiven, and yet the effect remain permanently; as wounds when healed often leave a scar behind.",
        "chapter": ("union-and-communion", 4),
        "paragraph": 36,
    },
    {
        "slug": "hudson-taylor-042ae2a5",
        "text": "The love that has made her what she is, and now takes delight in her, is not a fickle love, nor need she fear its change.",
        "chapter": ("union-and-communion", 9),
        "paragraph": 17,
    },
    {
        "slug": "hudson-taylor-3303adbe",
        "text": "No longer her own, heart-rest is alike her right and her enjoyment; and so the Bridegroom would have it.",
        "chapter": ("union-and-communion", 4),
        "paragraph": 108,
    },
    {
        "slug": "hudson-taylor-b7ada31d",
        "text": "Grace has made her like the palm-tree, the emblem alike of uprightness and of fruitfulness.",
        "chapter": ("union-and-communion", 8),
        "paragraph": 25,
    },
    {
        "slug": "hudson-taylor-b091a3fb",
        "text": "Do we sufficiently cultivate this unselfish desire to be all for JESUS, and to do all for His pleasure?",
        "chapter": ("union-and-communion", 6),
        "paragraph": 32,
    },
    {
        "slug": "hudson-taylor-fab4ab06",
        "text": "How wondrous the grace that has made the bride of CHRIST to be all this to her Beloved!",
        "chapter": ("union-and-communion", 8),
        "paragraph": 73,
    },
    {
        "slug": "hudson-taylor-07ddeeeb",
        "text": "The world can never be to her what it once was; the betrothed bride has learnt to love her LORD, and no other society than His can satisfy her.",
        "chapter": ("union-and-communion", 4),
        "paragraph": 5,
    },
    {
        "slug": "hudson-taylor-5e3c78b3",
        "text": "As the Spirit reveals Christ, so does Christ bestow the Spirit; and by faith in Christ and in His Word we appropriate the gift.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 60,
    },
    {
        "slug": "hudson-taylor-a656aebe",
        "text": "Many there are who fail to see that there can be but one lord, and that those who do not make God Lord of all do not make Him Lord at all.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 8,
    },
    {
        "slug": "hudson-taylor-e1f8b629",
        "text": "The good works of the unsaved may indeed benefit their fellow-creatures; but until life in Christ has been received, they cannot please God.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 23,
    },
    {
        "slug": "hudson-taylor-a1356158",
        "text": "We do not estimate our love-gifts by their intrinsic value, but rather by the love they express.",
        "chapter": ("separation-and-service", 4),
        "paragraph": 18,
    },
    {
        "slug": "hudson-taylor-037c4f21",
        "text": "The highest service demands the greatest sacrifice, but it secures the fullest blessing and the greatest fruitfulness.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 12,
    },
    {
        "slug": "hudson-taylor-6fa59319",
        "text": "Many a believer to whom Christ has left peace, knows little of it; but those who are filled with the Spirit are filled with peace.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 58,
    },
    {
        "slug": "hudson-taylor-dac18fb3",
        "text": "It was one of the objects of our Saviour's mission to reveal to us that, in Christ Jesus, God is also our Father.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 28,
    },
    {
        "slug": "hudson-taylor-d7a46992",
        "text": "It may be that we have separated ourselves to carry out our own will, or thought, or plan of service, instead of surrendering ourselves and our will, to learn and to do His will.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 4,
    },
    {
        "slug": "hudson-taylor-d4f6ede5",
        "text": "The little one's heart is full; and the mother's heart is also full; but her capacity is greater, and so her joy is deeper.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 14,
    },
    {
        "slug": "hudson-taylor-09cb8768",
        "text": "The Brightness of His Father's glory, the Sun of Righteousness, He came to manifest, as well as to speak of, the Father's love.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 35,
    },
    {
        "slug": "hudson-taylor-1f25798f",
        "text": "How much of prayer there is that begins and ends with the creature, forgetful of the privilege of giving joy to the Creator!",
        "chapter": ("union-and-communion", 6),
        "paragraph": 32,
    },
    {
        "slug": "hudson-taylor-fca298ba",
        "text": "Man's heart is so darkened by the Fall, and by personal sinfulness, that otherwise he would regard sin as a very small matter.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 28,
    },
    {
        "slug": "hudson-taylor-d51cda35",
        "text": "Nearness to God calls for tenderness of conscience, thoughtfulness in service, and implicit obedience.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 33,
    },
    {
        "slug": "hudson-taylor-a6c81b90",
        "text": "The burnt-offering tells us of the perfect and accepted righteousness of Christ, in virtue of which the imperfect believer and his imperfect service are accepted by God.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 68,
    },
    {
        "slug": "hudson-taylor-4257638e",
        "text": "When the Lord blesses His people with peace and plenty, it is His open Heart that moves His loving Hand.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 12,
    },
    {
        "slug": "hudson-taylor-292a6824",
        "text": "The Bible is a supernatural book, a divine revelation: the Holy Spirit is the supernatural, the divine Guide to its meaning.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 49,
    },
    {
        "slug": "hudson-taylor-61a35270",
        "text": "The Holy Spirit is the other Comforter, sent by the Father in Christ's name, that He might abide with the Church for ever.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 54,
    },
    {
        "slug": "hudson-taylor-b1a3a6a3",
        "text": "When sin is put away the Spirit again lifts up His countenance upon us, and peace fills the heart.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 56,
    },
    {
        "slug": "hudson-taylor-c92c5138",
        "text": "God is not hard to please, nor is true human love, for it is a dim reflection of His own.",
        "chapter": ("separation-and-service", 4),
        "paragraph": 18,
    },
    {
        "slug": "hudson-taylor-6659df97",
        "text": "When the Lord Jesus comes again, those, surely, who have stored most in heaven, and have least to leave behind on earth, will render their account with the greatest joy.",
        "chapter": ("separation-and-service", 4),
        "paragraph": 27,
    },
    {
        "slug": "hudson-taylor-34852374",
        "text": "Though we are not our own, it is, alas! possible to live as though we were; devotion to God is still a voluntary thing; hence the differences of attainment among Christians.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 5,
    },
    {
        "slug": "hudson-taylor-10b13faf",
        "text": "Our true self-denial, self-emptying, and giving for Christ's cause practically show our real estimate of the value of the Cross of Christ, our real love for the Christ who was crucified for us.",
        "chapter": ("separation-and-service", 4),
        "paragraph": 65,
    },
    {
        "slug": "hudson-taylor-7ac514c2",
        "text": "Thanks be to God, the illumination of the HOLY GHOST is promised to all who seek for it: what more can we desire?",
        "chapter": ("union-and-communion", 2),
        "paragraph": 1,
    },
    {
        "slug": "hudson-taylor-59c25747",
        "text": "The GOD of the Bible is a GOD who punishes sin, and cannot pardon without atonement.",
        "sermon": "under-the-shepherds-care",
        "paragraph": 2,
    },
    {
        "slug": "hudson-taylor-f8d18af3",
        "text": "Oh, it is sweet to live thus directly dependent upon the Lord, who never fails us!",
        "chapter": ("a-retrospect", 16),
        "paragraph": 6,
    },
    {
        "slug": "hudson-taylor-9e37f8aa",
        "text": "Sometimes we have trials which we cannot put into prayer; the LORD knows the secrets of our heart.",
        "sermon": "under-the-shepherds-care",
        "paragraph": 13,
    },
    {
        "slug": "hudson-taylor-d8fd45a2",
        "text": "If we are faithful to God in little things, we shall gain experience and strength that will be helpful to us in the more serious trials of life.",
        "chapter": ("a-retrospect", 3),
        "paragraph": 12,
    },
    {
        "slug": "hudson-taylor-4d77cbd9",
        "text": "The peace, which we can neither make nor keep, will itself, as a garrison, keep and protect us, and the cares and worries will strive to enter in vain.",
        "sermon": "blessed-adversity",
        "paragraph": 13,
    },
    {
        "slug": "hudson-taylor-a0b9c9a7",
        "text": "The habit of coming in faith to Him is incompatible with unmet hunger and thirst.",
        "sermon": "unfailing-springs",
        "paragraph": 13,
    },
    {
        "slug": "hudson-taylor-8f87ae30",
        "text": "GOD'S overflow more than supplies the lack of individual capacity.",
        "sermon": "unfailing-springs",
        "paragraph": 14,
    },
    {
        "slug": "hudson-taylor-cdcd2da5",
        "text": "If the whole resources of the Church of God were well utilised, how much more might be accomplished!",
        "chapter": ("a-retrospect", 2),
        "paragraph": 13,
    },
    {
        "slug": "hudson-taylor-a2017a32",
        "text": "To many minds there is the greatest shrinking from appearing peculiar; but God would often have His people unmistakably peculiar.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 15,
    },
    {
        "slug": "hudson-taylor-2dd2dd38",
        "text": "Where there is fitness for the work, the way will probably be made plain after a time of patient waiting.",
        "chapter": ("separation-and-service", 2),
        "paragraph": 22,
    },
    {
        "slug": "hudson-taylor-68ec7c26",
        "text": "Our love to GOD is secured by GOD’S love to us.",
        "chapter": ("union-and-communion", 9),
        "paragraph": 33,
    },
    {
        "slug": "hudson-taylor-a5415bca",
        "text": "We have to take our choice: we cannot enjoy both the world and CHRIST.",
        "chapter": ("union-and-communion", 5),
        "paragraph": 15,
    },
    {
        "slug": "hudson-taylor-5ac0c4d8",
        "text": "Where that blessing is not enjoyed, there is always something unreal or defective in the consecration.",
        "chapter": ("separation-and-service", 3),
        "paragraph": 4,
    },
    {
        "slug": "hudson-taylor-d414362d",
        "text": "Dangers seen sometimes appal us, or appal those who love us: but they are not more real than many we never dream of.",
        "sermon": "all-sufficiency",
        "paragraph": 4,
    },
    {
        "slug": "hudson-taylor-938e0682",
        "text": "We are not to think that our holiest service is free from sin, or can be accepted save through JESUS CHRIST our LORD.",
        "sermon": "a-ribband-of-blue",
        "paragraph": 6,
    },
    {
        "slug": "hudson-taylor-14428932",
        "text": "Self-will is unmingled folly, and can only end in injury and loss.",
        "sermon": "all-sufficiency",
        "paragraph": 3,
    },
    {
        "slug": "hudson-taylor-a1d67b37",
        "text": "Self-denial surely means something far greater than some slight insignificant lessening of our self-indulgences!",
        "sermon": "self-denial-versus-self-assertion",
        "paragraph": 3,
    },
    {
        "slug": "hudson-taylor-6356623c",
        "text": "Every true minister of GOD, every true missionary, every true Sunday-school teacher and Christian worker is a faith-worker.",
        "sermon": "a-full-reward",
        "paragraph": 8,
    },
    {
        "slug": "hudson-taylor-b6346059",
        "text": "The child of GOD has no need of the counsel of the ungodly; if he love and study GOD'S Word it will make him wiser than all such counsellors.",
        "sermon": "blessed-prosperity",
        "paragraph": 11,
    },
]

GARETH_EVANS = [
    {
        "slug": "gareth-evans-acd8fcf2",
        "text": "God has not called us to be famous or successful; He has called us to be faithful.",
        "chapter": ("he-holds-my-tomorrows", 15),
        "paragraph": 16,
    },
    {
        "slug": "gareth-evans-250ffc80",
        "text": "Faith does not deliver us from the chisel or hammer of the Divine sculptor.",
        "chapter": ("he-holds-my-tomorrows", 16),
        "paragraph": 45,
    },
    {
        "slug": "gareth-evans-7bf997cc",
        "text": "The only thing He requires of you is your love, and that cannot be forced from you.",
        "chapter": ("he-holds-my-tomorrows", 17),
        "paragraph": 25,
    },
    {
        "slug": "gareth-evans-ea56a35e",
        "text": "The great promises of God only come to those who have died to themselves.",
        "chapter": ("he-holds-my-tomorrows", 12),
        "paragraph": 28,
    },
    {
        "slug": "gareth-evans-8f7e4023",
        "text": "The faith that pleases God is not evidenced in the obedience of fear, but in the obedience of love and willingness.",
        "chapter": ("he-holds-my-tomorrows", 5),
        "paragraph": 19,
    },
    {
        "slug": "gareth-evans-0b4a12e9",
        "text": "Faith is an attribute of the heart and is evidenced in obedience.",
        "chapter": ("he-holds-my-tomorrows", 2),
        "paragraph": 40,
    },
    {
        "slug": "gareth-evans-c9e0110e",
        "text": "Faith does not need a man to understand and believe; it needs anyone who will obey, even when he does not understand or believe!",
        "chapter": ("he-holds-my-tomorrows", 17),
        "paragraph": 9,
    },
    {
        "slug": "gareth-evans-c17f1706",
        "text": "Jesus did not die to give us a crutch - he died that we might be made whole!",
        "chapter": ("soar-like-the-eagle-3", 2),
        "paragraph": 20,
    },
    {
        "slug": "gareth-evans-73429902",
        "text": "God never counts us as a failure if we do not pass His present testing.",
        "chapter": ("he-holds-my-tomorrows", 13),
        "paragraph": 10,
    },
    {
        "slug": "gareth-evans-5229253d",
        "text": "God only allows testing to come in our lives so that He might make us pure.",
        "chapter": ("he-holds-my-tomorrows", 13),
        "paragraph": 26,
    },
    {
        "slug": "gareth-evans-5df533df",
        "text": "God knows the heart of man and will only reveal Himself to those who are pure in heart.",
        "chapter": ("he-holds-my-tomorrows", 7),
        "paragraph": 41,
    },
    {
        "slug": "gareth-evans-cf0d0a61",
        "text": "The only way man can approach God is through the shed blood of a lamb.",
        "chapter": ("he-holds-my-tomorrows", 7),
        "paragraph": 31,
    },
    {
        "slug": "gareth-evans-b4cd492e",
        "text": "To every weapon of Satan they have an answer in the Word of God.",
        "chapter": ("feasting-at-the-table", 9),
        "paragraph": 9,
    },
    {
        "slug": "gareth-evans-732b3ef4",
        "text": "The Lord’s priority is not just the healing, which blesses you, but the reconciliation which blesses Him!",
        "chapter": ("the-key-in-my-hand", 15),
        "paragraph": 44,
    },
    {
        "slug": "gareth-evans-6a4f8972",
        "text": "Jesus pointed out to them that it was faith they needed, not belief.",
        "chapter": ("he-holds-my-tomorrows", 2),
        "paragraph": 13,
    },
    {
        "slug": "gareth-evans-d75fc266",
        "text": "God is always willing to reveal more of Himself to the one who is an overcomer when faced with the tests of life.",
        "chapter": ("feasting-at-the-table", 1),
        "paragraph": 4,
    },
    {
        "slug": "gareth-evans-04db311b",
        "text": "Jesus said that He did not come to be served but to serve - and He expects the same from His disciples.",
        "chapter": ("soar-like-the-eagle-3", 4),
        "paragraph": 13,
    },
    {
        "slug": "gareth-evans-dc3ec2c5",
        "text": "The gifts are given to individuals, not that they might glory or boast in them, but that they might be for the benefit of all.",
        "chapter": ("he-holds-my-tomorrows", 3),
        "paragraph": 68,
    },
    {
        "slug": "gareth-evans-7f44b4a6",
        "text": "The child does not experience the love whose fruit is security, identity, self-esteem, acceptance, and encouragement.",
        "chapter": ("the-key-in-my-hand", 6),
        "paragraph": 9,
    },
    {
        "slug": "gareth-evans-12a18c7e",
        "text": "To those who have placed their trust in the finished work of Calvary, there is no more condemnation but an access into the presence and fellowship of God.",
        "chapter": ("he-holds-my-tomorrows", 7),
        "paragraph": 34,
    },
    {
        "slug": "gareth-evans-eece1b59",
        "text": "The last prayer of Jesus for all who would come to believe Him, is that we may be ONE.",
        "chapter": ("feasting-at-the-table", 4),
        "paragraph": 5,
    },
    {
        "slug": "gareth-evans-cd926d0d",
        "text": "The end of the journey for all who walk in faith, is that they shall be with their Saviour, glorified in His presence.",
        "chapter": ("he-holds-my-tomorrows", 16),
        "paragraph": 39,
    },
    {
        "slug": "gareth-evans-5c0753d7",
        "text": "The ministry is built on their charisma or business acumen, rather than on the charismata and unction of God.",
        "chapter": ("soar-like-the-eagle-3", 9),
        "paragraph": 7,
    },
    {
        "slug": "gareth-evans-12ac9d3d",
        "text": "The eagle does not rest until it sees its offspring rise to soar above all the other birds in the vast expanse of the heavens.",
        "chapter": ("soar-like-the-eagle-3", 1),
        "paragraph": 33,
    },
    {
        "slug": "gareth-evans-90d08e5c",
        "text": "A sure way to stop the Lord moving in miraculous ways in your life, is to take offense.",
        "chapter": ("the-key-in-my-hand", 8),
        "paragraph": 27,
    },
    {
        "slug": "gareth-evans-531d812b",
        "text": "Jesus washed the feet of Judas knowing all that was in his heart.",
        "chapter": ("the-key-in-my-hand", 3),
        "paragraph": 29,
    },
]

#: Richard Allen — 6 quotations from his autobiography (the antislavery
#: address to slaveholders and his address on Christian charity).
RICHARD_ALLEN = [
    {
        "slug": "richard-allen-33f14308",
        "text": "We wish you to consider, that God himself was the first pleader of the cause of slaves.",
        "chapter": ("life-experience-gospel-labours", 9),
        "paragraph": 3,
    },
    {
        "slug": "richard-allen-55587960",
        "text": "Consider, my brethren, that all we have and are is entrusted to us by Almighty God.",
        "chapter": ("life-experience-gospel-labours", 11),
        "paragraph": 16,
    },
    {
        "slug": "richard-allen-79563ce8",
        "text": "Our blessed Lord has not committed his goods to us as a dead stock, to be boarded up, or to lie unprofitably in our own hands.",
        "chapter": ("life-experience-gospel-labours", 11),
        "paragraph": 17,
    },
    {
        "slug": "richard-allen-83c101e1",
        "text": "In short, the love of this world is a heavy weight upon the soul, which chains her down, and prevents her flight towards heaven.",
        "chapter": ("life-experience-gospel-labours", 11),
        "paragraph": 25,
    },
    {
        "slug": "richard-allen-31ab9496",
        "text": "To be slow and uneasy at almsgiving, argues a strong distrust in providence, either that God cannot or will not make up to us what we thus bestow.",
        "chapter": ("life-experience-gospel-labours", 11),
        "paragraph": 28,
    },
    {
        "slug": "richard-allen-009d57ea",
        "text": "All objections to charitable contributions may well be supposed to arise from covetousness, or an unwillingness to part with the present penny.",
        "chapter": ("life-experience-gospel-labours", 11),
        "paragraph": 33,
    },
]

#: Amanda Berry Smith — 15 quotations from her Autobiography (faith,
#: sanctification, prayer, trust, and temperance).
AMANDA_BERRY_SMITH = [
    {
        "slug": "amanda-berry-smith-a27a891a",
        "text": "In my heart was peace, but I did not know how to exercise faith as I should.",
        "chapter": ("amanda-smith-autobiography", 4),
        "paragraph": 12,
    },
    {
        "slug": "amanda-berry-smith-6ba0da7f",
        "text": "Thank God for real, practical, inright, outright, downright common sense; that is all I think people need on the color line.",
        "chapter": ("amanda-smith-autobiography", 6),
        "paragraph": 2,
    },
    {
        "slug": "amanda-berry-smith-d3999568",
        "text": "What else ought we to do, when we bring our friends, but to sink into the will of God, and put them into His hands, and trust Him?",
        "chapter": ("amanda-smith-autobiography", 8),
        "paragraph": 45,
    },
    {
        "slug": "amanda-berry-smith-c5cbc2c8",
        "text": "How often when we are passing through deep trials we look for human sympathy, and lean on the human more than on God.",
        "chapter": ("amanda-smith-autobiography", 8),
        "paragraph": 59,
    },
    {
        "slug": "amanda-berry-smith-3649ad8b",
        "text": "Learn to know the beauty of love and power and sympathy of Jesus Christ, our Lord and Savior.",
        "chapter": ("amanda-smith-autobiography", 10),
        "paragraph": 33,
    },
    {
        "slug": "amanda-berry-smith-e93eed38",
        "text": "The Gospel of Jesus was so full and practical, and with good, common sense it seemed to cover all my need.",
        "chapter": ("amanda-smith-autobiography", 10),
        "paragraph": 33,
    },
    {
        "slug": "amanda-berry-smith-3fe22a05",
        "text": "How glad I am that God nowhere teaches that men have to go into filth and indolence in order to be holy.",
        "chapter": ("amanda-smith-autobiography", 24),
        "paragraph": 18,
    },
    {
        "slug": "amanda-berry-smith-a0c1cb51",
        "text": "God gives us His Spirit, but we must walk in the light of the Spirit; then we will not fulfill the lust of the flesh, going in our own way.",
        "chapter": ("amanda-smith-autobiography", 24),
        "paragraph": 33,
    },
    {
        "slug": "amanda-berry-smith-a6a638e8",
        "text": "Strong drink does not only destroy the soul and body of men, but robs them of every comfort of life.",
        "chapter": ("amanda-smith-autobiography", 27),
        "paragraph": 113,
    },
    {
        "slug": "amanda-berry-smith-f22720ef",
        "text": "The very best chance for growing in grace, really and successfully, is to get the cleansing and all obstruction to growth out.",
        "chapter": ("amanda-smith-autobiography", 34),
        "paragraph": 132,
    },
    {
        "slug": "amanda-berry-smith-6316c853",
        "text": "How I do thank the Lord when it is my privilege to sing and pray and cheer the weary traveler along the lonesome road.",
        "chapter": ("amanda-smith-autobiography", 28),
        "paragraph": 108,
    },
    {
        "slug": "amanda-berry-smith-a8ab3c92",
        "text": "God was to separate me unto Himself and I must be weaned.",
        "chapter": ("amanda-smith-autobiography", 13),
        "paragraph": 23,
    },
    {
        "slug": "amanda-berry-smith-7de9680d",
        "text": "The burden rolled away; I felt it when it left me, and a flood of light and joy swept through my soul such as I had never known before.",
        "chapter": ("amanda-smith-autobiography", 6),
        "paragraph": 48,
    },
    {
        "slug": "amanda-berry-smith-cf826ddb",
        "text": "God showed me I was a dreadful sinner, but still I wanted to have my own way about it.",
        "chapter": ("amanda-smith-autobiography", 6),
        "paragraph": 17,
    },
    {
        "slug": "amanda-berry-smith-afbc34b8",
        "text": "How I have lived through it I cannot tell, but the blessedness of the love and the peace and power I can never describe.",
        "chapter": ("amanda-smith-autobiography", 9),
        "paragraph": 32,
    },
]

QUOTES = {
    "charles-h-spurgeon": SPURGEON,
    "thomas-a-kempis": THOMAS_A_KEMPIS,
    "andrew-murray": ANDREW_MURRAY,
    "e-m-bounds": E_M_BOUNDS,
    "augustine-of-hippo": AUGUSTINE,
    "jonathan-edwards": JONATHAN_EDWARDS,
    "john-wesley": JOHN_WESLEY,
    "george-muller": GEORGE_MULLER,
    "hudson-taylor": HUDSON_TAYLOR,
    "gareth-evans": GARETH_EVANS,
    "richard-allen": RICHARD_ALLEN,
    "amanda-berry-smith": AMANDA_BERRY_SMITH,
}


#: Which quotations are filed under each theme — what powers the "Quotes on
#: Prayer" pages and their per-author children. Grouped BY topic (with the
#: sentence echoed in a trailing comment) so a reviewer sees a whole theme at
#: once; `seed_quotes` inverts it onto `Quote.topics`.
#:
#: This is a KEYWORD-ASSISTED FIRST PASS, not a hand-read of every line: a
#: lexicon per theme shortlisted candidates and a person trims. Filing is lower-
#: stakes than the quotation itself (a well-sourced line under a loosely-related
#: theme is imperfect curation, not a misquotation), and the pages still show
#: only REVIEWED quotes. Refine a theme with the quote-extraction skill; the PR
#: review is the sign-off, as it is for the quotes themselves. Re-asserted every
#: deploy (NOT create-only) — a re-tag ships.

TOPIC_MEMBERS = {
    "prayer": [  # Prayer
        "charles-h-spurgeon-ddf56c92",  # Jesus is exalted on high, that through the virtue of His int
        "charles-h-spurgeon-e96bbdf6",  # God give us to be much in the holy art of arguing with God i
        "charles-h-spurgeon-813295f9",  # The Lord give you large mouths in prayer, great potency, not
        "charles-h-spurgeon-22f0858c",  # One prayer coming from the soul is better than a myriad cold
        "charles-h-spurgeon-f259f382",  # God’s Spirit is teaching you how to wrestle and agonize in p
        "charles-h-spurgeon-4b7afe02",  # The prayer that this morning you offered, Christ is now offe
        "charles-h-spurgeon-0a553264",  # The Lord Jesus has led captivity captive, and now sits at th
        "andrew-murray-7bc3e383",  # The knowledge of God's Father love is the first and simplest
        "andrew-murray-4e3ad077",  # Let us beware of the prayer for forgiveness becoming a forma
        "andrew-murray-7f00de09",  # Christ’s life and work, His suffering and death—it was all p
        "andrew-murray-ceef792c",  # It is the life abiding wholly in Christ that can pray the ef
        "andrew-murray-be6e77d9",  # Intercession is the most perfect form of prayer: it is the p
        "andrew-murray-75191679",  # Throughout Scripture, in the life of every saint, of God’s o
        "andrew-murray-13b9ac31",  # It is the branch-life, existing solely for the Vine, that wi
        "andrew-murray-def0eaf2",  # The life of abiding and obedience, of love and joy, of clean
        "andrew-murray-716ef8a0",  # To be a branch means not only bearing fruit on earth, but po
        "e-m-bounds-b174257b",  # Christ holds Himself ready to supply exactly, and fully, all
        "e-m-bounds-6b8891e3",  # Nothing distinguishes the children of God so clearly and str
        "e-m-bounds-49d3b925",  # Nothing is too hard for prayer because nothing is too hard f
        "e-m-bounds-52b568c0",  # The story of every great Christian achievement is the histor
        "e-m-bounds-6e68a441",  # No person is a soul-winner who is not an adept in the minist
        "e-m-bounds-1f61d2a7",  # The closet cannot be made holy to God when the life has not 
        "e-m-bounds-456fba5b",  # Prayer is mighty in its operations, and God never disappoint
        "e-m-bounds-b26355f0",  # Every revival of which we have any record has been bathed in
        "e-m-bounds-38b0ca28",  # Faith in Christ is the basis of all working, and of all pray
        "e-m-bounds-d44f9cee",  # To see God, to know God, and to live for God -- these form t
        "e-m-bounds-ab7864b0",  # The difficulty in prayer is not with faith, but with obedien
        "e-m-bounds-7894b850",  # No man can pray -- really pray -- who does not obey.
        "e-m-bounds-ca009ef5",  # The will must be surrendered to God as a primary condition o
        "e-m-bounds-aac43fc2",  # Prayer is not simply to get things from God, but to make tho
        "e-m-bounds-054f2705",  # The number and efficiency of the labourers in God’s vineyard
        "e-m-bounds-01f9f8d8",  # Prayer is not a mere form of words; it is not just calling u
        "e-m-bounds-af08081e",  # The one prominent characteristic of the experience into whic
        "e-m-bounds-da0bf2bc",  # To do God's will without demur, is the joy as it is the priv
        "e-m-bounds-2b2db6e0",  # The Christian soldier is to pray at all seasons, and under a
        "e-m-bounds-aaca3882",  # The entire life of a Christian soldier -- its being, intenti
        "e-m-bounds-019df67e",  # God is so concerned that men pray that He has promised to an
        "e-m-bounds-5c98ee06",  # Prayer is the seeking of God’s great and greatest good, whic
        "e-m-bounds-fa8348c7",  # Prayer is the child’s request, not to the winds nor to the w
        "e-m-bounds-81aa80b3",  # Prayer is God’s plan to supply man’s great and continuous ne
        "e-m-bounds-31dfd977",  # God has everything to do with prayer, as well as everything 
        "e-m-bounds-cac9217a",  # God’s Gospel has always waited more on prayer than on anythi
        "e-m-bounds-eaa3a1c9",  # Prayer is the only element in which the Holy Spirit can live
        "e-m-bounds-b95b2a8f",  # Jesus Christ was always a busy man with His work, but never 
        "e-m-bounds-3aad54a5",  # Prayer does not interpret God’s providences, but it does jus
        "e-m-bounds-7b379a07",  # Prayer without fervour is as a sun without light or heat, or
        "e-m-bounds-20b5210a",  # God can afford to commit Himself in prayer to those who have
        "e-m-bounds-1ce791ff",  # Prayer holds earth to heaven and brings heaven in close cont
        "e-m-bounds-3de95408",  # Prayer is intended for all men, because all men need God and
        "e-m-bounds-552c19f1",  # Prayer so prepares the heart that it softens under the disci
        "e-m-bounds-55b9917c",  # The prayer life is the direct fruit of entire consecration t
        "e-m-bounds-4d0e283e",  # God wants consecrated men because they can pray and will pra
        "e-m-bounds-ec80b3c8",  # Prayer promotes the spirit of devotion, while devotion is fa
        "e-m-bounds-ad66c674",  # Prayer is natural and almost spontaneous when compassion is 
        "e-m-bounds-132bf8cd",  # The prayer is made to God and the issue is with God.
        "e-m-bounds-541d3401",  # God’s people were always safe when their princes were prince
        "e-m-bounds-f89a467a",  # Nothing is clearer than that prayer has its only worth and s
        "e-m-bounds-bb90e88c",  # Prayer breaks all bars, dissolves all chains, opens all pris
        "e-m-bounds-d8c4a388",  # Prayer unites with the purposes of God and lays itself out t
        "e-m-bounds-d3d581c6",  # Prayer makes the man; prayer makes the preacher; prayer make
        "e-m-bounds-d4c5d477",  # Prayer puts the preacher’s heart into the preacher’s sermon;
        "e-m-bounds-d464b8c2",  # God’s true preachers have been distinguished by one great fe
        "e-m-bounds-b99a6740",  # Prayer which is felt as a mighty force is the mediate or imm
        "john-wesley-8c6200bd",  # Prayer is the lifting up of the heart to God: All words of p
        "john-wesley-27045827",  # Every new victory which a soul gains is the effect of a new 
        "john-wesley-14ab445e",  # Every action of a Christian that is good, is sanctified by t
        "george-muller-5ff82d10",  # When God gives a spirit of prayer, how easy then to pray!
        "george-muller-19668d74",  # If, after prayer, I feel persuaded that I should, I fix upon
        "george-muller-48c5690b",  # Frequently, too, a fresh answer to prayer, obtained in this 
        "george-muller-9ef0f4c9",  # A hearty desire for the conversion of sinners, and earnest p
        "george-muller-708ce87e",  # The lying too long in bed not merely keeps us from giving th
        "george-muller-ebf7ed77",  # How good is the Lord to have thus appeared for us, in answer
        "hudson-taylor-1f25798f",  # How much of prayer there is that begins and ends with the cr
        "gareth-evans-eece1b59",  # The last prayer of Jesus for all who would come to believe H
        "amanda-berry-smith-6316c853",  # How I do thank the Lord when it is my privilege to sing and 
        "augustine-of-hippo-1699c301",  # Thou light of my heart, Thou bread of my inmost soul, T
        "augustine-of-hippo-c006d51a",  # I call upon Thee, O my God, my mercy, Who createdst me,
        "augustine-of-hippo-4db0559b",  # O let the Light, the Truth, the Light of my heart, not
        "hudson-taylor-9e37f8aa",  # Sometimes we have trials which we cannot put into praye
        "george-muller-077854c2",  # Our motives must be godly: we must not seek any gift of 
        "george-muller-a23700ca",  # In our natural state we dislike dealing with God alone.
        "andrew-murray-f1456932",  # The child who only wants to know the love of the father when
        "andrew-murray-21b2f5b3",  # Our prayers must not be a vague appeal to His mercy, an inde
        "andrew-murray-3f9c18d7",  # In one aspect there must be faith before there can be prayer
        "andrew-murray-363d5b2b",  # Faith in the promise is the fruit of faith in the promiser: 
        "andrew-murray-20f246b8",  # A heart full of God has power for the prayer of faith.
        "andrew-murray-3f0a513b",  # Not according to what I try to be when praying, but what I a
        "andrew-murray-b8b0d6bf",  # A prayer meeting without recognised answer to prayer ought t
        "andrew-murray-8f923be4",  # God will not delay one moment longer than is absolutely nece
        "andrew-murray-9a33edf0",  # Man was created, and has now again been redeemed, to pray, a
        "andrew-murray-377c0454",  # Give yourself, and live, to do the works of Christ and you w
        "andrew-murray-6862a329",  # The name and the power of asking go together: when the Name 
        "andrew-murray-022ae1f5",  # To pray in the Name of Jesus is to pray in unity, in sympath
        "andrew-murray-2196a38c",  # Every believer ought to pray much that the unity of the Chur
        "andrew-murray-ac9e4831",  # Our priestly power with God depends on our personal life and
        "andrew-murray-7d56611c",  # God needs, greatly needs, priests who can draw near to Him, 
        "andrew-murray-0865b7b0",  # Christ is all, the life and the strength too for a never-cea
        "andrew-murray-b1464290",  # Not in God, not in His secret will, not in the limitations o
    ],
    "faith": [  # Faith
        "charles-h-spurgeon-94833965",  # The righteousness of faith is not the moral excellence of fa
        "charles-h-spurgeon-91fc01a4",  # The Lord's salvation can come to us though we have only fait
        "charles-h-spurgeon-a4fd540c",  # Faith which refuses to obey the commands of the Saviour is a
        "charles-h-spurgeon-5096795d",  # Faith is as much the gift of God as is the Saviour upon whom
        "charles-h-spurgeon-1f40aadf",  # Christ and the believing sinner are in the same boat: unless
        "charles-h-spurgeon-3b972466",  # Faith saves us because it makes us cling to Christ Jesus, an
        "charles-h-spurgeon-f7378bd5",  # Come by faith to Jesus, for without him you perish for ever.
        "charles-h-spurgeon-158e253e",  # Faith is the linen which binds the plaster of Christ's recon
        "charles-h-spurgeon-b0f71ee3",  # Come to Jesus, by quitting every other hope, by thinking of 
        "charles-h-spurgeon-cd259808",  # Our faithful God will never run back from His word, nor will
        "charles-h-spurgeon-cb6b8059",  # Not for confession, nor for reformation, but in connection w
        "charles-h-spurgeon-3eea1a98",  # Believe in the Lord Jesus Christ, and you, even you, will be
        "charles-h-spurgeon-92fc517e",  # Whether faith is large or small, whether you can do much or 
        "charles-h-spurgeon-c84751da",  # Salvation does not come from the preacher’s authority, but t
        "charles-h-spurgeon-d0fcbb43",  # Christ Jesus is the only escape for a sinner pursued by the 
        "charles-h-spurgeon-c3773b2e",  # Our first business has not to do with faith, but with Christ
        "charles-h-spurgeon-7faf8f59",  # Christ in the heart, means Christ believed in, Christ belove
        "charles-h-spurgeon-ab484f68",  # Little faith will get very great mercies, but great faith st
        "charles-h-spurgeon-36a701d9",  # Faith was Peter's life-buoy—it kept him up; but unbelief sen
        "charles-h-spurgeon-f28139b1",  # Believers are not only to be with Christ, and to behold His 
        "charles-h-spurgeon-57735f38",  # We are saved by faith, and not by feeling; yet there is a re
        "charles-h-spurgeon-f90f1753",  # Little-faith was bought with the blood of Christ; ay, and he
        "charles-h-spurgeon-c96dd1a1",  # The believer enjoys, in favored seasons, such an intimacy wi
        "thomas-a-kempis-b2579c20",  # Faith is required of you, and a sincere life, not a lofty in
        "thomas-a-kempis-8e7b6b00",  # Jesus Christ must be loved alone with a special love for He 
        "andrew-murray-d02a0de2",  # Faith seeks the glory that comes from God, and it only comes
        "andrew-murray-1b021ab8",  # Every believer has the right and calling, to stand in direct
        "andrew-murray-3e731043",  # The part of faith is always to lay hold on just that which a
        "andrew-murray-74ee7679",  # The only means by which this unseen enemy can be conquered i
        "andrew-murray-2097ba81",  # Christ longs to reveal Himself, but He cannot on account of 
        "andrew-murray-3272b680",  # Faith in Jesus is the secret of a holy life: all holy conduc
        "andrew-murray-77a4141f",  # It is the New Life that is the holy life: the full apprehens
        "andrew-murray-71f58011",  # In the beginning of the faith-life, faith is struggling; but
        "andrew-murray-3450b45b",  # Blessed the man who is not staggered by God’s delay, or sile
        "andrew-murray-d736c7c7",  # It was by obedience Christ as Vine honored the Father as Hus
        "e-m-bounds-3b245347",  # Faith does the impossible because it brings God to undertake
        "e-m-bounds-b174257b",  # Christ holds Himself ready to supply exactly, and fully, all
        "e-m-bounds-38b0ca28",  # Faith in Christ is the basis of all working, and of all pray
        "e-m-bounds-170e43be",  # Faith is not an aimless act of the soul, but a looking to Go
        "e-m-bounds-cc849a69",  # Faith is not believing just anything; it is believing God, r
        "e-m-bounds-ab7864b0",  # The difficulty in prayer is not with faith, but with obedien
        "e-m-bounds-af08081e",  # The one prominent characteristic of the experience into whic
        "augustine-of-hippo-f80a2bf6",  # In these two you have those three graces exemplified: faith 
        "augustine-of-hippo-87986dcb",  # The fact that we do not see either what we believe or what w
        "augustine-of-hippo-567e0947",  # No one, of course, is to be condemned as a liar who says wha
        "augustine-of-hippo-daf2b4a0",  # For when there is a question as to whether a man is good, on
        "augustine-of-hippo-e0fb2a79",  # We love God now by faith, then we shall love Him through sig
        "augustine-of-hippo-2c5b7319",  # Now we love even our neighbor by faith; for we who are ourse
        "jonathan-edwards-20cf3293",  # There is not only a rational belief that God is holy and tha
        "jonathan-edwards-f9dba01f",  # Faith abases men and exalts God, it gives all the glory of r
        "jonathan-edwards-053525a7",  # It is God that gives us faith whereby we close with Christ.
        "jonathan-edwards-27f6a365",  # He does not merely rationally believe that God is glorious, 
        "john-wesley-60c79eda",  # Faith is the condition, and the only condition, of sanctific
        "john-wesley-b8fe8d3c",  # The root of all religion is faith, without which it is impos
        "john-wesley-0d8ca0c2",  # The pure love of our neighbour, springing from the love of G
        "john-wesley-69cc6ec9",  # God gives this faith; in that moment we are accepted of God;
        "john-wesley-697ed3cb",  # Reason, however cultivated and improved, cannot produce the 
        "john-wesley-baa7a7a5",  # The foundation is faith, purifying the heart; the end love, 
        "john-wesley-740b7c0e",  # Believe in the Lord Jesus; and thou, even thou, art reconcil
        "george-muller-5fa461a5",  # Wherever God has given faith, it is given, among other reaso
        "george-muller-6e80ebdf",  # Not to believe Him is to make Him both a liar and a perjurer
        "george-muller-a1e19e7a",  # The answer is, believe in the Lord Jesus, trust in Him, depe
        "george-muller-65f3b573",  # Faith has to do with the word of God,—rests upon the written
        "george-muller-76e31dd8",  # As the increase of faith is a good gift, it must come from G
        "george-muller-ded699a3",  # In all simplicity have we to tell out our heart before God, 
        "hudson-taylor-5e3c78b3",  # As the Spirit reveals Christ, so does Christ bestow the Spir
        "hudson-taylor-6fa59319",  # Many a believer to whom Christ has left peace, knows little 
        "hudson-taylor-a6c81b90",  # The burnt-offering tells us of the perfect and accepted righ
        "gareth-evans-acd8fcf2",  # God has not called us to be famous or successful; He has cal
        "gareth-evans-250ffc80",  # Faith does not deliver us from the chisel or hammer of the D
        "gareth-evans-8f7e4023",  # The faith that pleases God is not evidenced in the obedience
        "gareth-evans-0b4a12e9",  # Faith is an attribute of the heart and is evidenced in obedi
        "gareth-evans-c9e0110e",  # Faith does not need a man to understand and believe; it need
        "gareth-evans-6a4f8972",  # Jesus pointed out to them that it was faith they needed, not
        "gareth-evans-eece1b59",  # The last prayer of Jesus for all who would come to believe H
        "gareth-evans-cd926d0d",  # The end of the journey for all who walk in faith, is that th
        "amanda-berry-smith-a27a891a",  # In my heart was peace, but I did not know how to exercise fa
        "hudson-taylor-a0b9c9a7",  # The habit of coming in faith to Him is incompatible wit
        "hudson-taylor-6356623c",  # Every true minister of GOD, every true missionary, ever
        "john-wesley-8fc9ccff",  # Faith worketh by love; faith overcometh the world; faith
        "george-muller-03935dd8",  # We are straitened in ourselves, and suppose that we are 
        "george-muller-955c302c",  # How true that word that those that trust in the Lord sha
        "george-muller-aedac97a",  # At first, our faith will be tried very little in compari
        "george-muller-80aee326",  # If the work in which we are engaged is indeed the work o
        "jonathan-edwards-90170d1f",  # A natural principle of self-love may be the foundation o
        "jonathan-edwards-80a1ab38",  # Persons may seem to have love to God and Christ, yea, to
        "andrew-murray-2f3cd850",  # The one thing by which man can honour and enjoy his God is f
        "andrew-murray-3f9c18d7",  # In one aspect there must be faith before there can be prayer
        "andrew-murray-363d5b2b",  # Faith in the promise is the fruit of faith in the promiser: 
        "andrew-murray-20f246b8",  # A heart full of God has power for the prayer of faith.
        "andrew-murray-3a68d90a",  # Faith can only live by feeding on what is Divine, on God Him
        "andrew-murray-54521d6f",  # Faith is obedience at home and looking to the Master: obedie
    ],
    "grace": [  # Grace
        "charles-h-spurgeon-e83563c7",  # Jesus has nothing which He will not use for a sinner's salva
        "charles-h-spurgeon-c918a184",  # The Lord may not give gold, but He will give grace: He may n
        "charles-h-spurgeon-c3d3a367",  # Let us be humble that we may not need to be humbled, but may
        "charles-h-spurgeon-2734034c",  # We view our God no more as Baal, our tyrant lord and mighty 
        "charles-h-spurgeon-ca2d8572",  # Look on the drops of grace, and remember that they distil fr
        "charles-h-spurgeon-a11d6733",  # Christ’s word of grace is very near you, it is on your tongu
        "charles-h-spurgeon-3abc20c9",  # Let a man truly know the grace of our Lord Jesus Christ, and
        "charles-h-spurgeon-2daf7b58",  # You will never perceive God in nature, until you have learne
        "charles-h-spurgeon-d25d6079",  # Grace is always grace, but it never seems so gracious as whe
        "charles-h-spurgeon-f0f5f775",  # The Christian's life is one of daily dependence on the grace
        "charles-h-spurgeon-e48554af",  # If we have grown in grace, it is absolutely certain that we 
        "charles-h-spurgeon-62f2db13",  # Your business is to seek Christ crucified for yourselves, no
        "thomas-a-kempis-d0edf151",  # God does well in giving the grace of consolation, but man do
        "thomas-a-kempis-90b0ce53",  # The man who lives without Jesus is the poorest of the poor, 
        "thomas-a-kempis-9a6d1484",  # Grace does not consider what is useful and advantageous to h
        "thomas-a-kempis-75fd349d",  # Grace brings all things back to God in Whom they have their 
        "thomas-a-kempis-dc7909dc",  # Grace is always given to him who is duly grateful, and what 
        "andrew-murray-53a45df8",  # Ever stand before God, in Christ; ever wait for all grace fr
        "augustine-of-hippo-c210876c",  # To Thy grace I ascribe it, and to Thy mercy, that Thou hast 
        "augustine-of-hippo-f80a2bf6",  # In these two you have those three graces exemplified: faith 
        "augustine-of-hippo-7df12100",  # Of these four different stages the first is before the law, 
        "jonathan-edwards-1a52dfe1",  # God has revealed no certain connection between salvation, an
        "jonathan-edwards-b7680c47",  # Many that others worship and serve as gods are cruel beings,
        "john-wesley-9a985cd4",  # Let not the thought of receiving more grace to-morrow, make 
        "george-muller-a471336a",  # Truly, we are poorer than ever; but through grace my eyes lo
        "george-muller-74de7829",  # It is certain that we children of God are so abundantly bles
        "hudson-taylor-38d234ec",  # To the soul really rescued by grace, no bribe to forsake GOD
        "hudson-taylor-b7ada31d",  # Grace has made her like the palm-tree, the emblem alike of u
        "hudson-taylor-fab4ab06",  # How wondrous the grace that has made the bride of CHRIST to 
        "amanda-berry-smith-f22720ef",  # The very best chance for growing in grace, really and succes
        "thomas-a-kempis-f4303a94",  # Just men depend on the grace of God rather than on their
        "augustine-of-hippo-c006d51a",  # I call upon Thee, O my God, my mercy, Who createdst me,
        "augustine-of-hippo-e35729b7",  # Let them then be turned, and seek Thee; because not as
        "augustine-of-hippo-c2f65106",  # Thou didst rescue my tongue, whence Thou hadst before r
        "hudson-taylor-8f87ae30",  # GOD'S overflow more than supplies the lack of individua
        "hudson-taylor-938e0682",  # We are not to think that our holiest service is free fr
        "john-wesley-24804ca0",  # God justifieth not the godly, but the ungodly; not those
        "john-wesley-14f9003f",  # Whatsoever good is in man, or is done by man, God is the
        "george-muller-5cce5220",  # Is not that, which alone can make us worthy to receive a
        "jonathan-edwards-2f83aa62",  # Man hath now a greater dependence on the grace of God th
        "jonathan-edwards-1adaf802",  # We are dependent on the power of God to convert us, and 
        "jonathan-edwards-5b3032a3",  # None are so low or inferior, but Christ's condescension 
        "andrew-murray-4fd4375c",  # The Lord does not demand of us a perfect fulfilment of the l
    ],
    "holy-spirit": [  # The Holy Spirit
        "charles-h-spurgeon-c1353dff",  # The Holy Ghost Himself cannot better glorify the Lord Jesus 
        "charles-h-spurgeon-d59a45ab",  # There never yet was a heavenly thought, a hallowed deed, or 
        "charles-h-spurgeon-c3eec6ac",  # Let us ever remember that Christ on the cross is of no value
        "andrew-murray-c28b985e",  # God alone, who gave us the Holy Spirit, can restore the Holy
        "andrew-murray-3279a07e",  # The Holy Spirit is the life of the heavenly Vine, and what y
        "e-m-bounds-eaa3a1c9",  # Prayer is the only element in which the Holy Spirit can live
        "jonathan-edwards-961af03e",  # The Spirit of God may act upon a creature, and yet not in ac
        "jonathan-edwards-0334dcf6",  # We may often observe it, that the Holy Spirit who indited th
        "hudson-taylor-6fa59319",  # Many a believer to whom Christ has left peace, knows little 
        "hudson-taylor-292a6824",  # The Bible is a supernatural book, a divine revelation: the H
        "hudson-taylor-61a35270",  # The Holy Spirit is the other Comforter, sent by the Father i
        "hudson-taylor-7ac514c2",  # Thanks be to God, the illumination of the HOLY GHOST is prom
        "thomas-a-kempis-72fe1814",  # Not every desire is from the Holy Spirit, even though it
        "andrew-murray-bb9d377b",  # With our whole being consciously yielded to the inspiration 
    ],
    "love-of-god": [  # The Love of God
        "charles-h-spurgeon-8b8e88db",  # We are not going to talk about law, and duty, and punishment
        "charles-h-spurgeon-c84751da",  # Salvation does not come from the preacher’s authority, but t
        "charles-h-spurgeon-d6d84bd3",  # Beloved, the Lord’s workers have sauce with their bread: not
        "charles-h-spurgeon-7faf8f59",  # Christ in the heart, means Christ believed in, Christ belove
        "charles-h-spurgeon-cfdd6903",  # The love of Christ casts not out the love of relatives, but 
        "charles-h-spurgeon-8e8ecc65",  # It is the distinguishing mark of God's people that they know
        "charles-h-spurgeon-31ec3990",  # God's people are often chastened, and the Lord's hand lieth 
        "charles-h-spurgeon-e48554af",  # If we have grown in grace, it is absolutely certain that we 
        "thomas-a-kempis-65308598",  # Love is never self-seeking, for in whatever a person seeks h
        "thomas-a-kempis-553acf8a",  # Let all things be loved for the sake of Jesus, but Jesus for
        "thomas-a-kempis-7acdee79",  # Love tends upward; it will not be held down by anything low.
        "thomas-a-kempis-4a380367",  # Let me love You more than myself, and let me not love myself
        "thomas-a-kempis-be6f13f2",  # The wise lover regards not so much the gift of Him Who loves
        "thomas-a-kempis-69ad2257",  # Place all your trust in God; let Him be your fear and your l
        "thomas-a-kempis-8e7b6b00",  # Jesus Christ must be loved alone with a special love for He 
        "andrew-murray-7bc3e383",  # The knowledge of God's Father love is the first and simplest
        "andrew-murray-29a39898",  # Chastisement is bringing your heart into unity with God’s Wi
        "andrew-murray-ba80b140",  # The spirit of separation is the spirit of self-sacrifice, of
        "andrew-murray-c38b33cb",  # If the love of God is in your heart you will love your broth
        "e-m-bounds-bef0ccaf",  # Love of ease, spiritual indolence, religious slothfulness, a
        "augustine-of-hippo-71005631",  # Too late loved I Thee, O Thou Beauty of ancient days, yet ev
        "augustine-of-hippo-2be5d987",  # I will now call to mind my past foulness, and the carnal cor
        "augustine-of-hippo-42c3e683",  # Not with doubting, but with assured consciousness, do I love
        "augustine-of-hippo-cd00fc05",  # What then do I love, when I love my God? who is He above the
        "augustine-of-hippo-e0fb2a79",  # We love God now by faith, then we shall love Him through sig
        "augustine-of-hippo-2c5b7319",  # Now we love even our neighbor by faith; for we who are ourse
        "jonathan-edwards-f0750291",  # The saint's affections begin with God; and self-love has a h
        "jonathan-edwards-7617f48e",  # The saints desire the sincere milk of the word, not so much 
        "john-wesley-cf00ad11",  # Love has purified his heart from envy, malice, wrath, and ev
        "john-wesley-185b43a1",  # Nothing is higher than this, but Christian love; the love of
        "john-wesley-c2096cd8",  # We might have loved God the Creator, God the Preserver, God 
        "john-wesley-6cc20b2f",  # If we love Him, we cannot but love one another, as Christ lo
        "john-wesley-664808a5",  # It is love excluding sin; love filling the heart, taking up 
        "john-wesley-cf8b3317",  # No suffering, but that of Christ, has any power to expiate s
        "john-wesley-9142f92d",  # We have by nature, not only no love, but no fear of God.
        "john-wesley-e2deb11e",  # What we love we delight in: But no man has naturally any del
        "john-wesley-baa7a7a5",  # The foundation is faith, purifying the heart; the end love, 
        "george-muller-46c0a31e",  # The Lord has indeed manifested his tender care of and his gr
        "george-muller-b28e4625",  # The desires of my heart were, to retain the beloved daughter
        "hudson-taylor-cad7f3ed",  # Despite all the unworthy fears of our poor hearts, Divine lo
        "hudson-taylor-38d234ec",  # To the soul really rescued by grace, no bribe to forsake GOD
        "hudson-taylor-042ae2a5",  # The love that has made her what she is, and now takes deligh
        "hudson-taylor-fab4ab06",  # How wondrous the grace that has made the bride of CHRIST to 
        "hudson-taylor-07ddeeeb",  # The world can never be to her what it once was; the betrothe
        "hudson-taylor-a1356158",  # We do not estimate our love-gifts by their intrinsic value, 
        "hudson-taylor-09cb8768",  # The Brightness of His Father's glory, the Sun of Righteousne
        "hudson-taylor-4257638e",  # When the Lord blesses His people with peace and plenty, it i
        "hudson-taylor-c92c5138",  # God is not hard to please, nor is true human love, for it is
        "hudson-taylor-10b13faf",  # Our true self-denial, self-emptying, and giving for Christ's
        "gareth-evans-7bf997cc",  # The only thing He requires of you is your love, and that can
        "gareth-evans-8f7e4023",  # The faith that pleases God is not evidenced in the obedience
        "gareth-evans-7f44b4a6",  # The child does not experience the love whose fruit is securi
        "richard-allen-83c101e1",  # In short, the love of this world is a heavy weight upon the 
        "amanda-berry-smith-3649ad8b",  # Learn to know the beauty of love and power and sympathy of J
        "amanda-berry-smith-afbc34b8",  # How I have lived through it I cannot tell, but the blessedne
        "thomas-a-kempis-6f280cbb",  # Affection for creatures is deceitful and inconstant, but
        "thomas-a-kempis-21a0bdf5",  # One who is in love flies, runs, and rejoices; he is free,
        "augustine-of-hippo-b15cdf51",  # Surely unhappy is he who knoweth all these, and knoweth
        "augustine-of-hippo-bd88fc3a",  # Surely vain are all men who are ignorant of God, and co
        "augustine-of-hippo-1699c301",  # Thou light of my heart, Thou bread of my inmost soul, T
        "augustine-of-hippo-cb389651",  # Luxury affects to be called plenty and abundance; but T
        "augustine-of-hippo-d10a086f",  # O Thou Good omnipotent, who so carest for every one of
        "augustine-of-hippo-88c4ad24",  # I sought what I might love, in love with loving, and sa
        "hudson-taylor-68ec7c26",  # Our love to GOD is secured by GOD’S love to us.
        "john-wesley-b6d3ae5f",  # Religion is the love of God and our neighbour; that is, 
        "john-wesley-2ea5c1d3",  # We think of what we love; but we do not love God; theref
        "john-wesley-df976f9c",  # Next to the love of God, there is nothing which Satan so
        "john-wesley-cd956c0e",  # God hath given this honour to love alone: Love is the en
        "john-wesley-0c62bd4a",  # May we not be of one heart, though we are not of one opi
        "john-wesley-44fac614",  # As God is love, so man, dwelling in love, dwelt in God, 
        "jonathan-edwards-193b1c59",  # Love is an affection, but will any Christian say, men ou
        "jonathan-edwards-b82be46e",  # Fear is cast out by the Spirit of God, no other way than
        "jonathan-edwards-2f3de031",  # The saints' love to God is the fruit of God's love to th
        "jonathan-edwards-b41b9375",  # What chiefly makes a man, or any creature lovely, is his
        "andrew-murray-f1456932",  # The child who only wants to know the love of the father when
    ],
    "humility": [  # Humility
        "charles-h-spurgeon-c3d3a367",  # Let us be humble that we may not need to be humbled, but may
        "thomas-a-kempis-dc7909dc",  # Grace is always given to him who is duly grateful, and what 
        "thomas-a-kempis-8ea5438f",  # The humble live in continuous peace, while in the hearts of 
        "andrew-murray-544f0576",  # Pride and self are all of man, till man has all from Christ.
        "andrew-murray-32b8b61a",  # Nothing can be our redemption but the restoration of the los
        "andrew-murray-ba743e80",  # The truth is this, pride may die in you or nothing of heaven
        "andrew-murray-307dbdae",  # Humility before God is nothing if not proved in humility bef
        "jonathan-edwards-4daf7d38",  # The deceitfulness of the heart of man appears in no one thin
        "thomas-a-kempis-c07353e9",  # Do not think yourself better than others lest, perhaps, y
        "thomas-a-kempis-79341ddc",  # The whole world will not make him proud whom truth has su
        "thomas-a-kempis-5e7c6a28",  # Humble knowledge of self is a surer path to God than the
        "john-wesley-1fed3831",  # With regard to the Most High, man and all the concerns o
        "john-wesley-8f518f4f",  # Every child of man is in a thousand mistakes, and is lia
        "jonathan-edwards-43b90c7e",  # A spirit of pride of man's own righteousness, morality, 
        "jonathan-edwards-786db3ae",  # A proud spirit is a rebellious spirit, but a humble spir
        "jonathan-edwards-c8077ab3",  # The true saints have not such a spirit of discerning tha
        "jonathan-edwards-2591b226",  # Our understandings, if we stretch them never so far, can
    ],
    "suffering": [  # Suffering & Trials
        "charles-h-spurgeon-116882b5",  # The Lord's mercy often rides to the door of our hearts on th
        "charles-h-spurgeon-31ec3990",  # God's people are often chastened, and the Lord's hand lieth 
        "thomas-a-kempis-aa58e7e7",  # Nothing is more acceptable to God, nothing more helpful for 
        "thomas-a-kempis-4aef1a9f",  # To glory in adversity is not hard for the man who loves, for
        "thomas-a-kempis-73cdb0bb",  # No one understands the passion of Christ so thoroughly or he
        "thomas-a-kempis-35828f2d",  # No man is fit to enjoy heaven unless he has resigned himself
        "andrew-murray-7f00de09",  # Christ’s life and work, His suffering and death—it was all p
        "john-wesley-69cc6ec9",  # God gives this faith; in that moment we are accepted of God;
        "george-muller-6e95f222",  # Do but stand still in the hour of trial, and you will see th
        "george-muller-4202e1fe",  # Do but stand still in the hour of trial, and you will see th
        "george-muller-caed9faa",  # From my inmost soul I do ascribe it to God alone that he has
        "amanda-berry-smith-c5cbc2c8",  # How often when we are passing through deep trials we look fo
        "hudson-taylor-9e37f8aa",  # Sometimes we have trials which we cannot put into praye
        "george-muller-6a06fd93",  # The Lord has not laid upon us a burden which is too heav
    ],
    "holiness": [  # Holiness
        "charles-h-spurgeon-cfdd6903",  # The love of Christ casts not out the love of relatives, but 
        "charles-h-spurgeon-4bdec927",  # Our court-dress in heaven, and our garment of sanctification
        "charles-h-spurgeon-62f2db13",  # Your business is to seek Christ crucified for yourselves, no
        "andrew-murray-3272b680",  # Faith in Jesus is the secret of a holy life: all holy conduc
        "andrew-murray-7866a702",  # Let obedience, the listening to and the doing the will of Go
        "andrew-murray-77a4141f",  # It is the New Life that is the holy life: the full apprehens
        "jonathan-edwards-5d08473b",  # The true beauty and loveliness of all intelligent beings doe
        "jonathan-edwards-7617f48e",  # The saints desire the sincere milk of the word, not so much 
        "jonathan-edwards-20cf3293",  # There is not only a rational belief that God is holy and tha
        "jonathan-edwards-707150e7",  # Holiness and happiness are in the fruit, here and hereafter,
        "john-wesley-60c79eda",  # Faith is the condition, and the only condition, of sanctific
        "john-wesley-14ab445e",  # Every action of a Christian that is good, is sanctified by t
        "gareth-evans-5df533df",  # God knows the heart of man and will only reveal Himself to t
        "thomas-a-kempis-043d2543",  # No man rejoices safely unless he has within him the testi
        "thomas-a-kempis-e72afb6e",  # To walk with God interiorly, to be free from any external
        "thomas-a-kempis-bd12b144",  # A spiritual man quickly recollects himself because he has
        "hudson-taylor-d8fd45a2",  # If we are faithful to God in little things, we shall ga
        "hudson-taylor-a2017a32",  # To many minds there is the greatest shrinking from appe
        "hudson-taylor-a5415bca",  # We have to take our choice: we cannot enjoy both the wo
        "hudson-taylor-5ac0c4d8",  # Where that blessing is not enjoyed, there is always som
        "hudson-taylor-938e0682",  # We are not to think that our holiest service is free fr
        "john-wesley-98c3db43",  # Outward religion may be where inward is not; but if ther
        "john-wesley-a392c43e",  # Christ indeed cannot reign, where sin reigns; neither wi
        "john-wesley-ec09b762",  # The righteousness of Christ is doubtless necessary for a
        "jonathan-edwards-4d2570d4",  # If we would learn what true religion is, we must go wher
        "jonathan-edwards-e429bd29",  # If we be not in good earnest in religion, and our wills 
        "jonathan-edwards-c02f29d7",  # Godliness consists not in a heart to intend to do the wi
        "jonathan-edwards-fb6548c8",  # Herein consists the beauty of the saints, that they are 
        "jonathan-edwards-1481dba4",  # The reason why it is not dishonorable to be necessarily 
        "andrew-murray-3f0a513b",  # Not according to what I try to be when praying, but what I a
        "andrew-murray-ac9e4831",  # Our priestly power with God depends on our personal life and
    ],
    "the-cross": [  # The Cross of Christ
        "charles-h-spurgeon-1fe6c2ed",  # The Lord cannot read our pardon written in the blood of His 
        "charles-h-spurgeon-cb6b8059",  # Not for confession, nor for reformation, but in connection w
        "charles-h-spurgeon-68366e72",  # Come, my soul, pluck up courage, and put down thy feet in th
        "charles-h-spurgeon-18e34bba",  # There are some sciences that may be learned by the head, but
        "charles-h-spurgeon-f34cdb2a",  # Though they know a little about Christ on Calvary, they know
        "charles-h-spurgeon-c3eec6ac",  # Let us ever remember that Christ on the cross is of no value
        "charles-h-spurgeon-f90f1753",  # Little-faith was bought with the blood of Christ; ay, and he
        "charles-h-spurgeon-1b7df6d3",  # If thou wouldst find thy way to God's bright throne, find fi
        "thomas-a-kempis-4aef1a9f",  # To glory in adversity is not hard for the man who loves, for
        "hudson-taylor-10b13faf",  # Our true self-denial, self-emptying, and giving for Christ's
        "gareth-evans-cf0d0a61",  # The only way man can approach God is through the shed blood 
        "gareth-evans-12a18c7e",  # To those who have placed their trust in the finished work of
        "thomas-a-kempis-77d5e620",  # A man’s true progress consists in denying himself, and th
        "hudson-taylor-59c25747",  # The GOD of the Bible is a GOD who punishes sin, and can
        "hudson-taylor-a1d67b37",  # Self-denial surely means something far greater than som
        "jonathan-edwards-411b4379",  # Christ never so eminently appeared for divine justice, a
    ],
    "trusting-god": [  # Trusting God
        "charles-h-spurgeon-63de5d24",  # Trust not thyself nor any born of woman, beyond due bounds; 
        "thomas-a-kempis-62c7429e",  # To trust in You above all things is the strongest comfort of
        "thomas-a-kempis-69ad2257",  # Place all your trust in God; let Him be your fear and your l
        "thomas-a-kempis-574029fa",  # The one often errs, the other trusts in God and is not decei
        "e-m-bounds-456fba5b",  # Prayer is mighty in its operations, and God never disappoint
        "e-m-bounds-cc849a69",  # Faith is not believing just anything; it is believing God, r
        "jonathan-edwards-27f6a365",  # He does not merely rationally believe that God is glorious, 
        "george-muller-6e95f222",  # Do but stand still in the hour of trial, and you will see th
        "george-muller-da2889c3",  # How great is the blessing which the soul obtains by trusting
        "george-muller-51145329",  # Ask God also to enlighten you not merely concerning your sta
        "george-muller-4202e1fe",  # Do but stand still in the hour of trial, and you will see th
        "george-muller-708ce87e",  # The lying too long in bed not merely keeps us from giving th
        "george-muller-caed9faa",  # From my inmost soul I do ascribe it to God alone that he has
        "gareth-evans-12a18c7e",  # To those who have placed their trust in the finished work of
        "richard-allen-31ab9496",  # To be slow and uneasy at almsgiving, argues a strong distrus
        "amanda-berry-smith-d3999568",  # What else ought we to do, when we bring our friends, but to 
        "thomas-a-kempis-85bd98b1",  # Seek true peace, not on earth but in heaven; not in men o
        "thomas-a-kempis-ce999abc",  # Many words do not satisfy the soul; but a good life eases
        "thomas-a-kempis-f4303a94",  # Just men depend on the grace of God rather than on their
        "augustine-of-hippo-d10a086f",  # O Thou Good omnipotent, who so carest for every one of
        "hudson-taylor-f8d18af3",  # Oh, it is sweet to live thus directly dependent upon th
        "hudson-taylor-2dd2dd38",  # Where there is fitness for the work, the way will proba
        "hudson-taylor-d414362d",  # Dangers seen sometimes appal us, or appal those who lov
        "john-wesley-c49400e2",  # You cannot deceive him; for he is infinite wisdom: You c
        "george-muller-dad57ef3",  # Is it not manifest that it is most precious in every way
        "george-muller-25db2ca7",  # How great is the blessing which the soul obtains by trus
        "george-muller-73e19adb",  # How blessed therefore is it to trust in God, and in him 
        "george-muller-d2db737a",  # Would it have been right to charge God with unfaithfulne
        "jonathan-edwards-4a8c058b",  # All the kings of the earth before God are as grasshopper
        "andrew-murray-8f923be4",  # God will not delay one moment longer than is absolutely nece
    ],
    "joy": [  # Joy
        "charles-h-spurgeon-d6d84bd3",  # Beloved, the Lord’s workers have sauce with their bread: not
        "charles-h-spurgeon-4389b884",  # He who delights in the possession of the Lord Jesus hath all
        "thomas-a-kempis-8a6df7db",  # God alone, the eternal and infinite, satisfies all, bringing
        "thomas-a-kempis-7ab2c082",  # Christ will come to you offering His consolation, if you pre
        "andrew-murray-bdffda15",  # Man was to have the joy of receiving every moment out of the
        "andrew-murray-cdf11ae9",  # The rest, the silence, the stillness, and the patient waitin
        "andrew-murray-7866a702",  # Let obedience, the listening to and the doing the will of Go
        "andrew-murray-def0eaf2",  # The life of abiding and obedience, of love and joy, of clean
        "e-m-bounds-da0bf2bc",  # To do God's will without demur, is the joy as it is the priv
        "augustine-of-hippo-01e56d20",  # Thou awakest us to delight in Thy praise; for Thou madest us
        "jonathan-edwards-35c8dd47",  # The former rejoices in himself; self is the first foundation
        "jonathan-edwards-b7680c47",  # Many that others worship and serve as gods are cruel beings,
        "john-wesley-e2deb11e",  # What we love we delight in: But no man has naturally any del
        "george-muller-0ddfdb70",  # A flow of joy came into my soul whilst realising thus the un
        "george-muller-48c5690b",  # Frequently, too, a fresh answer to prayer, obtained in this 
        "hudson-taylor-042ae2a5",  # The love that has made her what she is, and now takes deligh
        "hudson-taylor-d4f6ede5",  # The little one's heart is full; and the mother's heart is al
        "hudson-taylor-1f25798f",  # How much of prayer there is that begins and ends with the cr
        "hudson-taylor-6659df97",  # When the Lord Jesus comes again, those, surely, who have sto
        "amanda-berry-smith-3fe22a05",  # How glad I am that God nowhere teaches that men have to go i
        "amanda-berry-smith-7de9680d",  # The burden rolled away; I felt it when it left me, and a flo
        "thomas-a-kempis-21a0bdf5",  # One who is in love flies, runs, and rejoices; he is free,
        "jonathan-edwards-932bdf53",  # The saint hath spiritual joy and pleasure by a kind of e
    ],
    "hope": [  # Hope
        "charles-h-spurgeon-b0f71ee3",  # Come to Jesus, by quitting every other hope, by thinking of 
        "augustine-of-hippo-87986dcb",  # The fact that we do not see either what we believe or what w
        "augustine-of-hippo-196b5d19",  # No one, then, need hope that after he is dead he shall obtai
        "augustine-of-hippo-daf2b4a0",  # For when there is a question as to whether a man is good, on
        "john-wesley-9fddda8a",  # The righteousness of Christ is the whole and sole foundation
        "john-wesley-0d8ca0c2",  # The pure love of our neighbour, springing from the love of G
        "john-wesley-697ed3cb",  # Reason, however cultivated and improved, cannot produce the 
        "augustine-of-hippo-22d8524d",  # When, then, we believe that good is about to come, this
        "jonathan-edwards-d990b657",  # The soul of every man craves a happiness that is equal t
    ],
    "peace": [  # Peace
        "charles-h-spurgeon-010273ba",  # Unless the heart be kept peaceable, the life will not be hap
        "charles-h-spurgeon-c96dd1a1",  # The believer enjoys, in favored seasons, such an intimacy wi
        "thomas-a-kempis-8ea5438f",  # The humble live in continuous peace, while in the hearts of 
        "augustine-of-hippo-ae703f88",  # When out of their order, they are restless; restored to orde
        "augustine-of-hippo-7df12100",  # Of these four different stages the first is before the law, 
        "john-wesley-17ad2058",  # We know everyone who has peace with God, through Jesus Chris
        "hudson-taylor-4257638e",  # When the Lord blesses His people with peace and plenty, it i
        "hudson-taylor-b1a3a6a3",  # When sin is put away the Spirit again lifts up His countenan
        "amanda-berry-smith-a27a891a",  # In my heart was peace, but I did not know how to exercise fa
        "amanda-berry-smith-afbc34b8",  # How I have lived through it I cannot tell, but the blessedne
        "thomas-a-kempis-85bd98b1",  # Seek true peace, not on earth but in heaven; not in men o
        "thomas-a-kempis-1383b3ad",  # All men desire peace but all do not care for the things t
        "thomas-a-kempis-47fd3784",  # Happy is the man who can throw off the weight of every ca
        "thomas-a-kempis-a34c6521",  # True peace of heart, then, is found in resisting passions
        "augustine-of-hippo-109ebfbc",  # The Word itself calleth thee to return: and there is th
        "hudson-taylor-4d77cbd9",  # The peace, which we can neither make nor keep, will its
        "hudson-taylor-d414362d",  # Dangers seen sometimes appal us, or appal those who lov
    ],
    "repentance": [  # Repentance
        "charles-h-spurgeon-ddf56c92",  # Jesus is exalted on high, that through the virtue of His int
        "thomas-a-kempis-6ff5eb6f",  # No man deserves the consolation of heaven unless he persiste
        "thomas-a-kempis-47fd3784",  # Happy is the man who can throw off the weight of every ca
        "augustine-of-hippo-2fc36ce4",  # Be not foolish, O my soul, nor become deaf in the ear o
        "augustine-of-hippo-109ebfbc",  # The Word itself calleth thee to return: and there is th
        "augustine-of-hippo-e35729b7",  # Let them then be turned, and seek Thee; because not as
        "jonathan-edwards-39fe77bc",  # Holy fear is so much the nature of true godliness, that 
    ],
    "scripture": [  # The Word of God
        "charles-h-spurgeon-14b10a83",  # You may read the Bible continuously, and yet never learn any
        "andrew-murray-622d4639",  # The word is nothing if it is not kept, obeyed, or done.
        "andrew-murray-25892082",  # The effect of the word on the heart is in most cases not imm
        "andrew-murray-75191679",  # Throughout Scripture, in the life of every saint, of God’s o
        "jonathan-edwards-0334dcf6",  # We may often observe it, that the Holy Spirit who indited th
        "george-muller-65f3b573",  # Faith has to do with the word of God,—rests upon the written
        "hudson-taylor-292a6824",  # The Bible is a supernatural book, a divine revelation: the H
        "gareth-evans-b4cd492e",  # To every weapon of Satan they have an answer in the Word of 
        "hudson-taylor-b6346059",  # The child of GOD has no need of the counsel of the ungo
        "george-muller-06569328",  # How precious it is, even for this life, to act according
        "george-muller-37a07bae",  # Do not men believe that God means what he appears plainl
        "george-muller-46a167ee",  # We may therefore profitably meditate, with God’s blessin
        "jonathan-edwards-46a608bf",  # Holy affections are not heat without light; but evermore
        "andrew-murray-254d7f38",  # The chief thing is, not to know what God has said we must do
    ],
    "salvation": [  # Salvation & the Gospel
        "charles-h-spurgeon-91fc01a4",  # The Lord's salvation can come to us though we have only fait
        "charles-h-spurgeon-cb3665e4",  # Jesus Christ is to them a Saviour strong and mighty, a Rock 
        "charles-h-spurgeon-a4fd540c",  # Faith which refuses to obey the commands of the Saviour is a
        "charles-h-spurgeon-e60e0d86",  # You need not, therefore, despair: that which is necessary to
        "charles-h-spurgeon-e83563c7",  # Jesus has nothing which He will not use for a sinner's salva
        "charles-h-spurgeon-5096795d",  # Faith is as much the gift of God as is the Saviour upon whom
        "charles-h-spurgeon-d22c535f",  # Our awakenings are not to help the Saviour, but to help us t
        "charles-h-spurgeon-499c8b72",  # Salvation is not by our knowing our own ruin, but by fully g
        "charles-h-spurgeon-38eab6a5",  # Trust Christ, and by that trust you grasp salvation and eter
        "charles-h-spurgeon-3eea1a98",  # Believe in the Lord Jesus Christ, and you, even you, will be
        "charles-h-spurgeon-92fc517e",  # Whether faith is large or small, whether you can do much or 
        "charles-h-spurgeon-b11a33f8",  # Come utterly ruined and undone, for in Jesus Christ there is
        "charles-h-spurgeon-5fcb15f8",  # The gospel is not a scheme of giving to God, but of receivin
        "charles-h-spurgeon-57735f38",  # We are saved by faith, and not by feeling; yet there is a re
        "charles-h-spurgeon-0c53a2aa",  # As the Lord hath but one family, written in one register, re
        "thomas-a-kempis-e5643ba2",  # The present is very precious; these are the days of salvatio
        "andrew-murray-32b8b61a",  # Nothing can be our redemption but the restoration of the los
        "e-m-bounds-cac9217a",  # God’s Gospel has always waited more on prayer than on anythi
        "e-m-bounds-3aad54a5",  # Prayer does not interpret God’s providences, but it does jus
        "augustine-of-hippo-f39c2fe5",  # The Way, the Saviour Himself, well pleased me, but as yet I 
        "jonathan-edwards-1a52dfe1",  # God has revealed no certain connection between salvation, an
        "jonathan-edwards-f9dba01f",  # Faith abases men and exalts God, it gives all the glory of r
        "john-wesley-c2096cd8",  # We might have loved God the Creator, God the Preserver, God 
        "george-muller-a1e19e7a",  # The answer is, believe in the Lord Jesus, trust in Him, depe
        "george-muller-7716c8c8",  # Jesus came not to save painted but real sinners; but he has 
        "hudson-taylor-e1f8b629",  # The good works of the unsaved may indeed benefit their fello
        "hudson-taylor-dac18fb3",  # It was one of the objects of our Saviour's mission to reveal
        "gareth-evans-cd926d0d",  # The end of the journey for all who walk in faith, is that th
        "amanda-berry-smith-3649ad8b",  # Learn to know the beauty of love and power and sympathy of J
        "amanda-berry-smith-e93eed38",  # The Gospel of Jesus was so full and practical, and with good
        "augustine-of-hippo-c2f65106",  # Thou didst rescue my tongue, whence Thou hadst before r
        "augustine-of-hippo-6534752e",  # Let me not be mine own life; from myself I lived ill, d
        "hudson-taylor-59c25747",  # The GOD of the Bible is a GOD who punishes sin, and can
        "john-wesley-24804ca0",  # God justifieth not the godly, but the ungodly; not those
        "john-wesley-96fdc970",  # Christ is not only God above us; which may keep us in aw
        "george-muller-ac311d8d",  # Do you verily depend upon him alone for the salvation of
        "jonathan-edwards-cf2c4824",  # Conversion is a great and universal change of the man, t
        "jonathan-edwards-fe469383",  # Wisdom was a thing that the Greeks admired; but Christ i
        "jonathan-edwards-e8e8a7e6",  # We are dependent on Christ the Son of God, as he is our 
        "andrew-murray-0bdab1a3",  # Many a one wishes to be saved, but perishes because he does 
    ],
    "heaven": [  # Heaven & Eternity
        "charles-h-spurgeon-8b8e88db",  # We are not going to talk about law, and duty, and punishment
        "charles-h-spurgeon-38eab6a5",  # Trust Christ, and by that trust you grasp salvation and eter
        "charles-h-spurgeon-d59a45ab",  # There never yet was a heavenly thought, a hallowed deed, or 
        "charles-h-spurgeon-4bdec927",  # Our court-dress in heaven, and our garment of sanctification
        "thomas-a-kempis-35828f2d",  # No man is fit to enjoy heaven unless he has resigned himself
        "thomas-a-kempis-6ff5eb6f",  # No man deserves the consolation of heaven unless he persiste
        "andrew-murray-ba743e80",  # The truth is this, pride may die in you or nothing of heaven
        "andrew-murray-ee7711d2",  # God is a spirit: He is the Everlasting and Unchangeable One;
        "andrew-murray-3279a07e",  # The Holy Spirit is the life of the heavenly Vine, and what y
        "andrew-murray-9222df6d",  # Let us seek to understand that the life of the branch is a l
        "andrew-murray-716ef8a0",  # To be a branch means not only bearing fruit on earth, but po
        "e-m-bounds-056461e2",  # Nothing short of being red hot for God, can keep the glow of
        "e-m-bounds-1ce791ff",  # Prayer holds earth to heaven and brings heaven in close cont
        "augustine-of-hippo-b4abaa5a",  # Nothing then of Thy Word doth give place or replace, because
        "jonathan-edwards-32a16695",  # The kingdom of heaven is not to be taken but by violence.
        "jonathan-edwards-f3a4122f",  # None that will come to Christ, let his condition be what it 
        "john-wesley-b0fcf5f2",  # The way to hell has nothing singular in it; but the way to h
        "john-wesley-cf8b3317",  # No suffering, but that of Christ, has any power to expiate s
        "john-wesley-a998de10",  # Many indeed think of being happy with God in heaven; but the
        "hudson-taylor-6659df97",  # When the Lord Jesus comes again, those, surely, who have sto
        "gareth-evans-12ac9d3d",  # The eagle does not rest until it sees its offspring rise to 
        "richard-allen-83c101e1",  # In short, the love of this world is a heavy weight upon the 
        "george-muller-2059f3eb",  # Where should the heart of the disciple of the Lord Jesus
        "george-muller-edf32cb6",  # Remember that the world passeth away, but that the thing
        "jonathan-edwards-88349935",  # How great is their glory and honor that are admitted to 
    ],
    "surrender": [  # Surrender & Obedience
        "thomas-a-kempis-23ece4d7",  # No man commands safely unless he has learned well how to obe
        "andrew-murray-b4a4d4f8",  # God only asks of us to yield, to consent, to wait upon Him, 
        "andrew-murray-622d4639",  # The word is nothing if it is not kept, obeyed, or done.
        "andrew-murray-ba80b140",  # The spirit of separation is the spirit of self-sacrifice, of
        "andrew-murray-d736c7c7",  # It was by obedience Christ as Vine honored the Father as Hus
        "andrew-murray-53a45df8",  # Ever stand before God, in Christ; ever wait for all grace fr
        "e-m-bounds-7894b850",  # No man can pray -- really pray -- who does not obey.
        "e-m-bounds-ca009ef5",  # The will must be surrendered to God as a primary condition o
        "e-m-bounds-55b9917c",  # The prayer life is the direct fruit of entire consecration t
        "e-m-bounds-4d0e283e",  # God wants consecrated men because they can pray and will pra
        "augustine-of-hippo-6e758fea",  # The mind commands the body, and it obeys instantly; the mind
        "john-wesley-b2f0969f",  # A man may be in God’s favour though he feel sin; but not if 
        "hudson-taylor-d7a46992",  # It may be that we have separated ourselves to carry out our 
        "hudson-taylor-d51cda35",  # Nearness to God calls for tenderness of conscience, thoughtf
        "gareth-evans-0b4a12e9",  # Faith is an attribute of the heart and is evidenced in obedi
        "gareth-evans-c9e0110e",  # Faith does not need a man to understand and believe; it need
        "thomas-a-kempis-9de70a18",  # Whatever is not God is nothing and must be accounted as n
        "thomas-a-kempis-77d5e620",  # A man’s true progress consists in denying himself, and th
        "thomas-a-kempis-e72afb6e",  # To walk with God interiorly, to be free from any external
        "augustine-of-hippo-5176d739",  # Let not these occupy my soul; let God rather occupy it,
        "augustine-of-hippo-6534752e",  # Let me not be mine own life; from myself I lived ill, d
        "hudson-taylor-a5415bca",  # We have to take our choice: we cannot enjoy both the wo
        "hudson-taylor-5ac0c4d8",  # Where that blessing is not enjoyed, there is always som
        "hudson-taylor-14428932",  # Self-will is unmingled folly, and can only end in injur
        "hudson-taylor-a1d67b37",  # Self-denial surely means something far greater than som
        "john-wesley-c8f76836",  # The love of the creature is changed to the love of the C
        "john-wesley-4819ac9b",  # If you move but one step towards God, you are not as oth
        "andrew-murray-4fd4375c",  # The Lord does not demand of us a perfect fulfilment of the l
        "andrew-murray-bb9d377b",  # With our whole being consciously yielded to the inspiration 
        "andrew-murray-54521d6f",  # Faith is obedience at home and looking to the Master: obedie
        "andrew-murray-6b7ccf7f",  # Obedience is the only path that leads to the glory of God.
    ],
    "sin-and-temptation": [  # Sin & Temptation
        "charles-h-spurgeon-bda51fda",  # Our Lord Jesus did not die for imaginary sins, but His heart
        "charles-h-spurgeon-af63b79e",  # Jesus Christ, made sin for me, was what I saw, and that sigh
        "charles-h-spurgeon-76d1edd6",  # Jesus did not die for our righteousness, but He died for our
        "charles-h-spurgeon-1f40aadf",  # Christ and the believing sinner are in the same boat: unless
        "charles-h-spurgeon-158e253e",  # Faith is the linen which binds the plaster of Christ's recon
        "charles-h-spurgeon-96d23369",  # God will not lead you into temptation, but you may lead your
        "charles-h-spurgeon-b8b46bcf",  # Not only does God bear with sin, but in the person of his So
        "charles-h-spurgeon-3f56a9f6",  # The Lord Jesus was unto us a covering for sin, and so a cove
        "charles-h-spurgeon-d0fcbb43",  # Christ Jesus is the only escape for a sinner pursued by the 
        "charles-h-spurgeon-52ff0174",  # Jesus identified Himself with His people, and therefore thei
        "charles-h-spurgeon-f5498610",  # Our Lord Jesus did not handle sin with the golden tongs, but
        "charles-h-spurgeon-756e08e3",  # Not one sin is to be spared, but against the whole is to be 
        "charles-h-spurgeon-49d53581",  # Do you think that we are forever to be the drudges and the s
        "andrew-murray-e8346b82",  # A man does not get converted without having the conviction o
        "augustine-of-hippo-c210876c",  # To Thy grace I ascribe it, and to Thy mercy, that Thou hast 
        "augustine-of-hippo-f4cae61f",  # To me, however, it seems certain that every lie is a sin, th
        "augustine-of-hippo-1d48b0f6",  # After the fall, however, a more abundant exercise of God’s m
        "augustine-of-hippo-f72c34ba",  # As, then, the soul even now finds it impossible to desire un
        "jonathan-edwards-257aca58",  # The subtlety of Satan appears in its height, in his managing
        "john-wesley-b2f0969f",  # A man may be in God’s favour though he feel sin; but not if 
        "john-wesley-17ad2058",  # We know everyone who has peace with God, through Jesus Chris
        "john-wesley-664808a5",  # It is love excluding sin; love filling the heart, taking up 
        "george-muller-ef40c1e4",  # God sent Him, that He might bear the punishment, due to us g
        "george-muller-9ef0f4c9",  # A hearty desire for the conversion of sinners, and earnest p
        "george-muller-7716c8c8",  # Jesus came not to save painted but real sinners; but he has 
        "hudson-taylor-2d3e6a96",  # The sin of neglected communion may be forgiven, and yet the 
        "hudson-taylor-fca298ba",  # Man's heart is so darkened by the Fall, and by personal sinf
        "hudson-taylor-b1a3a6a3",  # When sin is put away the Spirit again lifts up His countenan
        "amanda-berry-smith-cf826ddb",  # God showed me I was a dreadful sinner, but still I wanted to
        "thomas-a-kempis-a34c6521",  # True peace of heart, then, is found in resisting passions
        "john-wesley-bd5633fb",  # The world is the men that know not God, that neither lov
        "john-wesley-2b7968c1",  # Sin is then overcome, but it is not rooted out; it is co
        "john-wesley-fbb70206",  # Abhor sin far more than death or hell; abhor sin itself,
        "john-wesley-59d8d274",  # The body dies when it is separated from the soul; the so
        "jonathan-edwards-406773f3",  # Every dog hath his kennel, every swine hath his swill; a
    ],
    "contentment": [  # Contentment
        "thomas-a-kempis-1e51f540",  # The man who is at perfect ease is never suspicious, but the 
        "george-muller-b28e4625",  # The desires of my heart were, to retain the beloved daughter
        "thomas-a-kempis-9de70a18",  # Whatever is not God is nothing and must be accounted as n
        "thomas-a-kempis-6f280cbb",  # Affection for creatures is deceitful and inconstant, but
        "thomas-a-kempis-32dc0a68",  # Man’s happiness does not consist in the possession of abu
        "augustine-of-hippo-5176d739",  # Let not these occupy my soul; let God rather occupy it,
        "augustine-of-hippo-cb389651",  # Luxury affects to be called plenty and abundance; but T
        "hudson-taylor-a0b9c9a7",  # The habit of coming in faith to Him is incompatible wit
        "george-muller-e263c093",  # The Lord helping us, we would rather suffer privation th
    ],
}
