package com.ochorus.app.widgets;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import java.util.Calendar;

/**
 * The Today widget: the day's verse, which turns over at local midnight
 * whether or not the app was opened — the snapshot holds the next few days'
 * verses, each dated, and this redraws on the new day:
 *
 *  - an alarm just after the coming midnight (inexact, not waking the phone:
 *    it lands the next time the screen is on, which is when a widget can be
 *    seen; no exact-alarm permission needed);
 *  - the clock or the time zone changing (exempt from the background-broadcast
 *    limits, so they reach a manifest receiver);
 *  - and the system's periodic update (res/xml/widget_today_info.xml), which
 *    also puts the alarm back after a reboot or an app update clears it.
 */
public class TodayWidgetProvider extends AppWidgetProvider {

    static final String ACTION_NEW_DAY = "com.ochorus.app.widgets.NEW_DAY";

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        manager.updateAppWidget(ids, WidgetRenderer.today(context));
        scheduleNewDay(context);
    }

    @Override
    public void onReceive(Context context, Intent intent) {
        super.onReceive(context, intent);
        String action = intent.getAction();
        if (
            ACTION_NEW_DAY.equals(action) ||
            Intent.ACTION_TIME_CHANGED.equals(action) ||
            Intent.ACTION_TIMEZONE_CHANGED.equals(action)
        ) {
            WidgetRenderer.updateAll(context);
            scheduleNewDay(context);
        }
    }

    @Override
    public void onDisabled(Context context) {
        AlarmManager alarms = context.getSystemService(AlarmManager.class);
        if (alarms != null) alarms.cancel(newDayIntent(context));
    }

    private static PendingIntent newDayIntent(Context context) {
        Intent intent = new Intent(context, TodayWidgetProvider.class).setAction(ACTION_NEW_DAY);
        return PendingIntent.getBroadcast(context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    /** An alarm a few seconds after the coming local midnight (replacing any earlier one). */
    static void scheduleNewDay(Context context) {
        AlarmManager alarms = context.getSystemService(AlarmManager.class);
        if (alarms == null) return;
        Calendar midnight = Calendar.getInstance();
        midnight.add(Calendar.DAY_OF_YEAR, 1);
        midnight.set(Calendar.HOUR_OF_DAY, 0);
        midnight.set(Calendar.MINUTE, 0);
        midnight.set(Calendar.SECOND, 5);
        midnight.set(Calendar.MILLISECOND, 0);
        // A 10-minute window: inexact (no SCHEDULE_EXACT_ALARM), but not left to
        // drift for hours as a plain set() may be.
        alarms.setWindow(AlarmManager.RTC, midnight.getTimeInMillis(), 10 * 60 * 1000L, newDayIntent(context));
    }
}
