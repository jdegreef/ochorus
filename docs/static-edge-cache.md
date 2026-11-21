# Cutting Render bandwidth: cache the reader's images at Cloudflare

Render bills every byte its CDN sends out: 25 GB a month is included on the
Pro workspace, then $0.15 per GB. In November 2026 the bill was heading for
about 550 GB, roughly $80 a month. Most of it is images: ~2,500 covers, author
portraits, in-book illustrations, emblems and share cards, served from the
static site (`ochorus-web`) under stable names.

The `server: cloudflare` header on ochorus.com is **Render's** own CDN, which
we can't configure, and anything it serves is billed. A Cloudflare zone of our
own in front of Render answers repeat requests from its edge, and Cloudflare's
free plan doesn't charge for bandwidth. Render then only sends a file when a
Cloudflare edge doesn't have it yet.

Founder action, about 30 minutes plus DNS wait. Nothing in the repo changes.

## 1. Move ochorus.com onto a Cloudflare zone

Follow **section 0 of [seo-edge-rules.md](seo-edge-rules.md)** exactly. It
covers the email DNS records that must stay grey (DNS only), Render's domain
verification, and the SSL mode (Full, never Flexible). Proxy (orange) only
`ochorus.com` and `www`.

Leave `api.ochorus.com` **grey** for now. Caching the API has its own setup
and a build carve-out ([egress-cloudflare.md](egress-cloudflare.md)). Without
that carve-out, the prerender crawl can be rate-limited and fail deploys.

## 2. The cache rule (Caching → Cache Rules → Create rule)

**Name:** `Long edge cache for images`

**Match (Edit expression):**

```
(http.host in {"ochorus.com" "www.ochorus.com"}
 and http.request.method eq "GET"
 and (starts_with(http.request.uri.path, "/covers/")
   or starts_with(http.request.uri.path, "/portraits/")
   or starts_with(http.request.uri.path, "/illustrations/")
   or starts_with(http.request.uri.path, "/emblems/")
   or starts_with(http.request.uri.path, "/og/")
   or starts_with(http.request.uri.path, "/icons/")
   or starts_with(http.request.uri.path, "/marks/")
   or starts_with(http.request.uri.path, "/textures/")
   or starts_with(http.request.uri.path, "/_app/immutable/")))
```

**Then:**

- **Cache eligibility:** Eligible for cache.
- **Edge TTL:** *Ignore cache-control header and use this TTL* → **1 day**.
  The origin says `s-maxage=300`, which is right for Render's CDN (Render
  purges it on every deploy) but would make our edge go back to Render every
  five minutes. Ours is not purged on deploy, so we choose a TTL instead.
- **Browser TTL:** *Respect origin*. `render.yaml`'s `headers:` keep deciding
  what a reader's browser keeps.
- **Cache key:** the defaults.

What the day costs: a cover, portrait or emblem that is redrawn under the same
name can show the old picture for up to a day after its deploy. Covers are the
only ones that change often, and a stale cover is the whole cost. Hand-made
covers never change (`library/designed_covers.py`). `/_app/immutable/` files
are content-hashed, so they are never stale.

When a new picture has to show **now**: Cloudflare → Caching → Configuration →
**Purge Cache → Custom Purge** → paste its URL(s), or **Purge Everything**.
It's safe at any time; the edge just refills from Render.

HTML is deliberately left out. Cloudflare doesn't cache pages by default, and
pages have to show a deploy at once. They are also a small share of the bytes.

## 3. Check it (after a day)

```
curl -sI https://ochorus.com/covers/<any-slug>.png | grep -i cf-cache-status
```

Run it twice: the second answer should be `HIT`. (Today the header reads
`BYPASS` or `DYNAMIC`, which is Render's CDN.)

- Cloudflare → **Analytics → Traffic**: *Percent cached* should climb above
  80%.
- Render → **Billing → Bandwidth**: the daily figure should fall over the next
  week.

## Undo

Turn the `ochorus.com` and `www` records back to grey (DNS only). The site is
plain Render again within a minute. Deleting the rule alone also undoes the
caching.
