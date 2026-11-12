package com.ochorus.app.widgets;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Where the widgets' data lives on the phone: the snapshot the web view last
 * sent (frontend/src/lib/widgetSnapshot.ts — localised words, the next days'
 * verses, the current book; no token, no account) in the app's private
 * SharedPreferences, and the current book's cover, downloaded once, as a small
 * PNG in the app's private files. Nothing here leaves the app's sandbox.
 */
final class WidgetStore {

    /** The snapshot shape this build draws (WIDGET_SNAPSHOT_VERSION). */
    static final int VERSION = 1;

    private static final String PREFS = "ochorus_widgets";
    private static final String KEY_SNAPSHOT = "snapshot";
    private static final String KEY_COVER_URL = "cover_url";
    /** Covers are drawn about 56dp wide: this is plenty at any density. */
    private static final int COVER_MAX_WIDTH = 240;
    private static final int COVER_MAX_BYTES = 4 * 1024 * 1024;

    private WidgetStore() {}

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static void saveSnapshot(Context context, String json) {
        prefs(context).edit().putString(KEY_SNAPSHOT, json).apply();
    }

    /** The stored snapshot, or null when there is none (or of another version). */
    static JSONObject snapshot(Context context) {
        String json = prefs(context).getString(KEY_SNAPSHOT, null);
        if (json == null) return null;
        try {
            JSONObject snapshot = new JSONObject(json);
            return snapshot.optInt("v") == VERSION ? snapshot : null;
        } catch (JSONException e) {
            return null;
        }
    }

    private static File coverFile(Context context) {
        return new File(new File(context.getFilesDir(), "widgets"), "cover.png");
    }

    /** The current book's cover, or null when there is none (yet). */
    static Bitmap cover(Context context) {
        File file = coverFile(context);
        return file.exists() ? BitmapFactory.decodeFile(file.getPath()) : null;
    }

    /**
     * Make the stored cover the one at {@code url} (null: none). Downloads only
     * when the URL changed. Blocking network: never on the main thread.
     */
    static void syncCover(Context context, String url) {
        String have = prefs(context).getString(KEY_COVER_URL, null);
        File file = coverFile(context);
        if (url == null || !url.startsWith("https://")) {
            //noinspection ResultOfMethodCallIgnored
            file.delete();
            prefs(context).edit().remove(KEY_COVER_URL).apply();
            return;
        }
        if (url.equals(have) && file.exists()) return;
        // The old cover goes first: better no cover than another book's.
        //noinspection ResultOfMethodCallIgnored
        file.delete();
        prefs(context).edit().remove(KEY_COVER_URL).apply();
        Bitmap bitmap = download(url);
        if (bitmap == null) return;
        File dir = file.getParentFile();
        if (dir != null && !dir.isDirectory() && !dir.mkdirs()) return;
        File tmp = new File(dir, "cover.tmp");
        try (FileOutputStream out = new FileOutputStream(tmp)) {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
        } catch (IOException e) {
            //noinspection ResultOfMethodCallIgnored
            tmp.delete();
            return;
        }
        if (tmp.renameTo(file)) prefs(context).edit().putString(KEY_COVER_URL, url).apply();
    }

    private static Bitmap download(String url) {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setConnectTimeout(10_000);
            connection.setReadTimeout(15_000);
            if (connection.getResponseCode() != HttpURLConnection.HTTP_OK) return null;
            byte[] bytes = readCapped(connection.getInputStream());
            if (bytes == null) return null;
            BitmapFactory.Options bounds = new BitmapFactory.Options();
            bounds.inJustDecodeBounds = true;
            BitmapFactory.decodeByteArray(bytes, 0, bytes.length, bounds);
            if (bounds.outWidth <= 0) return null;
            BitmapFactory.Options options = new BitmapFactory.Options();
            int sample = 1;
            while (bounds.outWidth / (sample * 2) >= COVER_MAX_WIDTH) sample *= 2;
            options.inSampleSize = sample;
            Bitmap bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.length, options);
            if (bitmap == null || bitmap.getWidth() <= COVER_MAX_WIDTH) return bitmap;
            int height = Math.round(bitmap.getHeight() * (COVER_MAX_WIDTH / (float) bitmap.getWidth()));
            return Bitmap.createScaledBitmap(bitmap, COVER_MAX_WIDTH, Math.max(1, height), true);
        } catch (IOException | RuntimeException e) {
            return null;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static byte[] readCapped(InputStream in) throws IOException {
        try (InputStream input = in; ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16 * 1024];
            int total = 0;
            int n;
            while ((n = input.read(buffer)) != -1) {
                total += n;
                if (total > COVER_MAX_BYTES) return null;
                out.write(buffer, 0, n);
            }
            return out.toByteArray();
        }
    }
}
