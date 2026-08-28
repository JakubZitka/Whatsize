# WhatSize mobile app (Flutter)

Skeleton only — the `android/` and `ios/` platform folders are generated
locally, not committed by hand:

```bash
cd mobile
flutter create . --org com.whatsize --platforms ios,android
flutter run
```

Targets from the PRD: iOS 16+, Android 10+ (after `flutter create`, raise
`minSdkVersion` to 29 in `android/app/build.gradle` and the iOS deployment
target to 16.0 in Xcode).

CI runs via `codemagic.yaml` in the repo root: analyze + test on PRs, store
uploads (TestFlight / Play internal) from `main`.
