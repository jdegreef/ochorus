package com.ochorus.app.widgets;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.Uri;
import android.view.View;
import android.widget.RemoteViews;
import com.ochorus.app.MainActivity;
import com.ochorus.app.R;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Draws the two widgets from the stored snapshot. Every word comes from the
 * snapshot, already in the reader's language; only the placeholder shown
 * before the app has ever sent one comes from this app's string resources.
 * Colours are resources with a values-night twin, so each widget follows the
 * phone's light or dark mode.
 */
final class WidgetRenderer {

    private WidgetRenderer() {}

    /** Redraw every placed Today and Continue widget. */
    static void updateAll(Context context) {
        AppWidgetManager manager = AppWidgetManager.getInstance(context);
        int[] today = manager.getAppWidgetIds(new ComponentName(context, TodayWidgetProvider.class));
        if (today.length > 0) manager.updateAppWidget(today, today(context));
        int[] cont = manager.getAppWidgetIds(new ComponentName(context, ContinueWidgetProvider.class));
        if (cont.length > 0) manager.updateAppWidget(cont, cont(context));
    }

    /** The reader's local date, as the snapshot dates its verses. */
    static String todayKey() {
        return new SimpleDateFormat("yyyy-MM-dd", Locale.US).format(new Date());
    }

    static RemoteViews today(Context context) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_today);
        JSONObject snapshot = WidgetStore.snapshot(context);
        if (snapshot == null) {
            views.setOnClickPendingIntent(android.R.id.background, open(context, null, 1));
            return views;
        }
        direction(views, snapshot);
        JSONObject labels = snapshot.optJSONObject("labels");
        JSONObject urls = snapshot.optJSONObject("urls");
        JSONArray verses = snapshot.optJSONArray("verses");
        List<String> dates = new ArrayList<>();
        for (int i = 0; verses != null && i < verses.length(); i++) {
            JSONObject verse = verses.optJSONObject(i);
            dates.add(verse == null ? null : verse.optString("date", null));
        }
        VersePicker.Pick pick = VersePicker.pick(dates, todayKey());
        if (pick == null) {
            // This language has no devotionals (or the clock went back): the app.
            views.setTextViewText(R.id.today_eyebrow, context.getString(R.string.app_name));
            views.setTextViewText(R.id.today_text, text(labels, "start"));
            views.setViewVisibility(R.id.today_ref, View.GONE);
            views.setContentDescription(android.R.id.background, text(labels, "start"));
            views.setOnClickPendingIntent(android.R.id.background, open(context, text(urls, "home"), 1));
            return views;
        }
        JSONObject verse = verses.optJSONObject(pick.index);
        String eyebrow = text(labels, "today");
        String body = text(verse, "text");
        String ref = text(verse, "ref");
        // Past the last stored day: the verse, but no claim that it is today's.
        views.setViewVisibility(R.id.today_eyebrow, pick.stale ? View.GONE : View.VISIBLE);
        views.setTextViewText(R.id.today_eyebrow, eyebrow);
        views.setTextViewText(R.id.today_text, body);
        views.setTextViewText(R.id.today_ref, ref);
        views.setViewVisibility(R.id.today_ref, View.VISIBLE);
        String said = body + " — " + ref;
        views.setContentDescription(android.R.id.background, pick.stale ? said : eyebrow + ". " + said);
        views.setOnClickPendingIntent(android.R.id.background, open(context, text(urls, "today"), 1));
        return views;
    }

    static RemoteViews cont(Context context) {
        RemoteViews views = new RemoteViews(context.getPackageName(), R.layout.widget_continue);
        JSONObject snapshot = WidgetStore.snapshot(context);
        if (snapshot == null) {
            views.setOnClickPendingIntent(android.R.id.background, open(context, null, 2));
            return views;
        }
        direction(views, snapshot);
        JSONObject labels = snapshot.optJSONObject("labels");
        JSONObject urls = snapshot.optJSONObject("urls");
        JSONObject book = snapshot.optJSONObject("book");
        views.setTextViewText(R.id.continue_eyebrow, text(labels, "continue"));
        if (book == null) {
            views.setViewVisibility(R.id.continue_cover, View.GONE);
            views.setViewVisibility(R.id.continue_chapter, View.GONE);
            views.setViewVisibility(R.id.continue_progress, View.GONE);
            views.setTextViewText(R.id.continue_title, text(labels, "start"));
            views.setContentDescription(android.R.id.background, text(labels, "start"));
            views.setOnClickPendingIntent(android.R.id.background, open(context, text(urls, "books"), 2));
            return views;
        }
        views.setViewVisibility(R.id.continue_cover, View.VISIBLE);
        Integer color = color(book.optString("coverColor", null));
        if (color != null) views.setInt(R.id.continue_cover, "setBackgroundColor", color);
        Bitmap cover = WidgetStore.cover(context);
        if (cover != null) {
            views.setImageViewBitmap(R.id.continue_cover_image, cover);
            views.setViewVisibility(R.id.continue_cover_image, View.VISIBLE);
        } else {
            views.setViewVisibility(R.id.continue_cover_image, View.GONE);
        }
        views.setTextViewText(R.id.continue_title, text(book, "title"));
        views.setTextViewText(R.id.continue_chapter, text(book, "chapter"));
        views.setViewVisibility(R.id.continue_chapter, View.VISIBLE);
        views.setProgressBar(R.id.continue_progress, 100, Math.max(0, Math.min(100, book.optInt("pct"))), false);
        views.setViewVisibility(R.id.continue_progress, View.VISIBLE);
        views.setContentDescription(android.R.id.background, text(book, "description"));
        views.setOnClickPendingIntent(android.R.id.background, open(context, text(book, "url"), 2));
        return views;
    }

    /** Lay the widget out in the snapshot's direction (Arabic: right to left),
     *  whatever the phone's own language is. */
    private static void direction(RemoteViews views, JSONObject snapshot) {
        int dir = snapshot.optBoolean("rtl") ? View.LAYOUT_DIRECTION_RTL : View.LAYOUT_DIRECTION_LTR;
        views.setInt(android.R.id.background, "setLayoutDirection", dir);
    }

    private static String text(JSONObject object, String key) {
        return object == null ? "" : object.optString(key, "");
    }

    private static Integer color(String hex) {
        if (hex == null || !hex.matches("#[0-9a-fA-F]{6}")) return null;
        return Color.parseColor(hex);
    }

    /**
     * Open the app — on {@code url}'s page when it is one of ochorus.com's
     * (https; the web view routes it, see $lib/platform's startAppShell). The
     * intent names MainActivity, so no browser can answer it.
     */
    private static PendingIntent open(Context context, String url, int requestCode) {
        Intent intent = new Intent(context, MainActivity.class);
        if (url != null && url.startsWith("https://")) {
            intent.setAction(Intent.ACTION_VIEW);
            intent.setData(Uri.parse(url));
        } else {
            intent.setAction(Intent.ACTION_MAIN);
            intent.addCategory(Intent.CATEGORY_LAUNCHER);
        }
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        return PendingIntent.getActivity(
            context,
            requestCode,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
    }
}
