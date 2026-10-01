<script lang="ts">
	import { auth } from '$lib/auth.svelte';
	import { adminResource } from '$lib/adminResource.svelte';
	import { ADMIN_SECTIONS, opensSection } from '$lib/adminSections';
	import {
		ABILITIES,
		ROLE_NAMES,
		ROLE_SUMMARIES,
		hasAbility,
		humanize,
		languageNames
	} from '$lib/adminHelp';
	import { getAdminRoles } from '$lib/library-admin';

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
	const myLanguages = $derived(
		isSuper ? ['All languages'] : languageNames([...new Set(scopes.flatMap((s) => s.languages))], langNames)
	);
	const roleLine = $derived(myRoles.map((r) => ROLE_NAMES[r] ?? humanize(r)).join(', '));

	// The matrix columns: each preset, then the super admin (who holds everything).
	const columns = $derived([
		...(model.data?.roles ?? []).map((r) => ({ code: r.code, grants: r.grants as Record<string, string> | null })),
		{ code: 'super_admin', grants: null }
	]);

	// A verb's chip, darker the higher it sits on the ladder.
	const VERB_CHIP: Record<string, string> = {
		view: 'bg-surface-2 text-muted',
		suggest: 'border border-border-strong text-text',
		act: 'bg-accent-soft text-accent',
		approve: 'bg-accent text-accent-contrast'
	};
</script>

<svelte:head><title>Admin · Help &amp; roles — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<header class="mb-8 mt-3">
		<p class="eyebrow mb-2 text-accent">Admin · Help</p>
		<h1 class="text-display">How the admin works</h1>
		<p class="mt-2 text-body text-muted">Ochorus keeps a living library of public-domain Christian classics across many languages. This is the room where the library is built, reviewed, and taken live. What you can see and do depends on the access you've been granted.</p>
	</header>

	<!-- Your access: what you can do, with where you do it -->
	<section class="mb-8 rounded-card border border-border bg-surface p-5">
		<div class="flex flex-wrap items-baseline justify-between gap-2">
			<h2 class="text-h3">Your access</h2>
			{#if isSuper || scopes.length}
				<span class="rounded-full bg-accent-soft px-2.5 py-0.5 text-micro font-semibold text-accent">
					{roleLine || 'Custom grants'} · {myLanguages.join(', ')}
				</span>
			{/if}
		</div>
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
	<section class="mb-8">
		<h2 class="mb-3 text-h3">What "access" means</h2>
		<p class="text-body text-muted">Access has two parts: <strong>which area</strong> (a capability, like reviewing or publishing), and <strong>how far you can go</strong> in it (a verb). Each grant is also scoped to one or more <strong>languages</strong>.</p>
		<div class="mt-4 flex flex-col gap-2">
			{#each [['View', 'See the reports and queues in an area.'], ['Suggest', 'Propose work — file a job — but apply nothing live yourself.'], ['Act', 'Make the change (record a review decision, publish an edition…).'], ['Approve', 'Confirm other people’s work, and use the high-stakes controls.']] as [verb, what] (verb)}
				<div class="flex gap-3 rounded-card border border-border bg-surface px-4 py-2.5">
					<span class="mono w-20 shrink-0 font-semibold text-accent">{verb}</span>
					<span class="text-small text-text">{what}</span>
				</div>
			{/each}
		</div>
		<p class="mt-2 text-small text-muted">Verbs stack: someone who can <em>act</em> can also <em>view</em> and <em>suggest</em>.</p>
	</section>

	<!-- Roles: the summaries, then the exact grid from the backend presets -->
	<section class="mb-8">
		<h2 class="mb-3 text-h3">The roles</h2>
		<ul class="flex flex-col gap-2">
			{#each Object.keys(ROLE_SUMMARIES) as code (code)}
				{@const mine = myRoles.includes(code)}
				<li
					class="flex flex-col gap-0.5 rounded-card border px-4 py-2.5 sm:flex-row sm:gap-3 {mine
						? 'border-accent bg-accent-soft'
						: 'border-border bg-surface'}"
				>
					<span class="w-32 shrink-0 text-small font-semibold {mine ? 'text-accent' : 'text-text'}">
						{ROLE_NAMES[code]}{#if mine}<span class="ml-1.5 text-micro font-normal">· you</span>{/if}
					</span>
					<span class="text-small {mine ? 'text-text' : 'text-muted'}">{ROLE_SUMMARIES[code]}</span>
				</li>
			{/each}
		</ul>

		<h3 class="mb-2 mt-6 text-small font-semibold text-text">Exactly what each role can do</h3>
		{#if model.data}
			<div class="overflow-x-auto rounded-card border border-border">
				<table class="w-full text-small">
					<thead>
						<tr class="bg-surface-2 text-left text-muted">
							<th class="px-3 py-2 font-semibold">Area</th>
							{#each columns as col (col.code)}
								<th class="whitespace-nowrap px-3 py-2 text-center font-semibold {myRoles.includes(col.code) ? 'bg-accent-soft text-accent' : ''}">
									{ROLE_NAMES[col.code] ?? humanize(col.code)}{myRoles.includes(col.code) ? ' · you' : ''}
								</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each model.data.capabilities as cap (cap.code)}
							<tr class="border-t border-border">
								<td class="px-3 py-2 text-text">{cap.label}</td>
								{#each columns as col (col.code)}
									{@const verb = col.grants ? col.grants[cap.code] : 'all'}
									<td class="px-3 py-2 text-center {myRoles.includes(col.code) ? 'bg-accent-soft' : ''}">
										{#if verb}
											<span class="inline-block min-w-16 rounded-sm px-1.5 py-0.5 text-micro font-semibold uppercase {VERB_CHIP[verb] ?? VERB_CHIP.approve}">{verb}</span>
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
			<p class="mt-2 text-micro text-muted">Each role's languages are chosen when it's granted. The super admin holds every area in every language.</p>
		{:else if model.error}
			<p class="text-small text-muted">Couldn't load the role details. <button class="font-semibold text-accent hover:underline" onclick={model.load}>Try again</button></p>
		{:else}
			<p class="text-small text-muted">Loading…</p>
		{/if}
	</section>

	<!-- Where things live: every admin section and the access that opens it -->
	<section class="mb-8">
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
							{sec.superOnly
								? 'Super admin only'
								: sec.capability
									? `Needs ${capLabel(sec.capability)}`
									: 'Needs any admin access'}
						</span>
					{/if}
				</li>
			{/each}
		</ul>
	</section>

	<!-- Reviewing -->
	<section class="mb-8">
		<h2 class="mb-2 text-h3">Reviewing — a reviewer proposes, an approver confirms</h2>
		<p class="text-body text-muted">On the review queue, a <strong>reviewer</strong> reads a translation and records a decision. If you hold <em>review</em> at the <em>act</em> level, your approval is <strong>provisional</strong> — it's saved and flagged "awaiting confirmation," but nothing changes until someone with <em>approve</em> (or a super admin) confirms it. That's why your button says "Submit for approval" rather than "Approve." An approver sees your submission and clicks "Confirm."</p>
	</section>

	<!-- How changes reach readers -->
	<section class="mb-8">
		<h2 class="mb-2 text-h3">How changes reach readers</h2>
		<p class="text-body text-muted">The public site is built ahead of time from the project's source files, not edited live. So most content changes — a new translation, a fixed chapter title, a biography — aren't instant database edits; you <strong>file a job</strong>, and it ships as a reviewed change on the next build. That's by design: it keeps every change reviewable. A few things <em>are</em> immediate — taking an edition offline (publish/unpublish), and recording review decisions — and those are the ones gated most tightly.</p>
	</section>

	<!-- Good to know -->
	<section>
		<h2 class="mb-3 text-h3">Good to know</h2>
		<ul class="flex flex-col gap-2">
			{#each ['Everything you do here is recorded in the Activity log — who did what, when.', 'Readers never see review state. "Awaiting review" and AI-translation flags are for this room only, never shown on the public site.', 'You only see the sections your access opens. If something seems missing, that’s your scope, not a bug — ask a super admin.', 'Filing a job changes nothing on its own; it queues work for a person to carry out.'] as tip (tip)}
				<li class="flex gap-2 text-small text-text"><span class="text-accent">·</span>{tip}</li>
			{/each}
		</ul>
	</section>
</div>
