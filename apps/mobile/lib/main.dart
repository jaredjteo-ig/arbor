import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/design/tokens/app_theme.dart';
import 'core/lifecycle/app_lifecycle_observer.dart';
import 'core/routing/router.dart';
import 'l10n/app_localizations.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  final lifecycleObserver = AppLifecycleObserver()..register();

  runApp(
    ProviderScope(
      child: ArborApp(lifecycleObserver: lifecycleObserver),
    ),
  );
}

/// Root widget for the Arbor mobile application.
///
/// Uses [MaterialApp.router] with GoRouter for declarative navigation,
/// Riverpod for state management, and the Arbor design system theme.
class ArborApp extends ConsumerStatefulWidget {
  const ArborApp({super.key, required this.lifecycleObserver});

  final AppLifecycleObserver lifecycleObserver;

  @override
  ConsumerState<ArborApp> createState() => _ArborAppState();
}

class _ArborAppState extends ConsumerState<ArborApp> {
  @override
  void dispose() {
    widget.lifecycleObserver.unregister();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'Central',
      theme: buildAppTheme(),
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
    );
  }
}
