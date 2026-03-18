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
      child: AiteApp(lifecycleObserver: lifecycleObserver),
    ),
  );
}

/// Root widget for the AITE mobile application.
///
/// Uses [MaterialApp.router] with GoRouter for declarative navigation,
/// Riverpod for state management, and the AITE design system theme.
class AiteApp extends ConsumerStatefulWidget {
  const AiteApp({super.key, required this.lifecycleObserver});

  final AppLifecycleObserver lifecycleObserver;

  @override
  ConsumerState<AiteApp> createState() => _AiteAppState();
}

class _AiteAppState extends ConsumerState<AiteApp> {
  @override
  void dispose() {
    widget.lifecycleObserver.unregister();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'AITE',
      theme: buildAppTheme(),
      debugShowCheckedModeBanner: false,
      routerConfig: router,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
    );
  }
}
