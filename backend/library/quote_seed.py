"""Curated quotations, by author — the sourced half of the quote pages.

A PILOT, deliberately one author. Quote pages are the only page type on this
site with no primary text underneath them: a chapter page is 1,900 words of
Bunyan whatever else it carries, but a quote page IS its furniture. That is the
shape search engines classify as a doorway when it is mass-produced, and the
risk is not confined to the quote pages — scaled thin content is judged against
a domain. So this ships sixty quotations for Charles Spurgeon and stops, until
their indexation says whether the next thirty-nine authors are worth doing.

HOW THESE WERE CHOSEN, and what that does and does not amount to. A mechanical
pass over ~400,000 words of Spurgeon shortlisted self-contained sentences of
12-34 words, dropping dangling openers, mid-sentence citations, quotation marks,
parentheticals and sentences about the book rather than about the faith; a
scoring pass favoured contrast, brevity and a recognisable subject; sentences
that closely track a verse of the bundled ASV were dropped, because printing a
psalm under Spurgeon's name is exactly the misattribution a sourced card exists
to beat. That left 171, from which these 60 were chosen by reading them.

That last pass is judgement, and it is not the same thing as a human being
saying "yes, print this under his name". Every row therefore seeds
`reviewed=False` and NOTHING reaches a reader until `approve_quotes` runs. The
public serializer filters on the flag; the page renders only what a person has
signed off. This mirrors how AI translations are gated, and for the same reason.

`paragraph` indexes the body's TOP-LEVEL CHILDREN — the unit the reader's `?p=`
jump counts. Indexing by <p> alone is wrong in any chapter with an <h2>, and was
wrong here until it was checked against the fixture: all sixty were verified to
resolve to the paragraph containing their own text.

Registered in `content_sources.json`, so editing this file rebuilds the reader.
"""

from __future__ import annotations

#: (author slug, quotations). Source is a ("book-slug", chapter_order) pair or a
#: sermon slug — exactly one of the two.
SPURGEON = [
    {
        "slug": "charles-h-spurgeon-8b8e88db",
        "text": "We are not going to talk about law, and duty, and punishment, but about love, and goodness, and forgiveness, and mercy, and eternal life.",
        "chapter": ("all-of-grace", 2),
        "paragraph": 2,
    },
    {
        "slug": "charles-h-spurgeon-2f75a3c1",
        "text": "Jesus Christ himself came not to call the righteous, and I am not going to do what He did not do.",
        "chapter": ("all-of-grace", 3),
        "paragraph": 12,
    },
    {
        "slug": "charles-h-spurgeon-bda51fda",
        "text": "Our Lord Jesus did not die for imaginary sins, but His heart's blood was spilt to wash out deep crimson stains, which nothing else can remove.",
        "chapter": ("all-of-grace", 3),
        "paragraph": 16,
    },
    {
        "slug": "charles-h-spurgeon-af63b79e",
        "text": "Jesus Christ, made sin for me, was what I saw, and that sight gave me rest.",
        "chapter": ("all-of-grace", 4),
        "paragraph": 18,
    },
    {
        "slug": "charles-h-spurgeon-1fe6c2ed",
        "text": "The Lord cannot read our pardon written in the blood of His own Son, and then smite us.",
        "chapter": ("all-of-grace", 5),
        "paragraph": 10,
    },
    {
        "slug": "charles-h-spurgeon-94833965",
        "text": "The righteousness of faith is not the moral excellence of faith, but the righteousness of Jesus Christ which faith grasps and appropriates.",
        "chapter": ("all-of-grace", 7),
        "paragraph": 6,
    },
    {
        "slug": "charles-h-spurgeon-91fc01a4",
        "text": "The Lord's salvation can come to us though we have only faith as a grain of mustard seed.",
        "chapter": ("all-of-grace", 7),
        "paragraph": 7,
    },
    {
        "slug": "charles-h-spurgeon-cb3665e4",
        "text": "Jesus Christ is to them a Saviour strong and mighty, a Rock immovable and immutable; they cling to him for dear life, and this clinging saves them.",
        "chapter": ("all-of-grace", 9),
        "paragraph": 10,
    },
    {
        "slug": "charles-h-spurgeon-a4fd540c",
        "text": "Faith which refuses to obey the commands of the Saviour is a mere pretence, and will never save the soul.",
        "chapter": ("all-of-grace", 9),
        "paragraph": 15,
    },
    {
        "slug": "charles-h-spurgeon-e60e0d86",
        "text": "You need not, therefore, despair: that which is necessary to salvation is not continuous thought, but a simple reliance upon Jesus.",
        "chapter": ("all-of-grace", 11),
        "paragraph": 8,
    },
    {
        "slug": "charles-h-spurgeon-76d1edd6",
        "text": "Jesus did not die for our righteousness, but He died for our sins.",
        "chapter": ("all-of-grace", 11),
        "paragraph": 9,
    },
    {
        "slug": "charles-h-spurgeon-e83563c7",
        "text": "Jesus has nothing which He will not use for a sinner's salvation, and He is nothing which He will not display in the aboundings of His grace.",
        "chapter": ("all-of-grace", 14),
        "paragraph": 7,
    },
    {
        "slug": "charles-h-spurgeon-5096795d",
        "text": "Faith is as much the gift of God as is the Saviour upon whom that faith relies.",
        "chapter": ("all-of-grace", 15),
        "paragraph": 16,
    },
    {
        "slug": "charles-h-spurgeon-ddf56c92",
        "text": "Jesus is exalted on high, that through the virtue of His intercession repentance may have a place before God.",
        "chapter": ("all-of-grace", 16),
        "paragraph": 2,
    },
    {
        "slug": "charles-h-spurgeon-116882b5",
        "text": "The Lord's mercy often rides to the door of our hearts on the black horse of affliction.",
        "chapter": ("all-of-grace", 16),
        "paragraph": 4,
    },
    {
        "slug": "charles-h-spurgeon-5bc6762f",
        "text": "The Lord is able, not only to save us from hell, but to keep us from falling.",
        "chapter": ("all-of-grace", 18),
        "paragraph": 5,
    },
    {
        "slug": "charles-h-spurgeon-1f40aadf",
        "text": "Christ and the believing sinner are in the same boat: unless Jesus sinks, the believer will never drown.",
        "chapter": ("all-of-grace", 19),
        "paragraph": 10,
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
        "paragraph": 13,
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
]

QUOTES = {"charles-h-spurgeon": SPURGEON}
