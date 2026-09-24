#!/usr/bin/env python3
"""Build "Working with Claude — A Field Manual": an 8-page, print-ready A4 guide
in the Ochorus paper theme, with Fraunces + Hanken Grotesk embedded as base64
woff2. Render to PDF with headless Chrome (see render command at the bottom)."""
import base64
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "claude-playbook.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
hanken = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2")
hanken_i = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-italic.woff2")

CSS = """
@font-face { font-family:'Fraunces'; src:url(data:font/woff2;base64,FRAUNCES) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKEN) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKENI) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }
:root{
  --bg:#faf6ef; --surface:#ffffff; --surface-2:#f6f1e7; --text:#221c15; --muted:#6e6358;
  --accent:#3f3d9a; --gold:#b07d22; --border:#e6dccb; --soft:#ecebf7; --soft-b:#d9d7f0;
  --green:#2f6b4f; --red:#a4402f;
  --serif:'Fraunces',Georgia,serif; --sans:'Hanken','Helvetica Neue',Arial,sans-serif;
  --mono:'SF Mono','SFMono-Regular','Menlo','Consolas',monospace;
}
@page { size:A4; margin:0; }
*{ box-sizing:border-box; }
html,body{ margin:0; padding:0; }
body{ font-family:var(--sans); color:var(--text); background:var(--bg);
  font-size:9.1pt; line-height:1.35; -webkit-print-color-adjust:exact; print-color-adjust:exact; }

.page{ width:210mm; height:297mm; padding:11mm 15mm 13mm; position:relative;
  page-break-after:always; overflow:hidden; background:var(--bg); }
.page:last-child{ page-break-after:auto; }

/* running head / foot */
.rh{ display:flex; justify-content:space-between; align-items:baseline;
  border-bottom:1px solid var(--border); padding-bottom:4px; margin-bottom:7px; }
.rh .t{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--gold); }
.rh .n{ font-family:var(--serif); font-size:8.5pt; color:var(--muted); }
.pfoot{ position:absolute; left:15mm; right:15mm; bottom:5mm; display:flex;
  justify-content:space-between; font-size:6.8pt; letter-spacing:.09em;
  text-transform:uppercase; color:#a1968a; border-top:1px solid var(--border); padding-top:4px; }

/* headings */
h1.title{ font-family:var(--serif); font-weight:600; font-size:33pt; line-height:1.02;
  letter-spacing:-.015em; margin:0 0 6px; }
.deck{ font-family:var(--serif); font-style:italic; font-size:12.5pt; color:var(--muted);
  line-height:1.3; margin:0 0 12px; max-width:150mm; }
h2{ font-family:var(--serif); font-weight:600; font-size:15pt; margin:0 0 5px; letter-spacing:-.005em; }
h2 .kicker{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--accent); display:block; margin-bottom:2px; }
h3{ font-family:var(--sans); font-weight:700; font-size:9.6pt; margin:0 0 3px; letter-spacing:-.002em; }
h4{ font-family:var(--sans); font-weight:700; font-size:8pt; letter-spacing:.1em;
  text-transform:uppercase; color:var(--accent); margin:0 0 4px; }
p{ margin:0 0 5px; }
.lede{ color:#463d33; margin:0 0 8px; font-size:9.4pt; }
.sec{ margin-bottom:9px; }
b, strong{ font-weight:700; }
em{ font-style:italic; }
code{ font-family:var(--mono); font-size:8pt; background:var(--soft); color:#322d5a;
  border:1px solid var(--soft-b); border-radius:3px; padding:0 3px; white-space:nowrap; }
a{ color:var(--accent); text-decoration:none; }

/* layout helpers */
.cols{ display:flex; gap:7mm; }
.cols > *{ flex:1; min-width:0; }
.cols3{ display:flex; gap:5mm; }
.cols3 > *{ flex:1; min-width:0; }
.tight p{ margin-bottom:3px; }

/* cards */
.card{ background:var(--surface); border:1px solid var(--border); border-radius:8px;
  padding:7px 10px; margin-bottom:5px; }
.card.acc{ border-left:3px solid var(--accent); }
.card.gold{ border-left:3px solid var(--gold); }
.card.green{ border-left:3px solid var(--green); }
.card.red{ border-left:3px solid var(--red); }
.card p:last-child{ margin-bottom:0; }
.card .why{ color:var(--muted); font-size:8.4pt; }

/* callout */
.callout{ background:var(--soft); border:1px solid var(--soft-b); border-radius:8px;
  padding:9px 12px; margin:0 0 8px; }
.callout .k{ font-weight:700; color:var(--accent); text-transform:uppercase;
  letter-spacing:.1em; font-size:7pt; display:block; margin-bottom:3px; }
.callout p:last-child{ margin-bottom:0; }
.callout.gold{ background:#fbf4e6; border-color:#ecd9b0; }
.callout.gold .k{ color:var(--gold); }

/* numbered loop */
.loop{ display:flex; gap:4px; margin:0 0 8px; }
.loop .step{ flex:1; background:var(--surface); border:1px solid var(--border);
  border-top:3px solid var(--accent); border-radius:7px; padding:7px 8px; }
.loop .step .n{ font-family:var(--serif); font-weight:600; font-size:13pt; color:var(--accent); line-height:1; }
.loop .step h5{ font-family:var(--sans); font-weight:700; font-size:8.4pt; margin:3px 0 2px; }
.loop .step p{ font-size:7.6pt; line-height:1.32; color:#4a4239; margin:0; }

/* tables */
table{ width:100%; border-collapse:collapse; margin:0 0 7px; font-size:8.4pt; }
th{ text-align:left; font-weight:700; font-size:7pt; letter-spacing:.09em; text-transform:uppercase;
  color:var(--accent); border-bottom:1.5px solid var(--soft-b); padding:0 6px 3px 0; vertical-align:bottom; }
td{ border-bottom:1px solid var(--border); padding:3px 6px 3px 0; vertical-align:top; line-height:1.3; }
tr:last-child td{ border-bottom:none; }
td.k{ font-weight:700; white-space:nowrap; }
td code{ white-space:normal; overflow-wrap:anywhere; }
.kv code{ white-space:normal; overflow-wrap:anywhere; }
td.k code{ white-space:nowrap; overflow-wrap:normal; }

/* lists */
ul{ margin:0 0 6px; padding-left:14px; }
ol{ margin:0 0 6px; padding-left:16px; }
li{ margin-bottom:2px; line-height:1.32; }
li::marker{ color:var(--accent); }
ul.tick{ list-style:none; padding-left:0; }
ul.tick li{ padding-left:15px; position:relative; }
ul.tick li:before{ content:'\\2713'; position:absolute; left:0; color:var(--green); font-weight:700; }
ul.cross{ list-style:none; padding-left:0; }
ul.cross li{ padding-left:15px; position:relative; }
ul.cross li:before{ content:'\\00D7'; position:absolute; left:0; color:var(--red); font-weight:700; font-size:10pt; }

/* code block */
pre{ font-family:var(--mono); font-size:7.6pt; line-height:1.45; background:#2a2740; color:#e6e4f5;
  border-radius:7px; padding:8px 10px; margin:0 0 6px; white-space:pre-wrap; word-break:break-word; }
pre .c{ color:#9d97c9; }
pre b{ color:#ffd479; font-weight:600; }
.prompt{ background:var(--soft); border:1px solid var(--soft-b); border-radius:7px;
  padding:7px 10px; margin:0 0 6px; }
.prompt .pl{ font-weight:700; font-size:6.8pt; letter-spacing:.12em; text-transform:uppercase;
  color:var(--accent); display:block; margin-bottom:3px; }
.prompt .q{ font-family:var(--mono); font-size:7.8pt; line-height:1.45; color:#322d5a; display:block; }

/* key/definition rows */
.kv{ display:flex; gap:8px; margin-bottom:3px; }
.kv .kk{ font-weight:700; min-width:26mm; color:var(--text); font-size:8.5pt; }
.kv .vv{ flex:1; font-size:8.5pt; color:#463d33; line-height:1.33; }

/* cover bits */
.mark{ font-family:var(--serif); font-weight:600; letter-spacing:.4em; color:var(--gold);
  font-size:9pt; text-indent:.4em; }
.rule{ width:46px; height:2px; background:var(--accent); margin:9px 0 14px; }
.byline{ color:var(--muted); font-size:8.6pt; margin-bottom:14px; }
.toc{ font-size:8.4pt; }
.toc div{ display:flex; justify-content:space-between; border-bottom:1px dotted var(--border); padding:2.5px 0; }
.toc div span:first-child{ color:var(--text); }
.toc div span:last-child{ color:var(--muted); font-family:var(--serif); }

.badge{ display:inline-block; font-size:6.6pt; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; padding:1px 5px; border-radius:3px; vertical-align:1px;
  background:var(--soft); color:var(--accent); border:1px solid var(--soft-b); }
.badge.g{ background:#e9f2ec; color:var(--green); border-color:#c3ddcd; }
.badge.o{ background:#fbf1de; color:var(--gold); border-color:#ecd9b0; }
"""
CSS = (CSS.replace("FRAUNCES", fraunces).replace("HANKENI", hanken_i)
          .replace("HANKEN", hanken))

TITLES = [
    "The operating model", "Context engineering", "Session craft", "Working in parallel",
    "Verification", "Quality gates & shipping", "Automation & tooling", "Beyond the terminal",
]


def page(i, body, title=None):
    t = title or TITLES[i - 1]
    return f"""<div class="page">
  <div class="rh"><span class="t">Working with Claude &nbsp;·&nbsp; {t}</span><span class="n">{i}</span></div>
  {body}
  <div class="pfoot"><span>Field manual · Ochorus · Take Root · Every Tongue</span><span>Page {i} of 8</span></div>
</div>"""


def page_plain(i, body):
    return f"""<div class="page">
  {body}
  <div class="pfoot"><span>Field manual · Ochorus · Take Root · Every Tongue</span><span>Page {i} of 8</span></div>
</div>"""


# ---------------------------------------------------------------- page 1 ----
P1 = r"""
<div class="mark">OCHORUS &nbsp;·&nbsp; TAKE ROOT &nbsp;·&nbsp; EVERY TONGUE</div>
<div class="rule"></div>
<h1 class="title">Working with Claude</h1>
<p class="deck">A field manual for building three apps with an AI pair &mdash; context,
craft, parallelism, verification, and the gates that keep <code>main</code> green.</p>
<p class="byline">Written against your actual stack: SvelteKit&nbsp;5 + Django/DRF + Supabase on Render,
three sibling repos, many parallel sessions.</p>

<div class="callout">
  <span class="k">The one idea</span>
  <p>Claude&rsquo;s ceiling is set by <strong>the context you engineer</strong>, not the prompt you type.
  A blunt ask against a well-instrumented repo beats a beautiful prompt against a bare one.
  Everything that follows is either a way of putting the right thing in front of the model
  <em>before</em> it starts &mdash; or a way of proving what came out.</p>
</div>

<div class="sec">
  <h2><span class="kicker">The loop</span>Six moves, every task</h2>
  <div class="loop">
    <div class="step"><div class="n">1</div><h5>Frame</h5><p>Goal, constraints, and what &ldquo;done&rdquo; looks like. Point at the files.</p></div>
    <div class="step"><div class="n">2</div><h5>Plan</h5><p>Plan mode for anything with more than one right answer. Approve the plan, not the diff.</p></div>
    <div class="step"><div class="n">3</div><h5>Build</h5><p>Let it work. Interrupt early rather than late &mdash; a wrong direction compounds.</p></div>
    <div class="step"><div class="n">4</div><h5>Verify</h5><p>Run it. Browser, tests, screenshots. A summary is not evidence.</p></div>
    <div class="step"><div class="n">5</div><h5>Review</h5><p><code>/simplify</code>, then <code>/code-review</code>. Fold findings into the same PR.</p></div>
    <div class="step"><div class="n">6</div><h5>Ship</h5><p>CI green, squash-merge, watch the deploy, verify the live site.</p></div>
  </div>
  <p class="lede">The expensive failures all come from skipping 1, 4 or 5. Step&nbsp;3 is the part
  that feels like work and is the part you should be least involved in.</p>
</div>

<div class="sec">
  <h2><span class="kicker">Architecture of memory</span>Four layers of context</h2>
  <div class="cols">
    <div>
      <div class="card acc"><h3>1 &nbsp;CLAUDE.md &mdash; the constitution</h3>
        <p class="why">Always loaded. Rules that apply to every task in that directory. Short, imperative,
        non-obvious only. Nested files (<code>backend/</code>, <code>frontend/</code>) layer on top.</p></div>
      <div class="card gold"><h3>2 &nbsp;Skills &mdash; the playbooks</h3>
        <p class="why">Loaded on demand when their <em>description</em> matches what you asked. Procedure,
        commands, and accumulated failure modes. Where the detail belongs.</p></div>
    </div>
    <div>
      <div class="card green"><h3>3 &nbsp;Memory &mdash; the facts</h3>
        <p class="why">Persists across sessions: who you are, what you decided and why, what you already
        investigated and rejected. Cheap to write, expensive to re-derive.</p></div>
      <div class="card"><h3>4 &nbsp;The session &mdash; transient and yours</h3>
        <p class="why">Everything read, run and said in this window. Finite, costly, and degrading as it
        fills. Curating it is an active job, not a background one.</p></div>
    </div>
  </div>
</div>

<div class="sec">
  <h2><span class="kicker">Contents</span>What&rsquo;s in here</h2>
  <div class="toc">
    <div><span><b>2 &nbsp;Context engineering</b> &mdash; CLAUDE.md, skills, memory: what goes where, and how to write each one</span><span>p. 2</span></div>
    <div><span><b>3 &nbsp;Session craft</b> &mdash; opening moves, plan mode, thinking budget, steering, context hygiene</span><span>p. 3</span></div>
    <div><span><b>4 &nbsp;Working in parallel</b> &mdash; worktrees, subagents, background work, cloud sessions</span><span>p. 4</span></div>
    <div><span><b>5 &nbsp;Verification</b> &mdash; the browser loop, per-repo gates, and the gotchas that fake a pass</span><span>p. 5</span></div>
    <div><span><b>6 &nbsp;Quality gates &amp; shipping</b> &mdash; review levels, PR discipline, merge races, deploys</span><span>p. 6</span></div>
    <div><span><b>7 &nbsp;Automation &amp; tooling</b> &mdash; hooks, MCP, plugins, custom commands, headless runs</span><span>p. 7</span></div>
    <div><span><b>8 &nbsp;Beyond the terminal</b> &mdash; models, the API in your product, and a quick-reference card</span><span>p. 8</span></div>
  </div>
</div>

<div class="callout gold" style="margin-top:10px">
  <span class="k">How to use it</span>
  <p>Read it once end to end, then treat it as a reference: pages&nbsp;2 and&nbsp;7 when you are
  <em>building your setup</em>, pages&nbsp;3 to&nbsp;6 when you are <em>in</em> a task, page&nbsp;8 pinned
  next to the keyboard. Everything here is written against what is already in your repos &mdash; where it
  describes something you don&rsquo;t have yet, that&rsquo;s the suggestion, not an assumption.</p>
</div>
"""

# ---------------------------------------------------------------- page 2 ----
P2 = r"""
<h2><span class="kicker">Layer 1</span>CLAUDE.md is a constitution, not a manual</h2>
<p class="lede">It is loaded on <em>every</em> turn, so every line costs you on every task. A long
CLAUDE.md is a diluted one &mdash; the rule you actually needed is buried among forty you didn&rsquo;t.</p>

<div class="cols">
  <div>
    <div class="card acc"><h3>Write only what isn&rsquo;t derivable</h3>
      <p class="why">If Claude can learn it by reading the code in ten seconds, leave it out. Keep:
      invariants, misconceptions it will otherwise walk into, conventions with no local example,
      and the consequences of getting it wrong.</p></div>
    <div class="card acc"><h3>Lead with the misconception</h3>
      <p class="why">Your root file opens &ldquo;<em>Architecture &mdash; read before &lsquo;fixing&rsquo; the
      frontend</em>&rdquo; and then says SvelteKit is <em>not</em> the server. That single paragraph prevents
      a whole class of confidently wrong work. Every repo has one or two of these.</p></div>
    <div class="card acc"><h3>Give the rule a reason, once</h3>
      <p class="why">&ldquo;A hand-made cover is frozen &mdash; it carries a judgement no data records.&rdquo;
      A rule with a reason generalises to cases you didn&rsquo;t enumerate. A bare prohibition doesn&rsquo;t.</p></div>
    <div class="card acc"><h3>Push procedure out to skills</h3>
      <p class="why">The constitution says <em>what is always true</em>; a skill says <em>how to do
      this one job</em>. Your &ldquo;Playbooks&rdquo; section &mdash; a list of pointers, not procedures &mdash;
      is the right shape.</p></div>
    <div class="card gold"><h3>Prefer a test to a bullet</h3>
      <p class="why">The strongest line in your backend file says a test now enforces the RLS rule and
      the bullet is &ldquo;just context&rdquo;. An executable rule never rots and costs no context. Convert
      bullets into gates whenever you can.</p></div>
  </div>
  <div>
    <h4>Where does this fact belong?</h4>
    <table>
      <tr><th style="width:44%">The fact</th><th>Home</th></tr>
      <tr><td>&ldquo;Never work in the Dropbox copy&rdquo;</td><td><b>CLAUDE.md</b> + a PreToolUse hook</td></tr>
      <tr><td>&ldquo;Compile Paraglide before <code>svelte-check</code>&rdquo;</td><td><b>CLAUDE.md</b> + a PostToolUse hook</td></tr>
      <tr><td>How to import and repair a book</td><td><b>Skill</b> (<code>book-import</code>)</td></tr>
      <tr><td>The Render deploy ordering trap</td><td><b>Skill</b> (<code>deploy</code>)</td></tr>
      <tr><td>&ldquo;We tried normalising fixture whitespace and chose not to&rdquo;</td><td><b>Memory</b></td></tr>
      <tr><td>&ldquo;James prefers X phrasing in PR titles&rdquo;</td><td><b>Memory</b></td></tr>
      <tr><td>What this function does</td><td><b>Nowhere</b> &mdash; it&rsquo;s in the code</td></tr>
      <tr><td>&ldquo;Don&rsquo;t break the build&rdquo;</td><td><b>Nowhere</b> &mdash; it&rsquo;s noise</td></tr>
    </table>
    <div class="callout gold">
      <span class="k">In-session shortcut</span>
      <p>Start a line with <code>#</code> and Claude writes the note into memory or the right
      CLAUDE.md for you. Use it the moment you catch yourself correcting the same thing twice.
      <code>/memory</code> opens the files for editing.</p>
    </div>
  </div>
</div>

<h2 style="margin-top:6px"><span class="kicker">Layer 2</span>Skills: procedures that load themselves</h2>
<div class="cols">
  <div>
    <div class="card"><h3>The description <em>is</em> the trigger</h3>
      <p class="why">Claude sees only each skill&rsquo;s <code>name</code> and <code>description</code>
      until it opens one. Write the description in <b>the symptoms you&rsquo;d type</b>:
      &ldquo;<em>&hellip;when a book reads wrong &mdash; bogus chapter titles, chapters split mid-sentence,
      a missing first letter&hellip;</em>&rdquo; fires; &ldquo;book utilities&rdquo; does not.</p></div>
    <div class="card"><h3>Progressive disclosure</h3>
      <p class="why">Keep <code>SKILL.md</code> to the procedure. Push reference tables into
      <code>references/</code> and anything deterministic into <code>scripts/</code> &mdash; a script that
      always works beats a paragraph asking the model to be careful.</p></div>
    <div class="card"><h3>Living playbooks</h3>
      <p class="why">Every one of yours ends &ldquo;<em>append new failure modes as we find them</em>&rdquo;,
      and a Stop hook nudges the review. The single highest-compounding habit in your setup: each bug
      you hit is paid for once.</p></div>
  </div>
  <div>
    <div class="card red"><h3>Anti-patterns</h3>
      <ul class="cross" style="margin-bottom:0">
        <li>A skill that restates the code &mdash; it drifts, then lies to you.</li>
        <li>A description written for you, not for the trigger.</li>
        <li>Procedure smuggled into CLAUDE.md because it felt important.</li>
        <li>Two overlapping skills: Claude picks one and you never learn which.</li>
        <li>Memory used as a diary. Facts and decisions only, one per file.</li>
      </ul></div>
    <div class="callout">
      <span class="k">Scope</span>
      <p><b>Repo skill</b> (<code>.claude/skills/</code>) &mdash; knowledge about <em>this</em> codebase,
      versioned with it. <b>Plugin skill</b> (your <code>founder-kit</code>) &mdash; anything that spans
      Ochorus, Take Root and Every Tongue. When a repo skill starts being copy-pasted to a sibling,
      that is the signal to promote it into the plugin.</p>
    </div>
  </div>
</div>
"""

# ---------------------------------------------------------------- page 3 ----
P3 = r"""
<h2><span class="kicker">Opening moves</span>Most bad sessions were lost in the first message</h2>
<div class="cols">
  <div>
    <p class="lede">A good opening prompt carries four things: the <b>goal</b>, the <b>constraint</b>,
    the <b>definition of done</b>, and a <b>pointer</b> to where to look. Anything you leave out,
    Claude will guess &mdash; competently, and sometimes not the way you meant.</p>
    <div class="prompt"><span class="pl">Template</span><span class="q">In &lt;repo&gt;, &lt;goal in one sentence&gt;.
Constraints: &lt;the invariant that must not break&gt;.
Done when: &lt;the observable thing&gt;.
Start by reading &lt;file&gt; / running &lt;command&gt;.</span></div>
    <div class="prompt"><span class="pl">Worked example</span><span class="q">In ochorus, the Spanish edition of &lsquo;holiness&rsquo; shows the
English cover. Constraint: designed covers are frozen &mdash; don't
redraw one. Done when the es edition renders a derived ground with
its own title and the digest gates still pass. Start with
library/designed_covers.py and build_derived_grounds.py.</span></div>
    <div class="card red"><h3>The two prompts that waste the most time</h3>
      <ul class="cross" style="margin-bottom:0">
        <li>&ldquo;<em>Fix the bug</em>&rdquo; with no reproduction. Give the input, the observed output,
        and the expected output &mdash; or ask it to reproduce first and report back before fixing.</li>
        <li>&ldquo;<em>Make it better</em>&rdquo;. Better along which axis? Name the axis and the ceiling.</li>
      </ul></div>
  </div>
  <div>
    <h4>Plan before you build</h4>
    <p>Press <b>Shift+Tab</b> to cycle into <b>plan mode</b>: Claude researches and proposes, but
    cannot edit. Use it whenever the task has more than one defensible shape &mdash; schema changes,
    a new route, anything touching the fixture or migrations. <b>Reviewing a plan is ten times
    cheaper than reviewing a diff</b>, and rejecting one costs you nothing.</p>
    <p>Shift+Tab again gives <b>auto-accept</b> mode. Reserve it for work you have already scoped
    and can cheaply throw away &mdash; a worktree branch, never the shared checkout.</p>
    <h4 style="margin-top:8px">Buy thinking when it&rsquo;s worth it</h4>
    <p>The words <code>think</code>, <code>think hard</code> and <code>ultrathink</code> escalate how
    much reasoning Claude spends before acting. Worth it for: race conditions, migration ordering,
    &ldquo;why is this only wrong in production&rdquo;, and any design with a one-way door. Not worth it
    for mechanical edits &mdash; it just costs tokens and latency.</p>
    <div class="callout gold"><span class="k">Rule of thumb</span>
      <p>Escalate thinking when <em>you</em> don&rsquo;t know the answer either. If you already know what
      the fix is and just want it typed, plain mode is faster and just as correct.</p></div>
  </div>
</div>

<h2 style="margin-top:4px"><span class="kicker">Context hygiene</span>The window is a workspace, not a wastebasket</h2>
<div class="cols">
  <div>
    <table>
      <tr><th style="width:30%">Move</th><th>When</th></tr>
      <tr><td class="k"><code>/clear</code></td><td>New task, same repo. Almost always the right call &mdash; a fresh window with a good opening prompt beats a tired one with history.</td></tr>
      <tr><td class="k"><code>/compact</code></td><td>Long task you must continue. Add an instruction: <code>/compact keep the migration plan and the failing test</code>.</td></tr>
      <tr><td class="k"><code>/context</code></td><td>When responses get vague or slow. Shows what is eating the window &mdash; usually a giant file read or an MCP server&rsquo;s tool definitions.</td></tr>
      <tr><td class="k"><code>/resume</code></td><td>Pick up a specific earlier session by name. <code>claude -c</code> continues the most recent.</td></tr>
      <tr><td class="k"><code>/cost</code>&nbsp;/&nbsp;<code>/usage</code></td><td>Before you start a fan-out you can&rsquo;t afford.</td></tr>
    </table>
    <div class="card green"><h3>One job per session</h3>
      <p class="why">The same rule as one job per branch. A session that has already imported a book,
      fixed a migration and argued about CSS is carrying three sets of assumptions into your fourth
      question. Clear it.</p></div>
  </div>
  <div>
    <h4>Steering and repair</h4>
    <div class="kv"><span class="kk">Esc</span><span class="vv">Interrupt <em>now</em>. The moment you see it reading the wrong file or reaching for the wrong approach &mdash; not after the edit lands. Redirect in one sentence.</span></div>
    <div class="kv"><span class="kk">Esc Esc</span><span class="vv">Jump back to an earlier message and take a different branch. Better than arguing forward from a bad state.</span></div>
    <div class="kv"><span class="kk"><code>/rewind</code></span><span class="vv">Restore the conversation and/or the code to an earlier checkpoint. Your undo button for an agent that ran too far.</span></div>
    <div class="kv"><span class="kk"><code>@path</code></span><span class="vv">Pull a specific file into context instead of hoping it searches for it.</span></div>
    <div class="kv"><span class="kk"><code>!cmd</code></span><span class="vv">Run a shell command yourself and put the output in context.</span></div>
    <div class="kv"><span class="kk">Ctrl+V</span><span class="vv">Paste a screenshot. For a visual bug this beats three paragraphs of description.</span></div>
    <div class="callout"><span class="k">Correction beats persuasion</span>
      <p>When output is wrong, don&rsquo;t debate it &mdash; state the correct fact and the constraint it
      violated, then let it redo the step. &ldquo;<em>That reverts the review state; seeds must be
      create-only for fields a workflow owns</em>&rdquo; fixes it. &ldquo;<em>No, that&rsquo;s wrong</em>&rdquo;
      starts a guessing game.</p></div>
  </div>
</div>
"""

# ---------------------------------------------------------------- page 4 ----
P4 = r"""
<h2><span class="kicker">Isolation</span>One worktree, one branch, one job</h2>
<p class="lede">You run many sessions at once across three repos. Everything on this page exists to
stop them from standing on each other &mdash; and the failure mode is not a merge conflict, it&rsquo;s a
<em>clean</em> tree that quietly lost your work.</p>
<div class="cols">
  <div>
    <pre><span class="c"># one isolated worktree per task, off the latest main</span>
git -C ~/dev/take-root fetch origin
git -C ~/dev/take-root worktree add \
    ~/dev/wt-&lt;task&gt; -b &lt;branch&gt; origin/main

<span class="c"># fresh worktrees have no gitignored files</span>
cp ~/dev/take-root/frontend/.env frontend/.env
npm install &amp;&amp; npx @inlang/paraglide-js compile \
    --project ./project.inlang --outdir src/lib/paraglide

<span class="c"># when the branch is merged</span>
git -C ~/dev/take-root worktree remove ~/dev/wt-&lt;task&gt;</pre>
    <div class="card red"><h3>The incident worth remembering</h3>
      <p class="why">Two sessions were handed the same <code>claude/ochorus-dev-*</code> branch. The
      second one&rsquo;s book landed on the first one&rsquo;s open sermon PR and they shipped together under a
      sermon-shaped title. <b>Suffix the job:</b> <code>claude/ochorus-dev-&lt;id&gt;-&lt;job&gt;</code>.
      If you do land on someone else&rsquo;s branch, rebase onto their commits &mdash; never force-push over
      them &mdash; and check your own file survived with <code>md5</code> against
      <code>git show HEAD:&lt;path&gt;</code>. A rebase that replaced your file leaves the tree clean,
      so <code>git status</code> tells you nothing is wrong.</p></div>
    <div class="card gold"><h3>Know where you are, before the first edit</h3>
      <p class="why">Open every session in a worktree with <code>git status -sb</code>. It costs a second
      and catches the two expensive mistakes &mdash; you&rsquo;re on <code>main</code>, or you&rsquo;re in
      the shared checkout &mdash; while they are still free to fix.</p></div>
    <div class="card"><h3>Handing a job between sessions</h3>
      <p class="why">Hand over <em>artefacts</em>, not a conversation: a pushed branch, a PR description
      saying what was verified, a note in the skill. The next session then starts from the repo, not from
      a summary of a summary.</p></div>
  </div>
  <div>
    <h4>Which mechanism for which shape of work?</h4>
    <table>
      <tr><th style="width:34%">Shape</th><th>Mechanism</th></tr>
      <tr><td class="k">Two features at once</td><td>Two <b>worktrees</b>, two terminal sessions. Never two sessions in one checkout.</td></tr>
      <tr><td class="k">&ldquo;Where is X handled?&rdquo; across a big tree</td><td><b>Subagent</b> (Explore). It reads widely and returns the conclusion, not the file dumps &mdash; your window stays clean.</td></tr>
      <tr><td class="k">Review along several axes</td><td><b>Subagents in parallel</b>, one per axis, then you synthesise.</td></tr>
      <tr><td class="k">A long build / test run</td><td><b>Background</b> it and keep working; you&rsquo;re notified when it exits.</td></tr>
      <tr><td class="k">Sequential edits to one file</td><td><b>Stay in the main session.</b> Fan-out here just creates conflicts.</td></tr>
      <tr><td class="k">Poll a deploy or a queue</td><td><code>/loop</code>, or a scheduled agent.</td></tr>
      <tr><td class="k">Work from the sofa / phone</td><td><b>Cloud sessions</b> at claude.ai/code &mdash; Every Tongue is built for exactly this.</td></tr>
    </table>
    <div class="card acc"><h3>Subagents: what they cost</h3>
      <p class="why">A subagent gets a <em>fresh</em> context and returns only its final report. That is
      the whole point &mdash; it protects your window &mdash; but it also means it doesn&rsquo;t know what you
      just discussed. Brief it like a contractor: repo, goal, constraints, and the exact shape of the
      answer you want back.</p></div>
  </div>
</div>

<h2 style="margin-top:4px"><span class="kicker">Throughput</span>Running more than one of you</h2>
<div class="cols3">
  <div class="card"><h3>Cloud sessions</h3>
    <p class="why">GitHub <code>main</code> is the source of truth, no Dropbox in the loop, PRs on
    <code>claude/*</code> branches, CI must pass, and Render gives each PR a preview URL. The safest
    place to run several agents at once, because nothing shares a filesystem.</p></div>
  <div class="card"><h3>Queue-driven work</h3>
    <p class="why">Your translation queue is the model to copy: the admin dashboard files a GitHub
    issue, a session takes <em>one</em> job end-to-end, a conflict gate says which pairs collide.
    Machine-readable work items make parallelism safe.</p></div>
  <div class="card"><h3>Shorthands</h3>
    <p class="why">&ldquo;<b>pq</b>&rdquo; expands to the whole translation-worker playbook. Codifying your
    own three-word triggers in CLAUDE.md is free throughput &mdash; and it forces the procedure to be
    written down once, properly.</p></div>
</div>
<div class="callout gold"><span class="k">The discipline that makes parallelism pay</span>
  <p><code>main</code> moves fast because many sessions land on it. Fetch and reconcile
  <em>immediately</em> before merging, expect fixture and migration conflicts, and never leave a branch
  open overnight you could land today. Parallelism converts wall-clock into merge risk; small,
  single-purpose PRs convert it back.</p></div>
"""

# ---------------------------------------------------------------- page 5 ----
P5 = r"""
<h2><span class="kicker">The rule</span>A summary is not evidence</h2>
<p class="lede">The most common way an AI-assisted change goes wrong is not a bad diff &mdash; it is a
<em>plausible report</em> about a diff nobody ran. Make &ldquo;show me&rdquo; the default.</p>

<div class="cols">
  <div>
    <h4>The browser loop</h4>
    <ol>
      <li>Start the server from <code>.claude/launch.json</code> &mdash; never a raw
      <code>npm run dev</code> in a shell you then lose track of.</li>
      <li>Navigate, then <b>read the page</b> (accessibility tree) rather than screenshotting: it&rsquo;s
      faster, and it proves text and structure, which is what you usually care about.</li>
      <li>Check the console and the network log for errors the UI hides.</li>
      <li>Drive the interaction &mdash; click, type, submit &mdash; and re-read to confirm.</li>
      <li>Resize to mobile and to dark mode if layout or theming moved.</li>
      <li><b>Then</b> screenshot, as proof for you, not as the check itself.</li>
    </ol>
    <div class="card acc"><h3>Keep <code>launch.json</code> honest</h3>
      <p class="why">Yours points into <code>.claude/worktrees/&hellip;</code> &mdash; right for a worktree
      session, wrong once that worktree is gone. Prune it when you remove one, or a future session will
      &ldquo;verify&rdquo; a stale tree and pass.</p></div>
    <div class="card gold"><h3>Verify what the crawler sees, not what the app renders</h3>
      <p class="why">Ochorus prerenders public routes for SEO. A page can look perfect in the browser
      and still ship an empty shell to Google. Check the <em>built HTML on disk</em> contains the real
      title and body &mdash; <code>grep</code> the file in <code>build/</code>, don&rsquo;t trust the tab.</p></div>
  </div>
  <div>
    <h4>Per-repo gates</h4>
    <table>
      <tr><th style="width:26%">Repo</th><th>Run before you even think about a PR</th></tr>
      <tr><td class="k">Ochorus<br><span style="font-weight:400;color:var(--muted)">frontend</span></td>
          <td><code>npm run check</code> &middot; <code>npm run build</code> &middot; <code>npm run sync:catalogues</code> when a locale or an English placeholder is added or removed</td></tr>
      <tr><td class="k">Ochorus<br><span style="font-weight:400;color:var(--muted)">backend</span></td>
          <td><code>makemigrations --check</code> &middot; tests &middot; the fixture gates (pk rows, dangling refs, cover digests)</td></tr>
      <tr><td class="k">Take Root</td>
          <td>Paraglide compile &rarr; <code>npm run check</code> &rarr; <code>npm run build</code>; backend tests with <code>DATABASE_URL=</code> to force SQLite</td></tr>
      <tr><td class="k">Every Tongue</td>
          <td><code>bash bootstrap.sh</code>, then backend tests + <code>npm run check &amp;&amp; npm run build</code>; probe <code>/api/health/</code></td></tr>
    </table>
    <div class="callout"><span class="k">Traps that produce a false green</span>
      <ul style="margin-bottom:0">
        <li><b>Prerender needs the API up.</b> A build that &ldquo;passed&rdquo; with the backend down proves nothing about SEO pages.</li>
        <li><b>Paraglide output is generated, not committed.</b> A fresh worktree fails <code>check</code> until you compile it.</li>
        <li><b><code>backend/.env</code> points at production Supabase.</b> Never run the suite without blanking <code>DATABASE_URL</code>.</li>
        <li><b>A stale <code>vite preview</code></b> serves the previous build happily. Rebuild, then restart it.</li>
        <li><b>Symlinked <code>node_modules</code></b> in a worktree can silently kill hydration.</li>
      </ul></div>
  </div>
</div>

<h2 style="margin-top:2px"><span class="kicker">Prompting for proof</span>Ask for the evidence, not the verdict</h2>
<div class="cols">
  <div>
    <div class="prompt"><span class="pl">Instead of &ldquo;does it work?&rdquo;</span><span class="q">Run it and show me: the failing case before the fix, the
same case after, and the exact command you ran. If you can't
run it, say so &mdash; don't infer.</span></div>
    <div class="prompt"><span class="pl">For a UI change</span><span class="q">Start ochorus-frontend, open /books/&lt;slug&gt;, screenshot at
desktop and mobile, paste any console errors, then say what
a reviewer would object to.</span></div>
  </div>
  <div>
    <div class="card green"><h3>Two questions worth asking every time</h3>
      <p class="why"><b>&ldquo;What did you <em>not</em> verify?&rdquo;</b> &mdash; surfaces the untested branch
      before your users do.<br>
      <b>&ldquo;What would make this wrong?&rdquo;</b> &mdash; invites the model to argue against its own
      change, which it does well and rarely volunteers.</p></div>
    <div class="card"><h3>Make failures loud in the repo</h3>
      <p class="why">Your RLS test, the fixture gates and the cover digests all turn &ldquo;remember to&hellip;&rdquo;
      into &ldquo;CI fails&rdquo;. Every time you catch Claude making the same mistake twice, ask whether it
      should have been a test instead of a sentence.</p></div>
  </div>
</div>

<h2 style="margin-top:2px"><span class="kicker">The ladder</span>Match the proof to the claim</h2>
<table>
  <tr><th style="width:26%">The claim</th><th style="width:37%">What actually settles it</th><th>What doesn&rsquo;t</th></tr>
  <tr><td class="k">&ldquo;It compiles&rdquo;</td><td>A clean <code>check</code> and <code>build</code>, output pasted</td><td>&ldquo;the types look right&rdquo;</td></tr>
  <tr><td class="k">&ldquo;It works&rdquo;</td><td>The interaction driven in a browser, console clean</td><td>A screenshot of the page loading</td></tr>
  <tr><td class="k">&ldquo;It&rsquo;s indexable&rdquo;</td><td>The title and body found in the built HTML on disk</td><td>The tab title in a dev server</td></tr>
  <tr><td class="k">&ldquo;It&rsquo;s live&rdquo;</td><td>A new entry-chunk hash on <code>ochorus.com</code></td><td>A green deploy in the Render dashboard</td></tr>
</table>
"""

# ---------------------------------------------------------------- page 6 ----
P6 = r"""
<h2><span class="kicker">Before the PR</span>Two passes, in this order</h2>
<div class="cols">
  <div>
    <div class="card acc"><h3><code>/simplify</code> &mdash; first</h3>
      <p class="why">Quality only: reuse, simplification, efficiency, altitude. It does not hunt for
      bugs. Run it first because it <em>changes the code</em>, and reviewing simplified code is cheaper
      than reviewing the sprawl that came out of a build session.</p></div>
    <div class="card acc"><h3><code>/code-review high</code> &mdash; second</h3>
      <p class="why">Correctness. Levels are a real dial: <b>low/medium</b> gives few, high-confidence
      findings; <b>high&ndash;max</b> broadens coverage and will include uncertain ones. Use
      <code>high</code> for anything logic-bearing &mdash; migrations, auth, the seed/upsert paths,
      anything touching money or content integrity.</p>
      <p class="why"><code>--fix</code> applies findings to the working tree; <code>--comment</code>
      posts them inline on the PR. <code>/code-review ultra</code> runs a deep multi-agent review in the
      cloud &mdash; save it for a change you&rsquo;d lose sleep over.</p></div>
    <div class="card gold"><h3><code>/security-review</code></h3>
      <p class="why">Worth a run on anything that adds an endpoint, touches
      <code>permission_classes</code>, changes sanitisation, or moves a key. Your DRF default is
      <code>AllowAny</code> &mdash; a forgotten <code>IsAdminEmail</code> ships an open, DB-mutating
      endpoint, and that is a review-shaped bug, not a test-shaped one.</p></div>
    <div class="callout"><span class="k">Fold, don&rsquo;t follow up</span>
      <p>Findings go into <b>the same PR</b>. A &ldquo;cleanup PR to follow&rdquo; is a PR that doesn&rsquo;t
      happen. Your <code>gh pr create</code> hook exists precisely to catch you here.</p></div>
  </div>
  <div>
    <h4>PR discipline</h4>
    <ul class="tick">
      <li><b>One feature per PR.</b> Not because it&rsquo;s tidy &mdash; because a mixed PR can&rsquo;t be reverted.</li>
      <li><b>Explicit paths.</b> Stage the files you meant; <code>git add -A</code> in a worktree with generated output is how junk lands.</li>
      <li><b>Title says what changed for a user</b>, body says why and what you verified. Your history reads well &mdash; keep that.</li>
      <li><b>Check CI before merging</b> (<code>gh pr checks &lt;n&gt;</code>). Render auto-deploys on merge; a red merge is a live outage.</li>
      <li><b>Squash-merge</b>, then delete the branch and remove the worktree.</li>
    </ul>
    <h4 style="margin-top:8px">The merge race</h4>
    <p><code>main</code> moves under you. Fetch and rebase <em>immediately</em> before merging, and
    expect the two conflict classes that actually bite:</p>
    <div class="kv"><span class="kk">Fixtures</span><span class="vv">One file per work makes most collisions impossible &mdash; that design is doing real work for you. Conflicts that remain are usually <code>authors.json</code> appends.</span></div>
    <div class="kv"><span class="kk">Migrations</span><span class="vv">Two branches both numbered <code>0092</code>. Resolve by renumbering and re-checking <code>makemigrations --check</code>, not by deleting one.</span></div>
    <h4 style="margin-top:8px">After the merge</h4>
    <ol>
      <li>Watch <em>both</em> Render services &mdash; the API runs <code>manage.py release</code> (migrate &rarr; seeds &rarr; backfills) as a pre-deploy step, the static site runs its own build.</li>
      <li>Confirm the deploy actually shipped: compare the entry-chunk hash, not the page&rsquo;s appearance.</li>
      <li>Verify on the URL readers use &mdash; <code>ochorus.com</code>, not just the Render hostname.</li>
      <li>If content changed in the DB, remember the static pages need a redeploy to catch up.</li>
    </ol>
  </div>
</div>

<h2 style="margin-top:2px"><span class="kicker">Checklist</span>The last ten minutes before merge</h2>
<div class="cols3">
  <div class="card"><h3>Correctness</h3>
    <ul class="tick" style="margin-bottom:0">
      <li>Gates run <em>after</em> the review fixes, not before.</li>
      <li>Migrations: <code>makemigrations --check</code> is clean and the numbering doesn&rsquo;t collide.</li>
      <li>New endpoint? <code>permission_classes</code> set explicitly.</li>
      <li>New table? RLS on, and the test agrees.</li>
    </ul></div>
  <div class="card"><h3>Hygiene</h3>
    <ul class="tick" style="margin-bottom:0">
      <li>Only the files you meant are staged.</li>
      <li>No generated output committed (Paraglide, build artefacts).</li>
      <li>No secrets, no <code>.env</code>, no prod connection string.</li>
      <li>Debug logging and scratch files removed.</li>
    </ul></div>
  <div class="card"><h3>Blast radius</h3>
    <ul class="tick" style="margin-bottom:0">
      <li>Could this revert human work on the next deploy? (See below.)</li>
      <li>Does it touch a frozen artefact &mdash; a designed cover, an approved translation?</li>
      <li>If it&rsquo;s wrong in production, how do you notice, and how fast can you revert?</li>
    </ul></div>
</div>

<div class="callout gold" style="margin-top:2px"><span class="k">Seeds re-run on every deploy &mdash; the rule that follows from it</span>
  <p>Any field a workflow owns <em>after</em> creation &mdash; review state, a hand-edit, an approval &mdash;
  must be <b>create-only</b> in the seed. Otherwise a perfectly good deploy silently reverts human
  work, and nothing fails. This is the highest-consequence invariant in the whole system and the
  easiest one for an agent to break while &ldquo;improving&rdquo; a seed. Say it out loud in any prompt that
  touches <code>seed_*</code>.</p></div>
"""

# ---------------------------------------------------------------- page 7 ----
P7 = r"""
<h2><span class="kicker">Hooks</span>Turn &ldquo;always remember to&hellip;&rdquo; into code</h2>
<p class="lede">A hook is a shell command the harness runs at a fixed point in the loop. It is the only
mechanism that is <em>guaranteed</em> to fire &mdash; instructions are advisory, hooks are not. Anything
you have written &ldquo;never&rdquo; or &ldquo;always&rdquo; about is a hook candidate.</p>
<div class="cols">
  <div>
    <table>
      <tr><th style="width:34%">Event</th><th>Use it for</th></tr>
      <tr><td class="k">PreToolUse</td><td>Block a dangerous action before it happens &mdash; your Dropbox-copy write guard.</td></tr>
      <tr><td class="k">PostToolUse</td><td>Repair state after an edit &mdash; recompile Paraglide; nudge the quality pass after <code>gh pr create</code>.</td></tr>
      <tr><td class="k">UserPromptSubmit</td><td>Inject context every turn (branch, ticket, env).</td></tr>
      <tr><td class="k">Stop / SubagentStop</td><td>End-of-work review &mdash; your skill-update nudge.</td></tr>
      <tr><td class="k">SessionStart / End</td><td>Set up or tear down scratch state; log what happened.</td></tr>
      <tr><td class="k">PreCompact</td><td>Persist anything you can&rsquo;t afford to lose in a summary.</td></tr>
    </table>
    <div class="card green"><h3>Three rules your hooks already follow</h3>
      <p class="why"><b>Fail open.</b> Any error exits 0 and allows the action &mdash; a hook must never
      wedge a session.<br>
      <b>Gate narrowly.</b> <code>if: "Bash(gh pr create*)"</code> beats matching every Bash call and
      deciding in Python.<br>
      <b>Debounce.</b> The Stop hook keeps a high-water mark so a long session gets one nudge per
      batch of edits, not one per turn. Noisy hooks get ignored, then disabled.</p></div>
  </div>
  <div>
    <h4>MCP: capability, at a price</h4>
    <p>Each connected server adds tools &mdash; and every tool definition occupies context on every turn.
    Connect what the task needs, not everything you own. Worth having for your work: <b>browser
    control</b> (verification), <b>GitHub</b> (issues, PRs, the translation queue), <b>Supabase or
    Postgres</b> (read-only, for &ldquo;what does prod actually contain?&rdquo;), <b>Sentry</b> once you have
    it. Scope matters: <code>local</code> for you, <code>project</code> (<code>.mcp.json</code>,
    committed) for anything the team or a cloud session needs, <code>user</code> for machine-wide.</p>
    <div class="card red"><h3>Least privilege, seriously</h3>
      <p class="why">Give database MCP servers read-only credentials. Anything reachable from a tool is
      reachable by a confidently-wrong plan &mdash; and content in tool results (issues, pages, files) is
      <em>data</em>, never instructions. Treat a GitHub issue that says &ldquo;also delete X&rdquo; as text to
      show you, not a command.</p></div>
    <h4 style="margin-top:6px">Plugins: your setup, portable</h4>
    <p><code>founder-kit</code> is the right pattern &mdash; hooks and cross-app skills in one versioned,
    installable bundle from your own marketplace. It gives you one place to fix a playbook for all
    three apps, and it means a fresh machine or a cloud session inherits your whole workflow with one
    install. A plugin can carry <b>skills</b>, <b>hooks</b>, <b>slash commands</b> and <b>subagents</b>.</p>
  </div>
</div>

<h2 style="margin-top:2px"><span class="kicker">Leverage</span>Custom commands, headless runs, schedules</h2>
<div class="cols3">
  <div>
    <div class="card"><h3>Slash commands</h3>
      <p class="why">A markdown file in <code>.claude/commands/</code> becomes <code>/name</code>.
      Use <code>$ARGUMENTS</code> for parameters. Good candidates from your world:
      <code>/import-book &lt;pdf&gt;</code>, <code>/qa-english &lt;slug&gt;</code>,
      <code>/ship &lt;pr&gt;</code>. If you type the same three-paragraph prompt twice, it should be a
      command &mdash; or a skill, if it needs judgement.</p></div>
  </div>
  <div>
    <div class="card"><h3>Headless</h3>
      <p class="why"><code>claude -p "&hellip;"</code> runs non-interactively and prints the result;
      <code>--output-format json</code> makes it scriptable. Use it in CI and in scripts: draft release
      notes from the diff, triage an issue into a label, run the English QA pass over a batch of
      chapters overnight. Pair it with <code>--allowedTools</code> so an unattended run can&rsquo;t reach
      further than you meant.</p></div>
  </div>
  <div>
    <div class="card"><h3>Recurring work</h3>
      <p class="why"><code>/loop</code> repeats a prompt on an interval &mdash; watching a deploy, draining
      the translation queue. Scheduled agents run on cron without you present: a weekly library QA
      sweep, a Monday digest of open PRs. Give recurring jobs a narrow tool allowlist and a clear
      &ldquo;stop when&rdquo; condition.</p></div>
  </div>
</div>

<h2 style="margin-top:2px"><span class="kicker">Next</span>Three hooks worth writing this week</h2>
<div class="cols3">
  <div class="card acc"><h3>Guard the production database</h3>
    <p class="why"><b>PreToolUse / Bash.</b> Block any <code>manage.py test</code> that doesn&rsquo;t blank
    <code>DATABASE_URL</code>. Take Root&rsquo;s <code>.env</code> points at real Supabase &mdash; today that
    rule is a sentence, one distracted session from being expensive.</p></div>
  <div class="card acc"><h3>Keep the catalogues in sync</h3>
    <p class="why"><b>PostToolUse / Edit.</b> When <code>messages/*.json</code> changes, run
    <code>npm run sync:catalogues -- --check</code> automatically &mdash; the same shape as your Paraglide hook. A
    test already catches it; a hook means you never see the failure.</p></div>
  <div class="card acc"><h3>Announce the branch</h3>
    <p class="why"><b>SessionStart.</b> Print the repo, branch, worktree path, and how far behind
    <code>origin/main</code> it is. Cheap insurance against the branch-collision failure on page&nbsp;4,
    and it puts the answer in context before the first question.</p></div>
</div>

<div class="callout"><span class="k">Fewer interruptions</span>
  <p>Permission prompts train you to click &ldquo;yes&rdquo; without reading, which is the real danger.
  Allowlist the read-only things you approve fifty times a day &mdash; <code>git status</code>,
  <code>git diff</code>, <code>ls</code>, <code>npm run check</code> &mdash; so that when a prompt
  <em>does</em> appear it means something. Keep writes, pushes and deploys on the list.</p></div>
"""

# ---------------------------------------------------------------- page 8 ----
P8 = r"""
<h2><span class="kicker">Model &amp; API</span>Claude inside the product, not just beside it</h2>
<div class="cols">
  <div>
    <h4>Choosing a model</h4>
    <div class="kv"><span class="kk">Opus</span><span class="vv">Hard reasoning, architecture, gnarly debugging, long agentic runs, and any translation or editorial pass where nuance is the product.</span></div>
    <div class="kv"><span class="kk">Sonnet</span><span class="vv">The everyday driver &mdash; most feature work, refactors, review passes. Fast and strong.</span></div>
    <div class="kv"><span class="kk">Haiku</span><span class="vv">High-volume, low-judgement: classification, extraction, formatting a thousand chapters. Cheap enough to run over the whole library.</span></div>
    <p style="margin-top:5px">Switch mid-session with <code>/model</code>. A useful pattern: plan on
    Opus, execute on Sonnet, batch-process on Haiku.</p>
    <div class="card acc"><h3>Patterns your pipelines should use</h3>
      <p class="why"><b>Prompt caching</b> &mdash; a long, stable prefix (style guide, glossary, book
      context) cached across every chapter is a large cost and latency win on exactly your workload.<br>
      <b>Batch processing</b> for anything not interactive &mdash; a whole book&rsquo;s translation at
      a discount.<br>
      <b>Structured output</b> &mdash; force a schema instead of parsing prose. Fewer failure modes,
      and validation happens before your code sees it.<br>
      <b>Evals before scale</b> &mdash; twenty hand-checked chapters tell you more about a prompt change
      than a thousand unchecked ones.</p></div>
    <div class="card green"><h3>You already have the most important guardrail</h3>
      <p class="why">AI translations ship as <code>ai_unreviewed</code>, wear an &ldquo;awaiting native
      review&rdquo; badge, and only a human approval upgrades them. Never auto-approve; never present an
      unreviewed translation as an original. Any new AI feature should copy that shape: <b>generate
      freely, publish only through a human gate.</b></p></div>
  </div>
  <div>
    <h4>Beyond the terminal</h4>
    <p><b>Artifacts</b> for anything with an audience &mdash; a strategy note, a spec, a report someone
    else will read. <b>Projects</b> for a standing context you return to (the style guide, the
    language roadmap). <b>Claude in the browser</b> for the parts of shipping that aren&rsquo;t code:
    dashboards, Render, Supabase config. <b>Voice / mobile</b> for thinking a problem through before
    you sit down to it &mdash; a good plan written on a walk is worth an hour at the keyboard.</p>

    <h4 style="margin-top:8px">Quick reference</h4>
    <table>
      <tr><th style="width:36%">Type this</th><th>To get</th></tr>
      <tr><td class="k">Shift+Tab</td><td>Cycle plan mode / auto-accept</td></tr>
      <tr><td class="k">Esc &nbsp;·&nbsp; Esc Esc</td><td>Interrupt &middot; jump back and re-branch</td></tr>
      <tr><td class="k"><code>#</code> &nbsp;·&nbsp; <code>@</code> &nbsp;·&nbsp; <code>!</code></td><td>Remember &middot; reference a file &middot; run a shell command</td></tr>
      <tr><td class="k"><code>/clear</code> &nbsp;·&nbsp; <code>/compact</code></td><td>Fresh window &middot; summarise and continue</td></tr>
      <tr><td class="k"><code>/context</code> &nbsp;·&nbsp; <code>/cost</code></td><td>What&rsquo;s filling the window &middot; what it cost</td></tr>
      <tr><td class="k"><code>/rewind</code> &nbsp;·&nbsp; <code>/resume</code></td><td>Undo to a checkpoint &middot; reopen a session</td></tr>
      <tr><td class="k"><code>/simplify</code> &nbsp;·&nbsp; <code>/code-review</code></td><td>The two pre-PR passes</td></tr>
      <tr><td class="k"><code>/agents</code> &nbsp;·&nbsp; <code>/mcp</code> &nbsp;·&nbsp; <code>/hooks</code></td><td>Manage subagents &middot; servers &middot; hooks</td></tr>
      <tr><td class="k"><code>claude -c</code> &nbsp;·&nbsp; <code>claude -p</code></td><td>Continue last session &middot; headless run</td></tr>
      <tr><td class="k"><code>/init</code> &nbsp;·&nbsp; <code>/memory</code></td><td>Bootstrap CLAUDE.md &middot; edit memory</td></tr>
    </table>
  </div>
</div>

<h2 style="margin-top:2px"><span class="kicker">The short version</span>Twelve habits</h2>
<div class="cols3" style="font-size:8.4pt">
  <div>
    <p><b>1. Frame before you ask.</b> Goal, constraint, done, pointer.</p>
    <p><b>2. Plan mode for anything with two right answers.</b> Reviewing a plan is ten times cheaper than reviewing a diff.</p>
    <p><b>3. One job per session, per branch, per worktree, per PR.</b></p>
    <p><b>4. Interrupt early.</b> The cost of a wrong direction compounds every turn.</p>
  </div>
  <div>
    <p><b>5. Never accept a report as proof.</b> Ask for the command and its output.</p>
    <p><b>6. Prefer a test to a sentence.</b> A rule in CI never rots; a rule in prose does.</p>
    <p><b>7. Write down every failure the moment it happens</b> &mdash; into the skill, not into your head.</p>
    <p><b>8. Curate the context window</b> the way you&rsquo;d curate a workbench.</p>
  </div>
  <div>
    <p><b>9. <code>/simplify</code> then <code>/code-review</code>, folded into the same PR.</b></p>
    <p><b>10. Fetch immediately before merging.</b> <code>main</code> moved while you were reading this.</p>
    <p><b>11. Generate freely; publish through a human gate.</b></p>
    <p><b>12. When you correct the same thing twice, that&rsquo;s a bug in your setup</b> &mdash; not in the model. Fix the setup.</p>
  </div>
</div>

<h2 style="margin-top:4px"><span class="kicker">Honest assessment</span>Where you&rsquo;re strong, and where to push</h2>
<div class="cols">
  <div>
    <div class="card green"><h3>Already ahead of most</h3>
      <p class="why">Short, opinionated CLAUDE.md files that lead with the misconception. Living-playbook
      skills with real failure modes in them. A plugin that carries hooks and playbooks across three
      repos. Invariants enforced by tests rather than by prose. A human approval gate on AI output.
      Worktree isolation with a written record of the incident that taught you why.</p></div>
  </div>
  <div>
    <div class="card gold"><h3>The next three moves</h3>
      <p class="why"><b>1.</b> Turn the remaining &ldquo;never&rdquo; sentences into hooks or tests &mdash;
      start with the production-database guard.<br>
      <b>2.</b> Make verification the default rather than a request: put the browser loop and the per-repo
      gates into a <code>verify</code> skill that every ship playbook calls.<br>
      <b>3.</b> Promote whatever you&rsquo;ve copy-pasted between Ochorus and Take Root into
      <code>founder-kit</code>, so Every Tongue inherits it on day one instead of re-earning it.</p></div>
  </div>
</div>
"""

DOC = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<title>Working with Claude — A Field Manual</title><style>" + CSS + "</style></head><body>"
       + page_plain(1, P1)
       + page(2, P2) + page(3, P3) + page(4, P4) + page(5, P5)
       + page(6, P6) + page(7, P7) + page(8, P8)
       + "</body></html>")

OUT.write_text(DOC, encoding="utf-8")
print(f"wrote {OUT} ({len(DOC)//1024} KB, fonts embedded)")

# Render to PDF (A4, 8 pages):
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
#     --disable-gpu --no-pdf-header-footer --virtual-time-budget=6000 \
#     --print-to-pdf=claude-playbook.pdf "file://$PWD/claude-playbook.html"
