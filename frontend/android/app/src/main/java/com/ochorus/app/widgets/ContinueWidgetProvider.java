package com.ochorus.app.widgets;

import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;

/**
 * The Continue widget: the book the reader is in — cover, title, chapter and
 * a progress bar — opening the reader at their place. It changes only when the
 * reader reads, which happens in the app, so the app redraws it (through
 * OchorusWidgetsPlugin) and the system asks for no periodic update.
 */
public class ContinueWidgetProvider extends AppWidgetProvider {

    @Override
    public void onUpdate(Context context, AppWidgetManager manager, int[] ids) {
        manager.updateAppWidget(ids, WidgetRenderer.cont(context));
    }
}
