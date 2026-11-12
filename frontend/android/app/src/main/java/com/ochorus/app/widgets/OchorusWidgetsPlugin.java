package com.ochorus.app.widgets;

import android.content.Context;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * The web view's way to the home-screen widgets: {@code setSnapshot({ json })}
 * from $lib/platform (setWidgetSnapshot) stores what the widgets draw and
 * redraws them. The app's own plugin — no npm package — registered in
 * MainActivity.
 */
@CapacitorPlugin(name = "OchorusWidgets")
public class OchorusWidgetsPlugin extends Plugin {

    /** A snapshot is a few KB; anything near this is not one. */
    private static final int MAX_LENGTH = 64 * 1024;

    @PluginMethod
    public void setSnapshot(PluginCall call) {
        String json = call.getString("json");
        if (json == null || json.length() > MAX_LENGTH) {
            call.reject("No snapshot");
            return;
        }
        JSONObject snapshot;
        try {
            snapshot = new JSONObject(json);
        } catch (JSONException e) {
            call.reject("Not a snapshot");
            return;
        }
        if (snapshot.optInt("v") != WidgetStore.VERSION) {
            call.reject("Snapshot version " + snapshot.optInt("v") + " is not " + WidgetStore.VERSION);
            return;
        }
        Context context = getContext().getApplicationContext();
        WidgetStore.saveSnapshot(context, json);
        call.resolve();
        JSONObject book = snapshot.optJSONObject("book");
        String coverUrl = book == null || book.isNull("coverUrl") ? null : book.optString("coverUrl", null);
        // The cover may need a download, so the redraw runs off the plugin
        // thread — one snapshot at a time, so two never race for the file. An
        // unchanged cover returns at once; a new book's waits for its cover
        // rather than flash the last book's.
        WORK.execute(() -> {
            WidgetStore.syncCover(context, coverUrl);
            WidgetRenderer.updateAll(context);
        });
    }

    private static final ExecutorService WORK = Executors.newSingleThreadExecutor();
}
