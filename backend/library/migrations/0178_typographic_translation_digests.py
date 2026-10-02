"""Fingerprint translations by their WORDS, not their typography.

`translation_staleness` now hashes each row's ``typographic_form`` — dashes,
quotation marks, ellipses, entities and whitespace folded — so a typography
sweep of the English (#4936 set 4,460 typewriter dashes as em dashes) no
longer flags every translation of every work it touched.

Changing the hash changes every stored digest at once, so this re-fingerprints
the corpus under the new rule while carrying each translation's state over:

* every row's ``content_digest`` becomes its new-rule digest, so the next
  ``refresh`` sees no "own text changed" anywhere and re-baselines nothing it
  should not;
* a translation that is CURRENT gets the new-rule digest of its English. Current
  means its ``english_digest`` equals the English row's stored digest (current
  under the old rule) — or equals that English's old-rule digest from just
  BEFORE #4936 (`PRE_4936`, taken from the fixture at #4936's parent), for the
  76 works #4936 changed by typography alone. Those are the translations that
  deploy flagged for a dash; this clears them, and only them.
* any other translation keeps its old-rule ``english_digest``, which can never
  equal a new-rule digest — it stays stale until it is re-made or someone marks
  it current, exactly as before. Brainerd's #4936 change moved a tag, so it is
  not in `PRE_4936` and its translations stay flagged.

A row whose prod text differs from the fixture simply fails to match and stays
as it was: the error is always "still flagged", never "wrongly cleared".
"""

from __future__ import annotations

import hashlib

from django.db import migrations

from library.originals import is_original
from library.translation_staleness import typographic_form

_SEP = "\x1f"

#: (kind, slug) -> the English row's old-rule content_digest before #4936.
PRE_4936 = {
    (
        "book",
        "a-serious-call",
    ): "97fb24e360b1de180de8004893f9f1ebdbf5108bf926aadd6bcbc14df8f881ff",
    (
        "book",
        "all-of-grace",
    ): "693cc0a83ac13d7f5fd6e6637fc173e3a57e1bd7460a0f7dcd0f2a0570d02dd7",
    (
        "book",
        "cheque-book",
    ): "74daeb505098d3a4b34c6eed923b3b0e2d21f0ef33b443204bd5bebf9707330b",
    (
        "book",
        "christ-the-healer",
    ): "b454f4ec89e7b05f39da2f8c8778561a92911cd1406168ddbd1f01e3dd620407",
    (
        "book",
        "epistles-of-ignatius",
    ): "37e14ed308ea99ad75adead9d5d4d76854e412247f12d618346a5b472425e8dd",
    (
        "book",
        "evening-by-evening",
    ): "a0047e28b9c33bec3a3aaeb527ee0433ec6930fcb136f0496d4d0882aaa7479e",
    (
        "book",
        "finney-memoirs",
    ): "665b39984dc5627bd519eb5266bcdc35e9f027e02764cf9d2091aa83b39258b7",
    (
        "book",
        "foxes-book-of-martyrs",
    ): "4c84e0b8349aec82700283b6fd203928908c258bd1674b7cfd98c7520d2d6b3c",
    (
        "book",
        "humility-2",
    ): "74fc4c3aa4f5ce91bfb33ea12f41297b002d03aba24fd128d3c053f02309d29b",
    (
        "book",
        "life-experience-gospel-labours",
    ): "85d88fec46a751bc77a7fb153753538309344b03f5178cb1f9f04a32160bdb1f",
    (
        "book",
        "morning-by-morning",
    ): "b63e7b3a052c75f0b6698fa009c4675449e744f1ea09892b7a0ce6905e82e710",
    (
        "book",
        "necessity-of-prayer",
    ): "c63818c459ffd2cc1d13e285ef0bccaeb9aceedfbb453d7567e45dacb085e5ab",
    (
        "book",
        "our-daily-walk",
    ): "041de877933b9ea92b3fe229aa6fd37c6f4cc59db9b3d8b7f7c20e26c7bc180a",
    (
        "book",
        "possibilities-of-prayer",
    ): "42b30be1835cfe822e2f92303a02ec18077aeabf0d1d62972886f11868da097d",
    (
        "book",
        "purity-of-heart",
    ): "fa66bc45e535ad8baa643a0ee4875788efe1208ea63cccc0fa0435ae51dbee6a",
    (
        "book",
        "soar-like-the-eagle-3",
    ): "3867a8366f8d2855efc424534dcb9f20d38af8970aa916331ed48df3f3e1427a",
    (
        "book",
        "the-christians-secret-of-a-happy-life-4",
    ): "80cb7421fb424334468761bc938066bf3bc8e31b2983562dbe30a65b2550b8a2",
    (
        "book",
        "the-gospel-of-healing",
    ): "49de73cb606b8e60eab8fe89112deb8b724faf6b5526682fa10836dbb92fa31e",
    (
        "book",
        "the-normal-christian-life",
    ): "cbd384d6bfc2b18d9f72a37b776be32d2a88f50bf2749006562c156fb4f8683a",
    (
        "book",
        "treatises-of-cyprian",
    ): "7c6aa2d549bad18c5a877ec59f2497c5e970f569d755e6f6496bad17d58bf29f",
    (
        "book",
        "way-into-holiest",
    ): "bee08b936484f18df3713a5d9bb161ea8b3418d802c57ca3989ff7162a6de110",
    (
        "sermon",
        "a-divine-and-supernatural-light",
    ): "02374f7214a1baf95ab99a27fc356987efd3e5d34b07470d0b70fa476ccded45",
    (
        "sermon",
        "a-full-reward",
    ): "36c5d36193703b9e30966db2e2750bde6255f1efd3861628f58755629a82cbea",
    (
        "sermon",
        "a-living-hope-of-the-hereafter",
    ): "ad2748246a883f1c43d62a1ebb73842b43773452ee323c509386326dbef1bf15",
    (
        "sermon",
        "a-ribband-of-blue",
    ): "b94db033319d2961e88911e1e754ae2a35d141e3aec5870569aa8b2efa6fbdfe",
    (
        "sermon",
        "a-true-and-a-false-faith",
    ): "b32c6c5d4a95f832478370726366a977f8bd4d79a3d8ef48fd093e51a3a0de85",
    (
        "sermon",
        "adaptation-of-measures",
    ): "849e97312365255546ca0ebb8c814e873b5717a0b1bcd74b7918588e94945af3",
    (
        "sermon",
        "aggressive-christianity",
    ): "7ccc5b468e14bd56094e7aaca236f3a1c60d8f2121ca327ab0fee31e7ed082a8",
    (
        "sermon",
        "all-sufficiency",
    ): "c03f8ea7faeacad9387de15bc4ba3edecbbf61eb3afe9860b034594e5d16a234",
    (
        "sermon",
        "assurance-of-salvation",
    ): "8a11014b0301f1c45d4191af18b6a25840d816416bbc394e2b9a0d98fd43e45f",
    (
        "sermon",
        "blessed-adversity",
    ): "1f5678e8177a67f1a676f1024818b976a92e02f3f7dd494ab1240dbfa79ee338",
    (
        "sermon",
        "blessed-prosperity",
    ): "631137c8831f9f719b8adccc3fd573bfbf2e796f10c8623a0789932135f28e20",
    (
        "sermon",
        "christ-all-in-all",
    ): "622317a6caa815877d96a0b4237d3f763d0569653f3b90b2314f334b1376b5ce",
    (
        "sermon",
        "coming-to-the-king",
    ): "649248434ae6e0d89556da948a6dcf4923e59669077edc06241d4ed314ef9938",
    (
        "sermon",
        "dealing-with-anxious-souls",
    ): "e0f2b7d3d6e7fe775cdf2e60c54698744f2cb4dfed0d7b35195dfa4806bcbd41",
    (
        "sermon",
        "enduring-persecution-for-christ",
    ): "aed55fd91268933d93d12cf94635a0c511ab6c5084a731b74d9649d3216c784e",
    (
        "sermon",
        "excuses",
    ): "86aaa24816c433a8ea82df3f36eda8e925366da948c10cde4657c43420373288",
    (
        "sermon",
        "found-wanting",
    ): "54f5d337acb3fc2c636c18253b6944e83782def571dd657ea04f916e9a824d2f",
    (
        "sermon",
        "gideon-or-the-strength-of-weakness",
    ): "f75e25617d126e9afaf69f6d7be868a534ed0ca6cf278d6d20cac5b8d802ac5e",
    (
        "sermon",
        "god-glorified-in-mans-dependence",
    ): "01f17d95ddb7b1debafdf6f5876ab6651e7b2c41bf5bcbe4a16c5a0467ff7017",
    (
        "sermon",
        "god-or-mammon",
    ): "c5e25694ce256366fddb522a78f27d38fd581adeb2e2461d74f9db9ba1b0d3b0",
    (
        "sermon",
        "gods-love-for-a-sinning-world",
    ): "10d5157f6b8ed86d8ccb0b77d0540673f9e3b927b2eb6ceab0e54d6d2228f079",
    (
        "sermon",
        "heroes-and-cowards",
    ): "5ca63518d8d98a3759d70a8e256ca8fb73a7c71439f1556b3f709161dbb5a4f5",
    (
        "sermon",
        "how-to-work-for-god-with-success",
    ): "89f5fea8131829d10553b83ad5d1d2b66aa754e4f06a4e61a6f4eef984247002",
    (
        "sermon",
        "jephthah-or-the-faith-that-leads-to-faithfulness",
    ): "632f90f78b81f1d8f23921aeb25b6ef248d66c154374694e66cb172d1da02888",
    (
        "sermon",
        "partnership-with-god",
    ): "ee813d7ede2313fa0785b223c7c3407d4c240dade9fcc370e99a220d2afe5d6e",
    (
        "sermon",
        "pauls-praise-of-christian-love",
    ): "f4bbfc1501272cf012c5054f19d50e33595b457768862c99f8964336886071b2",
    (
        "sermon",
        "practical-prayer",
    ): "2992c0675b45bfb9673359061a2ed0e5a7e20e5da04f6019048e34a6d3d71f92",
    (
        "sermon",
        "refuges-of-lies",
    ): "2b5fab0a6b62b17f5f3bcdd94567d164672394d2a1a3786cb9d23d2644e3d8ba",
    (
        "sermon",
        "self-denial-versus-self-assertion",
    ): "dc86a809624f6e37235412e3268882fb4d9cfe5320c455fd669c2fb0e8f7ee63",
    (
        "sermon",
        "sinners-bound-to-change-their-own-hearts",
    ): "b329445c81083533ff3c732a1a3ff84aff93a39124358656864475cc73f9a735",
    (
        "sermon",
        "sinners-in-the-hands-of-an-angry-god",
    ): "54b3bd54ca15c7dea706aab7b1f5f2127120ac247271878bc176f90fe0566493",
    (
        "sermon",
        "the-appearing-of-the-grace-of-god",
    ): "1d0bb0b173143f2548aa6956182115aebdfede54491496e9deddd772eb1758b7",
    (
        "sermon",
        "the-boundless-sufficiency",
    ): "e4742c132ae47ac32920db1a8284adb9ffebba6ad5ddc7a6abcbc303f7f39afa",
    (
        "sermon",
        "the-christian-temper-supernatural-and-divine",
    ): "1ccbb4a1d409b832d51858cd37ff7a3097cca18e599047e07889f4794ea7f6d0",
    (
        "sermon",
        "the-cloud-of-witnesses",
    ): "02a9d6e1b416f3aba9f74d30ccb134b20b335552411ae38c17446c0b07a7f34e",
    (
        "sermon",
        "the-cross-is-a-radical-thing",
    ): "61d5a2b243686a590c16694e9d7a012afb0374e35a13c906137a05092962b3bb",
    (
        "sermon",
        "the-day-of-golden-opportunity",
    ): "636557b3b5f6623b5e0da981805223106725e3aaf3249a85b0fdaf1723a8f92b",
    (
        "sermon",
        "the-drama-of-life-in-three-acts",
    ): "adca10761db69ed794ba425738c0feca61233b2eb7d4d8a3909a55bda12e10a7",
    (
        "sermon",
        "the-excellency-of-christ",
    ): "d767fbe60b9c35373b8bd836bd72c8774d72320d10239e25c7444f5632a775ff",
    (
        "sermon",
        "the-holy-ghost",
    ): "5287a02ab8eac17fbd5926ef60c41b8caed08257423f5e1e1de6e1402ee02feb",
    (
        "sermon",
        "the-most-important-question",
    ): "d52058a4101f8840f5121b053234a6bf61a922f17b976ff3967a9c2388e7946e",
    (
        "sermon",
        "the-office-of-the-holy-spirit",
    ): "48da18d5304071df792b82337f657e66049a6259ab45ca19136d97075c3790bc",
    (
        "sermon",
        "the-possibilities-of-faith",
    ): "48ffa2a1637302fb8e717d73620542add4ca8ba728f910acd2e274c367e545ea",
    (
        "sermon",
        "the-practical-discipline-of-life",
    ): "64292ecfaf9fc0727cf7c02aca37ca9c1ad1de04af99548f52bd38eace074b5b",
    (
        "sermon",
        "the-practical-hope-of-the-lords-coming",
    ): "6c2bca167f9bbe55394bdb69a643b6acfafcf336266e15f6766d3b7fe6c2d181",
    (
        "sermon",
        "the-salt-of-the-earth",
    ): "d41fbf34c3772c025c0973439b8ec45421d0e021d3f7f676a910c273a51f10c3",
    (
        "sermon",
        "the-training-of-children",
    ): "567eeafba440fe655404e99bc82bd55b8446dabf3846c1dc740cd9bf8abc58df",
    (
        "sermon",
        "the-way-of-salvation-made-plain",
    ): "4a331b464bd47ba6d1237a3b305c15ac022a2943ebdb31d34c65608e9f538d1f",
    (
        "sermon",
        "the-worlds-need",
    ): "df550976ce5b2fc53c2b72ba25a8c0c20a362f536d0e7fab5d602553a4573ec3",
    (
        "sermon",
        "the-wrath-of-god",
    ): "632cf8b600ff94f7660dfd17067cb7f3542ef1ff032cbd44f8de222eeda49bfa",
    (
        "sermon",
        "three-fires",
    ): "036082a490bad8003c2436782e8f0a88261a15ee0afbc79ac305381985784973",
    (
        "sermon",
        "under-the-shepherds-care",
    ): "7e24148a2a59dc417ba13cfe3fdd987533f21c00b7fba776c14e5f25089fa3ab",
    (
        "sermon",
        "what-is-revival",
    ): "3932439c1fb047069ef2c8785fbbd757c1614f4b4566ea4b999335e37bf7e283",
    (
        "sermon",
        "what-it-costs-not-to-be-a-christian",
    ): "73f75d5e4243eedf752cf275e10ee0eec617876e0c11de65ffed7f23b8738db1",
    (
        "sermon",
        "witnessing-for-christ",
    ): "2d0c8e184929a0906984d56cc080e144d1ee5b7aaea2d36cdcf1de44b42d4d11",
}


def _digest(parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(typographic_form(p or "").encode("utf-8"))
        h.update(_SEP.encode())
    return h.hexdigest()


def _book_digests(Chapter):
    out, current, h = {}, None, None
    rows = (
        Chapter.objects.order_by("book_id", "order")
        .values_list("book_id", "order", "title", "body_html")
        .iterator(chunk_size=200)
    )
    for book_id, order, title, body in rows:
        if book_id != current:
            if h is not None:
                out[current] = h.hexdigest()
            current, h = book_id, hashlib.sha256()
        for p in (str(order), title, body):
            h.update(typographic_form(p or "").encode("utf-8"))
            h.update(_SEP.encode())
    if h is not None:
        out[current] = h.hexdigest()
    return out


def refingerprint(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    models = {
        "book": apps.get_model("library", "Book"),
        "sermon": apps.get_model("library", "Sermon"),
        "article": apps.get_model("library", "Article"),
    }
    empty = _digest(())  # a book with no chapters, as `_row_digests` gives it
    for kind, model in models.items():
        if kind == "book":
            new = _book_digests(Chapter)
        else:
            title = "title" if kind == "sermon" else "h1"
            new = {
                pk: _digest((t, body))
                for pk, t, body in model.objects.order_by()
                .values_list("pk", title, "body_html")
                .iterator(chunk_size=200)
            }
        rows = list(
            model.objects.only(
                "pk",
                "slug",
                "language",
                "source_type",
                "content_digest",
                "english_digest",
            )
        )
        english_old = {r.slug: r.content_digest for r in rows if r.language == "en"}
        english_new = {r.slug: new.get(r.pk, empty) for r in rows if r.language == "en"}
        for r in rows:
            if r.language != "en" and not is_original(r.language, r.source_type):
                baseline = r.english_digest
                current = (
                    bool(baseline)
                    and r.slug in english_new
                    and (
                        baseline == english_old.get(r.slug)
                        or baseline == PRE_4936.get((kind, r.slug))
                    )
                )
                if current:
                    r.english_digest = english_new[r.slug]
            r.content_digest = new.get(r.pk, empty)
        model.objects.bulk_update(
            rows, ["content_digest", "english_digest"], batch_size=500
        )


def noop(apps, schema_editor):
    """Irreversible: the old-rule digests are not recoverable, and the next
    deploy's refresh would recompute them under whichever rule is current."""


class Migration(migrations.Migration):
    # Also the merge of main's three parallel 0177 leaves.
    dependencies = [
        ("library", "0177_author_tagline"),
        ("library", "0177_languagehealthsnapshot"),
        ("library", "0177_searchdecision_synonym_pinned"),
    ]
    operations = [migrations.RunPython(refingerprint, noop)]
