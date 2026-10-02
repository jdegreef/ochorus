<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { adminResource } from '$lib/adminResource.svelte';
	import { ADMIN_SECTIONS, opensSection, sectionRequirement } from '$lib/adminSections';
	import { ABILITIES, hasAbility, humanize, languageNames } from '$lib/adminHelp';
	import { getAdminRoles } from '$lib/library-admin';
	import { scrollSpy } from '$lib/scrollSpy.svelte';

	// The viewer's own access comes from the already-loaded profile; the access
	// model (capability labels, what each role grants) from /api/admin/roles/,
	// which reads the backend presets — so the matrix can't drift from them.
	const model = adminResource(getAdminRoles, 'Something went wrong loading the roles.');

	const isSuper = $derived(auth.isAdmin); // is_admin is the super-admin flag
	const scopes = $derived(auth.scopes === 'all' ? [] : auth.scopes);
	const myRoles = $derived(
		isSuper ? ['super_admin'] : [...new Set(scopes.map((s) => s.role).filter(Boolean))]
	);
	const langNames = $derived(model.data?.languages ?? {});
	const capLabel = (code: string) =>
		model.data?.capabilities.find((c) => c.code === code)?.label ?? humanize(code);
	const myLanguageCodes = $derived([...new Set(scopes.flatMap((s) => s.languages))].sort());
	const myLanguages = $derived(isSuper ? ['All languages'] : languageNames(myLanguageCodes, langNames));
	// Grants that cover fewer languages than the rest — the chips would otherwise
	// claim every grant reaches every one of them. When any grant covers all
	// languages, every grant that doesn't is the narrower one.
	const narrowerGrants = $derived(
		scopes.filter(
			(s) =>
				!s.languages.includes('*') &&
				(myLanguageCodes.includes('*') || s.languages.length < myLanguageCodes.length)
		)
	);
	const roles = $derived(model.data?.roles ?? []);
	const roleLabel = (code: string) => roles.find((r) => r.code === code)?.label ?? humanize(code);
	const roleLine = $derived(myRoles.map(roleLabel).join(', '));

	// The page's sections, in order — the "On this page" rail and its scroll spy
	// both read this list, so a new section is one entry here plus its id.
	const SECTIONS = [
		{ id: 'your-access', label: 'Your access' },
		{ id: 'levels', label: 'Access levels' },
		{ id: 'roles', label: 'The roles' },
		{ id: 'where-things-live', label: 'Where things live' },
		{ id: 'reviewing', label: 'Reviewing' },
		{ id: 'going-live', label: 'Going live' },
		{ id: 'good-to-know', label: 'Good to know' },
		{ id: 'glossary', label: 'Glossary' }
	];
	// The band sits just below the sticky app bar, so a jumped-to section — which
	// lands at the top — is the one lit, not whatever reaches mid-screen.
	const spy = scrollSpy(() => SECTIONS.map((s) => s.id), { rootMargin: '-15% 0px -80% 0px' });
	// The last section is short and may never climb into that band on a tall
	// screen, so at the very bottom of the page it is the one lit.
	$effect(() => {
		const atBottom = () => {
			if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4)
				spy.set(SECTIONS[SECTIONS.length - 1].id);
		};
		window.addEventListener('scroll', atBottom, { passive: true });
		return () => window.removeEventListener('scroll', atBottom);
	});

	// The review hand-off, step by step, with the queue's real button labels
	// (routes/admin/review: "Submit for approval" without approve, then "Confirm").
	const REVIEW_STEPS = [
		{ who: 'Arrives', what: 'AI translation', note: 'Ships unreviewed. Readers can already read it.' },
		{ who: 'Reviewer', what: 'Reads it', note: 'Presses “Submit for approval”.' },
		{ who: 'Waiting', what: 'Provisional', note: 'Saved and flagged. Nothing changes yet.' },
		{ who: 'Approver', what: 'Reviewed', note: 'Presses “Confirm”.' }
	];

	// The admin's own words, defined once.
	const GLOSSARY = [
		['Edition', 'One language’s copy of a work. Teen and children’s versions are separate books with their own editions.'],
		['Job', 'A request for work, filed from the admin. It changes nothing until someone carries it out.'],
		['Unreviewed', 'An AI translation no native speaker has approved yet. Readers can read it; only the admin sees the flag.'],
		['Provisional', 'A review decision waiting for someone with approve to confirm it.'],
		['Go-live', 'Turning a whole language on for readers. Super admin only.'],
		['Next build', 'When a merged change reaches the public site, after the site is rebuilt.']
	];

	// The access ladder, lowest first — each step includes the ones below it.
	const LADDER = [
		{ verb: 'View', what: 'See the reports and queues in an area.' },
		{ verb: 'Suggest', what: 'File a job. Nothing goes live from it.' },
		{ verb: 'Act', what: 'Make the change: record a review, publish an edition.' },
		{ verb: 'Approve', what: 'Confirm other people’s work; use the high-stakes controls.' }
	];

	// Where the Activity log tip links, when the viewer can open the log at all.
	const activity = ADMIN_SECTIONS.find((s) => s.href === '/admin/activity')!;
	const canSeeActivity = $derived(opensSection(activity, auth));

	// A verb's chip, darker the higher it sits on the ladder.
	const VERB_CHIP: Record<string, string> = {
		view: 'bg-surface-2 text-muted',
		suggest: 'border border-border-strong text-text',
		act: 'bg-accent-soft text-accent',
		approve: 'bg-accent text-accent-contrast'
	};
</script>

<svelte:head><title>Admin · Help &amp; roles — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<!-- One column; from xl up, an "On this page" rail sits in the space to its right. -->
<div class="mx-auto max-w-3xl px-5 py-10 xl:grid xl:max-w-5xl xl:grid-cols-[minmax(0,48rem)_11rem] xl:gap-10">
<div class="min-w-0">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<header class="mb-8 mt-3">
		<p class="eyebrow mb-2 text-accent">Admin · Help</p>
		<h1 class="text-display">Help &amp; roles</h1>
		<p class="mt-2 text-body text-muted">What your access lets you do, and how work moves from a filed job to the live site.</p>
	</header>

	<!-- Your access: what you can do, with where you do it -->
	<section id="your-access" class="mb-8 scroll-mt-24 rounded-card border border-border bg-surface p-5">
		<div class="flex flex-wrap items-baseline justify-between gap-2">
			<h2 class="text-h3">Your access</h2>
			{#if isSuper || scopes.length}
				<span class="rounded-full bg-accent-soft px-2.5 py-0.5 text-micro font-semibold text-accent">
					{roleLine || 'Custom grants'}
				</span>
			{/if}
		</div>
		{#if isSuper || scopes.length}
			<div class="mt-2 flex flex-wrap items-center gap-1.5">
				<span class="text-micro text-muted">In</span>
				{#each myLanguages as name (name)}
					<span class="rounded-full border border-border px-2 py-0.5 text-micro font-semibold text-text">{name}</span>
				{/each}
			</div>
			{#each narrowerGrants as g (g.capability)}
				<p class="mt-1 text-micro text-muted">
					{capLabel(g.capability)} covers {languageNames(g.languages, langNames).join(', ')} only.
				</p>
			{/each}
		{/if}
		{#if isSuper || scopes.length}
			<ul class="mt-3 flex flex-col gap-1.5">
				{#each ABILITIES as a (a.label)}
					{@const ok = hasAbility(a, auth.scopes, isSuper)}
					<li class="flex flex-wrap items-baseline justify-between gap-x-3 text-small {ok ? 'text-text' : 'text-muted'}">
						<span>
							<span aria-hidden="true" class={ok ? 'text-accent' : ''}>{ok ? '✓' : '✕'}</span>
							<span class="sr-only">{ok ? 'You can:' : 'You can’t:'}</span>
							{a.label}
						</span>
						{#if ok && a.href}
							<a href={a.href} class="text-small font-semibold text-accent hover:underline">Open →</a>
						{:else if !ok}
							<span class="text-micro">needs {a.superOnly ? 'super admin' : `${capLabel(a.capability)} · ${a.verb}`}</span>
						{/if}
					</li>
				{/each}
			</ul>
			{#if !isSuper}
				<p class="mt-3 text-micro text-muted">Need something you don't have? Ask a super admin to add it on the Team page.</p>
			{/if}
		{:else}
			<p class="mt-2 text-body text-muted">You don't currently hold any admin grants. If you should, ask a super admin to add you on the Team page.</p>
		{/if}
	</section>

	<!-- Verbs -->
	<section id="levels" class="mb-8 scroll-mt-24">
		<h2 class="mb-3 text-h3">What "access" means</h2>
		<p class="text-body text-muted">Access has two parts: <strong>which area</strong> (a capability, like reviewing or publishing), and <strong>how far you can go</strong> in it (a verb). Each grant is also scoped to one or more <strong>languages</strong>.</p>
		<!-- A staircase: each step is taller than the one below it, so "the higher
		     level includes the lower ones" is the picture, not a footnote. -->
		<ol class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4 sm:items-end">
			{#each LADDER as step, i (step.verb)}
				<li
					class="flex flex-col justify-end rounded-card bg-accent-soft p-3 {[
						'sm:min-h-24',
						'sm:min-h-32',
						'sm:min-h-40',
						'sm:min-h-48'
					][i]}"
				>
					<span class="font-semibold text-accent">{step.verb}</span>
					<span class="mt-1 text-micro text-text">{step.what}</span>
				</li>
			{/each}
		</ol>
		<p class="mt-2 text-small text-muted">Each level includes the ones below it: someone who can <em>act</em> can also <em>view</em> and <em>suggest</em>.</p>
	</section>

	<!-- Roles: the summaries, then the exact grid from the backend presets -->
	<section id="roles" class="mb-8 scroll-mt-24">
		<h2 class="mb-3 text-h3">The roles</h2>
		{#if model.data}
			<ul class="flex flex-col gap-2">
				{#each roles as role (role.code)}
					{@const mine = myRoles.includes(role.code)}
					<li
						class="flex flex-col gap-0.5 rounded-card border px-4 py-2.5 sm:flex-row sm:gap-3 {mine
							? 'border-accent bg-accent-soft'
							: 'border-border bg-surface'}"
					>
						<span class="w-32 shrink-0 text-small font-semibold {mine ? 'text-accent' : 'text-text'}">
							{role.label}{#if mine}<span class="ml-1.5 text-micro font-normal">· you</span>{/if}
						</span>
						<span class="text-small {mine ? 'text-text' : 'text-muted'}">{role.summary}</span>
					</li>
				{/each}
			</ul>

			<h3 class="mb-2 mt-6 text-small font-semibold text-text">Exactly what each role can do</h3>
			<div class="overflow-x-auto rounded-card border border-border">
				<table class="w-full text-small">
					<thead>
						<tr class="bg-surface-2 text-left text-muted">
							<th class="px-3 py-2 font-semibold">Area</th>
							{#each roles as col (col.code)}
								<th class="whitespace-nowrap px-3 py-2 text-center font-semibold {myRoles.includes(col.code) ? 'bg-accent-soft text-accent' : ''}">
									{col.label}{myRoles.includes(col.code) ? ' · you' : ''}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each model.data.capabilities as cap (cap.code)}
							<tr class="border-t border-border">
								<td class="px-3 py-2 text-text">{cap.label}</td>
								{#each roles as col (col.code)}
									{@const verb = col.grants[cap.code]}
									<td class="px-3 py-2 text-center {myRoles.includes(col.code) ? 'bg-accent-soft' : ''}">
										{#if verb}
											<span class="inline-block min-w-16 rounded-sm px-1.5 py-0.5 text-micro font-semibold uppercase {VERB_CHIP[verb] ?? VERB_CHIP.view}">{verb}</span>
										{:else}
											<span class="text-muted" aria-label="no access">—</span>
										{/if}
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p class="mt-2 text-micro text-muted">
				Each role's languages are chosen when it's granted. The super admin holds every area in every language.
				{#if isSuper}<a href="/admin/team" class="font-semibold text-accent hover:underline">Grant a role on the Team page →</a>{/if}
			</p>
		{:else if model.error}
			<p class="text-small text-muted">Couldn't load the role details. <button class="font-semibold text-accent hover:underline" onclick={model.load}>Try again</button></p>
		{:else}
			<p class="text-small text-muted">Loading…</p>
		{/if}
	</section>

	<!-- Where things live: every admin section and the access that opens it -->
	<section id="where-things-live" class="mb-8 scroll-mt-24">
		<h2 class="mb-2 text-h3">Where things live</h2>
		<p class="mb-3 text-body text-muted">Every admin section, and the access it needs. If a section is missing from your sidebar, this says why.</p>
		<ul class="overflow-hidden rounded-card border border-border bg-surface">
			{#each ADMIN_SECTIONS as sec (sec.href)}
				{@const ok = opensSection(sec, auth)}
				<li class="flex flex-wrap items-baseline justify-between gap-x-3 border-t border-border px-4 py-2 text-small first:border-t-0">
					{#if ok}
						<a href={sec.href} class="font-semibold text-text hover:text-accent">{sec.label}</a>
						<span class="text-micro font-semibold text-accent">You have this</span>
					{:else}
						<span class="text-muted">{sec.label}</span>
						<span class="text-micro text-muted">
							{sectionRequirement(sec, capLabel)}
						</span>
					{/if}
				</li>
			{/each}
		</ul>
	</section>

	<!-- Reviewing: the hand-off as four steps, with the buttons people press -->
	<section id="reviewing" class="mb-8 scroll-mt-24">
		<h2 class="mb-2 text-h3">Reviewing — a reviewer proposes, an approver confirms</h2>
		<p class="text-body text-muted">If you hold <em>review</em> at the <em>act</em> level, your approval is provisional: it is saved, but nothing changes until someone with <em>approve</em> confirms it.</p>
		<ol class="mt-4 grid gap-2 sm:grid-cols-4">
			{#each REVIEW_STEPS as step, i (step.who)}
				<li
					class="rounded-card border px-3 py-2.5 {i === 2
						? 'border-warning bg-surface-2'
						: i === 3
							? 'border-accent bg-accent-soft'
							: 'border-border bg-surface'}"
				>
					<span class="block text-micro font-semibold uppercase tracking-wide text-muted">{step.who}</span>
					<span class="block text-small font-semibold text-text">{step.what}</span>
					<span class="block text-micro text-muted">{step.note}</span>
				</li>
			{/each}
		</ol>
		<p class="mt-2 text-small text-muted">If you hold <em>approve</em>, your button says “Approve” and the decision applies at once.</p>
	</section>

	<!-- How changes reach readers: the two lanes a change can take -->
	<section id="going-live" class="mb-8 scroll-mt-24">
		<h2 class="mb-2 text-h3">How changes reach readers</h2>
		<p class="text-body text-muted">The public site is built ahead of time from the project's source files, so most changes reach readers on the next build. A few take effect at once, and those are the most tightly controlled.</p>
		<div class="mt-4 overflow-hidden rounded-card border border-border bg-surface">
			<div class="flex flex-col gap-2 border-b border-border px-4 py-3 sm:flex-row sm:items-center sm:gap-4">
				<span class="w-28 shrink-0 text-micro font-semibold uppercase tracking-wide text-danger">Instant</span>
				<ul class="flex flex-wrap gap-2">
					{#each ['Publish or unpublish an edition', 'Record a review decision'] as change (change)}
						<li class="rounded-full border border-border px-2.5 py-0.5 text-micro font-semibold text-text">{change}</li>
					{/each}
				</ul>
			</div>
			<div class="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:gap-4">
				<span class="w-28 shrink-0 text-micro font-semibold uppercase tracking-wide text-accent">Next build</span>
				<ol class="flex flex-wrap items-center gap-x-1.5 gap-y-2 text-small">
					{#each ['File a job', 'Change made as a pull request', 'Reviewed and merged', 'Live after the build'] as stage, i (stage)}
						{#if i}<li aria-hidden="true" class="text-muted">→</li>{/if}
						<li class="rounded-sm px-2 py-1 {i === 3 ? 'bg-accent-soft font-semibold text-accent' : 'bg-surface-2 text-text'}">{stage}</li>
					{/each}
				</ol>
			</div>
		</div>
		<p class="mt-2 text-small text-muted">Next-build changes include new translations, fixed titles, biographies and covers. Every one is reviewed before it ships.</p>
	</section>

	<!-- Good to know -->
	<section id="good-to-know" class="mb-8 scroll-mt-24">
		<h2 class="mb-3 text-h3">Good to know</h2>
		<ul class="flex flex-col gap-2 text-small text-text">
			<li class="flex gap-2">
				<span class="text-accent" aria-hidden="true">·</span>
				<span>
					Everything you do here is recorded in the Activity log: who did what, and when.
					{#if canSeeActivity}<a href={activity.href} class="font-semibold text-accent hover:underline">Open the log →</a>{/if}
				</span>
			</li>
			<li class="flex gap-2">
				<span class="text-accent" aria-hidden="true">·</span>
				<span>Readers never see review state. "Awaiting review" and AI-translation flags are for the admin only, never shown on the public site.</span>
			</li>
			<li class="flex gap-2">
				<span class="text-accent" aria-hidden="true">·</span>
				<span>
					You only see the sections your access opens. If something seems missing, that's your access, not a bug.
					<a href="#where-things-live" class="font-semibold text-accent hover:underline">See what each section needs →</a>
				</span>
			</li>
			<li class="flex gap-2">
				<span class="text-accent" aria-hidden="true">·</span>
				<span>Filing a job changes nothing on its own; it queues work for a person to carry out.</span>
			</li>
		</ul>
	</section>

	<!-- Glossary: the admin's own words, defined once -->
	<section id="glossary" class="scroll-mt-24">
		<h2 class="mb-3 text-h3">Glossary</h2>
		<dl class="grid gap-x-4 gap-y-2 text-small sm:grid-cols-[8rem_minmax(0,1fr)]">
			{#each GLOSSARY as [term, meaning] (term)}
				<dt class="font-semibold text-text">{term}</dt>
				<dd class="mb-1 text-muted sm:mb-0">{meaning}</dd>
			{/each}
		</dl>
	</section>
</div>

<nav aria-label="On this page" class="hidden xl:block">
	<div class="sticky top-[calc(var(--appnav-h,0px)+1.5rem)] mt-24 border-s-2 border-border ps-3">
		<p class="mb-2 text-micro font-semibold text-muted">On this page</p>
		<ul class="flex flex-col gap-1.5 text-small">
			{#each SECTIONS as sec (sec.id)}
				{@const on = spy.active === sec.id}
				<li>
					<a
						href="#{sec.id}"
						onclick={() => spy.set(sec.id)}
						aria-current={on ? 'location' : undefined}
						class="-ms-[14px] block border-s-2 ps-3 hover:text-accent {on
							? 'border-accent font-semibold text-accent'
							: 'border-transparent text-muted'}">{sec.label}</a
					>
				</li>
			{/each}
		</ul>
	</div>
</nav>
</div>
