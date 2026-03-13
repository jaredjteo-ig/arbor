import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:hr_advisory_mobile/core/lifecycle/app_lifecycle_observer.dart';
import 'package:hr_advisory_mobile/main.dart';

void main() {
  testWidgets('App shell renders with bottom navigation',
      (WidgetTester tester) async {
    final observer = AppLifecycleObserver()..register();

    await tester.pumpWidget(
      ProviderScope(
        child: AiteApp(lifecycleObserver: observer),
      ),
    );
    await tester.pumpAndSettle();

    // The bottom navigation bar should show all five tab labels.
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Advisory'), findsOneWidget);
    expect(find.text('Tools'), findsOneWidget);
    expect(find.text('Docs'), findsOneWidget);
    expect(find.text('More'), findsOneWidget);

    // The default route is '/' which shows the Dashboard home screen.
    expect(find.text('Dashboard'), findsOneWidget);

    observer.unregister();
  });
}
