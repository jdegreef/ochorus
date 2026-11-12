package com.ochorus.app;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.ochorus.app.widgets.OchorusWidgetsPlugin;

public class MainActivity extends BridgeActivity {

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // The app's own plugins (no npm package, so `cap sync` cannot list
        // them): registered before the bridge starts.
        registerPlugin(OchorusWidgetsPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
