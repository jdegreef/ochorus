<script lang="ts">
	import { auth } from '$lib/auth.svelte';

	// The viewer's own access, from the already-loaded profile (no API call).
	const isSuper = $derived(auth.isAdmin); // is_admin is the super-admin flag
	const scopes = $derived(auth.scopes === 'all' ? [] : auth.scopes);
	const roles = $derived(
		auth.scopes === 'all' ? ['super admin'] : [...new Set(scopes.map((s) => s.role).filter(Boolean))]
	);
</script>

<svelte:head><title>Admin · Help &amp; roles — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-3xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<header class="mb-8 mt-3">
		<p class="eyebrow mb-2 text-accent">Admin · Help</p>
		<h1 class="text-display">How the admin works</h1>
		<p class="mt-2 text-body text-muted">Ochorus keeps a living library of public-domain Christian classics across many languages. This is the room where the library is built, reviewed, and taken live. What you can see and do depends on the access you've been granted.</p>
	</header>

	<!-- Your access -->
	<section class="mb-8 rounded-card border border-border bg-surface p-5">
		<h2 class="text-h3">Your access</h2>
		{#if isSuper}
			<p class="mt-2 text-body text-text">You're a <strong>super admin</strong> — full access, including granting access to others on the Team page.</p>
		{:else if scopes.length}
			<p class="mt-2 text-body text-text">You hold {roles.length ? `the ${roles.join(', ')} role` : 'these grants'}:</p>
			<ul class="mt-2 flex flex-col gap-1">
				{#each scopes as s (s.capability)}
					<li class="text-small text-muted"><code class="text-text">{s.capability}</code> · {s.verb} · {s.languages.join(', ')}</li>
				{/each}
			</ul>
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

	<!-- Roles -->
	<section class="mb-8">
		<h2 class="mb-3 text-h3">The roles</h2>
		<div class="overflow-x-auto rounded-card border border-border">
			<table class="w-full text-small">
				<thead>
					<tr class="bg-surface-2 text-left text-muted">
						<th class="px-3 py-2 font-semibold">Role</th>
						<th class="px-3 py-2 font-semibold">Can</th>
					</tr>
				</thead>
				<tbody>
					<tr class="border-t border-border"><td class="px-3 py-2 font-semibold text-text">Contributor</td><td class="px-3 py-2 text-muted">View the library and queues; suggest work (file translation / content-fix jobs). Applies nothing live.</td></tr>
					<tr class="border-t border-border"><td class="px-3 py-2 font-semibold text-text">Reviewer</td><td class="px-3 py-2 text-muted">Everything a contributor can, plus record review decisions on their language(s) — see "Reviewing" below.</td></tr>
					<tr class="border-t border-border"><td class="px-3 py-2 font-semibold text-text">Language admin</td><td class="px-3 py-2 text-muted">Act &amp; approve within their language(s) — publish, confirm reviews.</td></tr>
					<tr class="border-t border-border"><td class="px-3 py-2 font-semibold text-text">Super admin</td><td class="px-3 py-2 text-muted">Everything, including granting access and taking a language live.</td></tr>
				</tbody>
			</table>
		</div>
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
