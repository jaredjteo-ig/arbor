import 'dart:developer' as developer;

import 'package:flutter/widgets.dart';

/// Observes application lifecycle transitions (foreground, background, etc.)
/// and logs them for diagnostics.
///
/// Extend this class to add token refresh, socket reconnection, or analytics
/// hooks when the app resumes from the background.
class AppLifecycleObserver with WidgetsBindingObserver {
  /// Registers this observer with [WidgetsBinding].
  void register() {
    WidgetsBinding.instance.addObserver(this);
    developer.log('AppLifecycleObserver registered', name: 'lifecycle');
  }

  /// Unregisters this observer from [WidgetsBinding].
  void unregister() {
    WidgetsBinding.instance.removeObserver(this);
    developer.log('AppLifecycleObserver unregistered', name: 'lifecycle');
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    developer.log(
      'App lifecycle state changed to: ${state.name}',
      name: 'lifecycle',
    );

    switch (state) {
      case AppLifecycleState.resumed:
        _onResumed();
      case AppLifecycleState.inactive:
        _onInactive();
      case AppLifecycleState.paused:
        _onPaused();
      case AppLifecycleState.detached:
        _onDetached();
      case AppLifecycleState.hidden:
        _onHidden();
    }
  }

  /// Called when the app returns to the foreground.
  ///
  /// Override to refresh auth tokens, reconnect sockets, etc.
  void _onResumed() {
    // TODO: token refresh, socket reconnection
  }

  /// Called when the app is partially obscured (e.g. incoming call overlay).
  void _onInactive() {
    // No-op for now.
  }

  /// Called when the app moves to the background.
  void _onPaused() {
    // No-op for now.
  }

  /// Called when the app is about to be terminated.
  void _onDetached() {
    // No-op for now.
  }

  /// Called when the app is hidden (e.g. another app covers it entirely).
  void _onHidden() {
    // No-op for now.
  }
}
