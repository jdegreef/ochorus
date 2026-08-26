<script lang="ts">
	import { adminResource } from '$lib/adminResource.svelte';
	import AdminGate from '$lib/components/AdminGate.svelte';
	import { getAdminActivity, type AdminActionRow } from '$lib/library-admin';

	const activity = adminResource(getAdminActivity, 'Something went wrong loading activity.');
	const data = $derived(activity.data);

	const when = (iso: string) =>
		new Date(iso).toLocaleString('en', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});

	/**
	 * The detail, as a line rather than a JSON blob. Each endpoint records a
	 * small flat object of the things worth keeping, so rendering it generically
	 * means a new action reads properly here without an edit.
	 */
	function summarise(detail: Record<string, unknown>): string {
		return Object.entries(detail)
			.filter(([, v]) => v !== '' && v !== null && v !== undefined)
			.map(([k, v]) => {
				const label = k.replace(/_/g, ' ');
				if (typeof v === 'boolean') return v ? label : `not ${label}`;
				if (Array.isArray(v)) return `${label}: ${v.join(', ')}`;
				if (v && typeof v === 'object') return `${label}: ${Object.keys(v).length}`;
				return `${label}: ${v}`;
			})
			.join(' · ');
	}

	// Colour carries meaning here rather than decoration: taking a language live
	// and publishing a document are the two that reach readers.
	const tone = (a: AdminActionRow) =>
		a.action === 'language.go_live' || a.action === 'content.publish'
			? 'border-accent-soft-border bg-accent-soft text-accent'
			: 'border-border text-muted';
</script>

<svelte:head><title>Admin · Activity — Ochorus</title><meta name="robots" content="noindex" /></svelte:head>

<div class="mx-auto max-w-4xl px-5 py-10">
	<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
		<div>
			<p class="eyebrow mb-2 text-accent">Admin</p>
			<h1 class="text-display">Activity</h1>
			<p class="mt-2 text-body text-muted">
				Every change made from this dashboard — who, what and when. Append-only.
			</p>
		</div>
		{#if data}
			<button class="btn btn-ghost" onclick={activity.load} disabled={activity.loading}
				>{activity.loading ? 'Refreshing…' : 'Refresh'}</button
			>
		{/if}
	</header>

	<AdminGate resource={activity} errorTitle="Couldn't load activity">
		{#snippet children(d)}
			{#if d.actions.length === 0}
				<div class="rounded-card border border-border bg-surface p-8 text-center">
					<p class="text-h3">Nothing recorded yet</p>
					<p class="mt-1 text-body text-muted">
						Creating a language, publishing a document or deciding a review will show up here.
					</p>
				</div>
			{:else}
				{#if d.total > d.actions.length}
					<p class="mb-3 text-small text-muted">
						Showing the most recent {d.actions.length} of {d.total}.
					</p>
				{/if}
				<ul class="overflow-hidden rounded-card border border-border bg-surface">
					{#each d.actions as a (a.at + a.action + a.target)}
						<li class="border-b border-border p-4 last:border-0">
							<div class="flex flex-wrap items-baseline justify-between gap-2">
								<span
									class="shrink-0 rounded-full border px-2.5 py-0.5 text-small font-semibold {tone(a)}"
									>{a.label}</span
								>
								<span class="text-small tabular-nums text-muted">{when(a.at)}</span>
							</div>
							<p class="mt-2 text-body text-text">
								<span class="font-medium">{a.target || '—'}</span>
								<!-- Blank only for a DEBUG loopback request, which has no token to
								     name; saying so beats printing an empty gap. -->
								<span class="text-small text-muted">
									by {a.actor || 'a local dev request'}</span
								>
							</p>
							{#if summarise(a.detail)}
								<p class="mt-1 text-small text-muted">{summarise(a.detail)}</p>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		{/snippet}
	</AdminGate>
</div>
