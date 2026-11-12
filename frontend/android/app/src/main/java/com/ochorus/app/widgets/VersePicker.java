package com.ochorus.app.widgets;

import java.util.List;

/**
 * Which stored verse the Today widget shows on a local date: the one dated
 * today; else the latest before today, "stale" (drawn without the "Verse for
 * today" eyebrow, so an old verse never wears today's date); else none.
 *
 * The same rule as pickVerseDay in frontend/src/lib/widgetSnapshot.ts, which
 * the web tests pin — keep the two (and iOS's pickVerse) in step. Pure Java,
 * so it is unit-tested without a device.
 */
public final class VersePicker {

    private VersePicker() {}

    /** The chosen index into {@code dates} and whether it is stale, or null. */
    public static Pick pick(List<String> dates, String today) {
        int best = -1;
        for (int i = 0; i < dates.size(); i++) {
            String date = dates.get(i);
            if (date == null) continue;
            if (date.equals(today)) return new Pick(i, false);
            // YYYY-MM-DD sorts as text.
            if (date.compareTo(today) < 0 && (best < 0 || date.compareTo(dates.get(best)) > 0)) best = i;
        }
        return best < 0 ? null : new Pick(best, true);
    }

    public static final class Pick {

        public final int index;
        public final boolean stale;

        Pick(int index, boolean stale) {
            this.index = index;
            this.stale = stale;
        }
    }
}
