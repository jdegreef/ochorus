<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getMyWork } from '$lib/library-admin';
	import { relativeTime } from '$lib/relativeTime';

	const res = adminResource(getMyWork, 'Something went wrong loading your work.');
	const ago = (iso: string) => relativeTime(Date.parse(iso), 'en', 'just now');
</script>

<svelte:head>
	<title>Admin · My work — Ochorus</title><meta name="robots" content="noindex" />
</svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<a href="/admin" class="text-small text-accent hover:underline">← Back to dashboard</a>

	<AdminGate
		resource={res}
		errorTitle="Couldn't load your work"
		loadingText="Loading…"
		panelClass="mt-6"
	>
		{#snippet children(d)}
			<header class="mb-6 mt-3">
				<p class="eyebrow mb-2 text-accent">Admin · Overview</p>
				<h1 class="text-display">My work</h1>
				<p class="mt-2 text-body text-muted">
					What is waiting on you: feedback assigned to you, review decisions that need your
					confirmation, and emails you started. Oldest first. The queues themselves hold everything
					else.
				</p>
			</header>

			{#if !d.sections.length}
				<p class="rounded-card border border-border bg-surface p-5 text-body text-muted">
					Your access doesn't include any queues that can be assigned to you.
				</p>
			{:else if !d.total}
				<p class="mb-6 rounded-card border border-border bg-surface p-5 text-body text-muted">
					Nothing is waiting on you right now.
				</p>
			{/if}

			{#each d.sections as s (s.key)}
				<section class="mb-8">
					<div class="mb-3 flex items-baseline justify-between gap-3">
						<h2 class="text-h3">{s.title} <span class="text-muted">· {s.items.length}</span></h2>
						<a href={s.href} class="text-small text-accent hover:underline">Open the queue →</a>
					</div>
					{#if s.items.length}
						<ul class="divide-y divide-border rounded-card border border-border bg-surface">
							{#each s.items as i (i.id)}
								<li>
									<a
										href={i.href}
										class="flex items-baseline justify-between gap-3 px-4 py-3 hover:bg-surface-2 hover:no-underline"
									>
										<span class="min-w-0">
											<span class="block truncate font-semibold text-text">{i.label}</span>
											<span class="text-small text-muted">{i.meta}</span>
										</span>
										<span class="shrink-0 text-small text-muted">{ago(i.at)}</span>
									</a>
								</li>
							{/each}
						</ul>
					{:else}
						<p class="text-small text-muted">{s.empty}</p>
					{/if}
				</section>
			{/each}
		{/snippet}
	</AdminGate>
</div>
