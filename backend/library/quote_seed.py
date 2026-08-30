"""Curated quotations, by author — the sourced half of the quote pages.

Quote pages are the only page type on this site with no primary text underneath
them: a chapter page is 1,900 words of Bunyan whatever else it carries, but a
quote page IS its furniture. That is the shape search engines classify as a
doorway when it is mass-produced, and the risk is not confined to the quote
pages — scaled thin content is judged against a domain. The pilot shipped ONE
author (Spurgeon) and waited; this is the considered scale-up to three, chosen
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
#: andrew-murray         — approved 2026-08-30, twenty-seven.
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
    {"charles-h-spurgeon", "thomas-a-kempis", "andrew-murray"}
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
]


QUOTES = {
    "charles-h-spurgeon": SPURGEON,
    "thomas-a-kempis": THOMAS_A_KEMPIS,
    "andrew-murray": ANDREW_MURRAY,
}
