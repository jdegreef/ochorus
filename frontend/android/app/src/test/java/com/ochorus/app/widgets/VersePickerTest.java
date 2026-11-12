package com.ochorus.app.widgets;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import org.junit.Test;

/** The Today widget's midnight rule — the same cases as widgetSnapshot.test.ts. */
public class VersePickerTest {

    private final List<String> days = Arrays.asList("2026-11-12", "2026-11-13", "2026-11-14");

    @Test
    public void showsTheVerseDatedToday() {
        VersePicker.Pick pick = VersePicker.pick(days, "2026-11-13");
        assertEquals(1, pick.index);
        assertFalse(pick.stale);
    }

    @Test
    public void pastTheLastDayKeepsTheLastVerseUndated() {
        VersePicker.Pick pick = VersePicker.pick(days, "2026-11-20");
        assertEquals(2, pick.index);
        assertTrue(pick.stale);
    }

    @Test
    public void fillsAGapWithTheLatestEarlierVerse() {
        VersePicker.Pick pick = VersePicker.pick(Arrays.asList("2026-11-12", "2026-11-14"), "2026-11-13");
        assertEquals(0, pick.index);
        assertTrue(pick.stale);
    }

    @Test
    public void showsNothingBeforeTheFirstVerseOrWithNone() {
        assertNull(VersePicker.pick(days, "2026-11-01"));
        assertNull(VersePicker.pick(Collections.<String>emptyList(), "2026-11-12"));
    }
}
