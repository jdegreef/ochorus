# Launch checklist — email + the phone apps

The code for both is built. What's left is mostly accounts, DNS and dashboard
settings that only the founder can do. Start the slow items first: **Apple
Developer enrollment, Google Play account verification and Resend domain
verification can each take hours to days.**

Order of work:

| Do today (slow, external) | Then |
|---|---|
| Resend account + `news.ochorus.com` domain + DNS (§1.1–1.2) | Email review mode (§1.4), then live (§1.6) |
| Apple Developer Program enrollment (§2.1) | TestFlight build from the Mac (§2.3) |
| Google Play Console account + identity verification (§2.2) | Internal / closed testing upload (§2.4) |

---

## 1. Email (Resend)

How it works: the API (`backend/emails/`) renders and sends through Resend; the
`ochorus-lifecycle-email` Render cron runs `send_email_cron` every 15 minutes
(onboarding drip, plan reminders, series nudges, milestones, automations, the
auto-built digest, due broadcasts). Resend posts delivery events back to the
API's webhook. Nothing is sent while `EMAIL_ENABLED` is off — sends are
recorded as "skipped".

### 1.1 Resend account and domain

1. Sign up at resend.com. Choose a plan that covers the expected volume
   (Free is 3,000/month and 100/day — fine for review mode, too small for a
   broadcast to the whole list).
2. **Domains → Add domain → `news.ochorus.com`**. Send from this subdomain, not
   the root: the root's reputation (and `support@ochorus.com`) stays safe if a
   campaign goes badly. The code's default From is
   `Ochorus <hello@news.ochorus.com>`.

### 1.2 DNS (at the ochorus.com registrar / DNS host)

Add **exactly the records Resend shows** for `news.ochorus.com`. Typically:

| Type | Name | Purpose |
|---|---|---|
| TXT | `resend._domainkey.news` | DKIM |
| MX | `send.news` → `feedback-smtp.<region>.amazonses.com` (priority 10) | bounce handling (Return-Path) |
| TXT | `send.news` → `v=spf1 include:amazonses.com ~all` | SPF |

Then add DMARC yourself (Resend recommends it; Gmail/Yahoo require it for bulk
senders):

| TXT | `_dmarc.news` | `v=DMARC1; p=none; rua=mailto:support@ochorus.com` |

Start at `p=none`; move to `p=quarantine` after a few clean weeks.

> ⚠️ Add records only. **Don't edit or delete the existing root `MX`/`TXT`
> records** — they carry `support@ochorus.com` (see DEPLOYMENT.md §5).

Click **Verify** in Resend. All records must show green before sending works.

### 1.3 Keys and webhook

1. **API Keys → Create** — permission "Sending access", domain
   `news.ochorus.com`. Copy it (`re_…`).
2. **Webhooks → Add endpoint**:
   - URL: `https://api.ochorus.com/api/emails/webhook/`
   - Events: `email.sent`, `email.delivered`, `email.delivery_delayed`,
     `email.opened`, `email.clicked`, `email.bounced`, `email.complained`,
     `email.failed`.
   - Copy the signing secret (`whsec_…`).

### 1.4 Render env vars — review mode first

On **ochorus-api → Environment** (the cron reads the same values via
`fromService`, so set them once, on the API):

| Key | Value |
|---|---|
| `RESEND_API_KEY` | the `re_…` key |
| `RESEND_WEBHOOK_SECRET` | the `whsec_…` secret |
| `EMAIL_FROM` | `Ochorus <hello@news.ochorus.com>` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API → `service_role` (secret; reads each reader's verified address) |
| `PUBLIC_SITE_URL` | `https://ochorus.com` (CTA and preference-centre links) |
| `API_PUBLIC_URL` | `https://api.ochorus.com` (unsubscribe links; falls back to the `.onrender.com` host if unset) |
| `EMAIL_WELCOME_START` | now, ISO, e.g. `2026-10-21T00:00:00Z` — the welcome drip never mails the back catalogue |
| `EMAIL_ALLOWLIST` | `james.degreef@gmail.com` (plus any reviewers, or `@ochorus.com`) |
| `EMAIL_ENABLED` | `true` |

While `EMAIL_ALLOWLIST` is set, **only those addresses get mail**, on every
path (drip, broadcast, tests). Everyone else is recorded as skipped.

### 1.5 Check the cron exists, then test

1. Render dashboard: is there a cron service named **`ochorus-lifecycle-email`**?
   If not, **Blueprints → ochorus → Sync** (render.yaml changes need a manual
   sync). Its env should show the values above as linked from `ochorus-api`.
2. Admin → Emails: open a broadcast (or a starter template), run the pre-send
   checks, and **Send test** to yourself. Check:
   - it arrives in the inbox, not spam (Gmail: "Show original" → SPF, DKIM and
     DMARC all `PASS`);
   - links open ochorus.com; **Unsubscribe** and **preferences** work;
   - Gmail shows its own "Unsubscribe" link next to the sender (one-click
     `List-Unsubscribe` header);
   - Resend → Webhooks shows `200` deliveries, and the message's opens/clicks
     appear in the admin email history.
3. Sign up a fresh test account with an address that is on the allowlist
   (matching is exact, so a `+tag` alias must be listed itself), then wait for a
   cron tick (≤15 min). The welcome email should arrive.
4. Render → `ochorus-lifecycle-email` → Logs: the last run exits 0.

### 1.6 Go live

1. Clear `EMAIL_ALLOWLIST` (delete the variable).
2. First broadcast: narrow the audience (one language, or recently active
   readers) for the first send, and watch the health panel in Admin → Emails. The guardrail pauses a broadcast
   by itself if bounces pass 5% or complaints pass 0.3% (after 100 sends).
3. Raise `EMAIL_SEND_RATE` only if the Resend plan allows more than 2/s.

### 1.7 Recommended: Supabase sign-in emails through Resend too

Supabase's built-in mailer for sign-up confirmations and password resets is
rate-limited to a handful per hour, which real sign-ups will hit. Supabase →
**Authentication → Emails → SMTP Settings → Enable custom SMTP**:

- Host `smtp.resend.com`, port `465`, user `resend`, password: a Resend API key
- Sender: `Ochorus <no-reply@news.ochorus.com>`

Then raise the email rate limit under **Authentication → Rate Limits**.

---

## 2. Phone apps (iOS + Android)

The app is the same reader, wrapped by Capacitor (`frontend/MOBILE.md`). It
reads signed-out until in-app sign-in ships (MOBILE.md roadmap 3). It can still
ship to the stores that way: no account means no Sign in with Apple
requirement.

### 2.1 Apple Developer Program (start today)

1. developer.apple.com/programs/enroll — **$99/year**.
   - **As an organization** (shows "Ochorus" or the legal entity as the
     seller): needs a **D-U-N-S number** (free from Dun & Bradstreet, can take
     a week or more) and a website on the org's domain.
   - **As an individual**: faster, but your personal name shows as the seller.
2. Two-factor authentication on the Apple ID is required.
3. Once approved: App Store Connect → **Apps → +** → bundle id
   **`com.ochorus.app`** (permanent), name "Ochorus".

### 2.2 Google Play Console (start today)

1. play.google.com/console — **$25 one-time**. Identity verification (and for
   an organization, a D-U-N-S number) takes a few days.
2. ⚠️ **New personal accounts must run a closed test with at least 12 testers
   for 14 continuous days** before they may publish to production.
   Organization accounts are exempt. Line up 12+ testers (Gmail addresses) now
   if you enroll as an individual.
3. Create the app; package name **`com.ochorus.app`**. Enroll in Play App
   Signing (default).

### 2.3 What each store listing needs (gather now)

- **Privacy policy URL**: `https://ochorus.com/legal` (check it covers the app
  and what the app collects — signed-out reading sends page views to the API
  and errors to Sentry).
- **Support URL**: `https://ochorus.com/contact`.
- **Account deletion URL** (Google requires one if the app ever has accounts):
  the web settings page already deletes an account.
- **Privacy labels / Data safety form**: answered from what the app actually
  sends. Signed-out: diagnostics (Sentry crash data) and usage analytics only
  if engagement events fire in the app; no contact info, no tracking, no ads.
- **Screenshots**: iPhone 6.9" (1320×2868) and 6.5", iPad 13" if iPad is
  supported; Android phone (min 2), plus a 1024×500 feature graphic.
- **Icon**: 1024×1024 (from `frontend/resources/`, already generated).
- **Description, short description (Android, 80 chars), keywords (iOS, 100
  chars), category** (Books / Books & Reference), **age rating** questionnaire
  (Everyone / 4+).
- **Content rights**: confirm the texts are public domain (they are) — Apple
  asks about third-party content.

### 2.4 First builds

- **iOS** (on the Mac, `frontend/MOBILE.md`): `npm run app:ios`, set the Team
  to the paid account, bump `CURRENT_PROJECT_VERSION`, **Product → Archive →
  Distribute → App Store Connect**. Then TestFlight → add yourself as an
  internal tester.
- **Android**: Android Studio → **Build → Generate Signed App Bundle** (create
  an upload keystore — **back it up**; losing it means a key reset through
  Google). Upload the `.aab` to **Testing → Internal testing**, then Closed
  testing for the 12-tester rule.

CI uploads (fastlane to TestFlight and Play internal testing) are on the
MOBILE.md roadmap (item 5). They need, as GitHub secrets: an App Store Connect
API key (`.p8` + key id + issuer id), a Google Play service-account JSON, and
the Android upload keystore + passwords. Create those once the accounts exist.

### 2.5 Review pitfalls to avoid

- **Apple 4.2 "minimum functionality"**: an app that's only a website in a
  wrapper can be rejected. Ochorus's native polish (share sheet, system
  browser for outside links, back button, safe areas) and offline reading
  (roadmap 2) are the answers; mention them in the review notes.
- Give reviewers a note that no login is needed to use the app.
- Every upload needs a higher build number than the last.
