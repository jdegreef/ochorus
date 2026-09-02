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
#: charles-h-spurgeon    — approved 2026-08-28, sixty.
#: thomas-a-kempis       — approved 2026-08-30, thirty-six.
#: andrew-murray         — approved 2026-08-30, twenty-seven;
#:                         and 2026-09-02, twenty-three more (the four new books).
#: e-m-bounds            — approved 2026-08-30, twenty-eight.
#: augustine-of-hippo    — approved 2026-08-30, thirteen.
#: jonathan-edwards      — approved 2026-08-30, eleven.
#: john-wesley           — approved 2026-08-30, eighteen.
#: george-muller         — approved 2026-08-30, eleven.
#: hudson-taylor         — approved 2026-08-30, ten.
#: gareth-evans          — approved 2026-08-30, twenty-two;
#:                          four more 2026-08-31 (twenty-six).
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
    }
)

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
}
