# Android Build and Release

## What ships today: an installable PWA

The web app is a mobile-first Progressive Web App:

- `manifest.webmanifest` with 192/512 px standard and maskable icons,
  standalone display, and theme colors.
- A service worker (`sw.js`) caching the app shell and immutable assets;
  `/api/*` is never cached (session data stays live and private).
- Verified layouts from 320 px up, a bottom tab bar, 44 px touch targets,
  and safe-area padding.

On Android (Chrome): open the app → menu → **Add to Home screen /
Install app**. It launches standalone with the Agentic OS icon and splash
colors.

## Native Android (Capacitor) — documented path, not shipped

A real `apps/android` Capacitor project requires the Android SDK and
Gradle to build and an emulator/device to test. Neither exists in the
implementation environment, and committing an unbuilt, untested native
project would violate the no-placeholder rule. The exact path:

```bash
cd frontend
npm i @capacitor/core @capacitor/cli @capacitor/android
npx cap init "Agentic OS" com.agenticos.app --web-dir=dist
npm run build && npx cap add android && npx cap sync android
cd android && ./gradlew lintDebug testDebugUnitTest assembleDebug
# artifact: android/app/build/outputs/apk/debug/app-debug.apk
```

Release requirements (per Android core app quality + V2 §18): HTTPS-only
API origin, tokens in platform secure storage (not WebView localStorage),
deep-link allowlist, minimal permissions requested at point of use, back/
keyboard/safe-area handling (the PWA layout already handles safe areas),
adaptive icons (the maskable icons ship already), and CI jobs for lint,
unit tests, and `assembleDebug` with the APK as an artifact. Never commit
keystores or signing credentials.

Do not claim device validation until it has actually run on hardware.
