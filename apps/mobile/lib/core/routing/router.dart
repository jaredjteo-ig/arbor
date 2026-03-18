import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/advisory/screens/advisory_screen.dart';
import '../../features/advisory/screens/home_screen.dart';
import '../../features/alerts/screens/alerts_screen.dart';
import '../../features/analytics/screens/analytics_screen.dart';
import '../../features/auth/screens/forgot_password_screen.dart';
import '../../features/auth/screens/login_screen.dart';
import '../../features/auth/screens/reset_password_screen.dart';
import '../../features/auth/screens/signup_screen.dart';
import '../../features/calculators/screens/calculator_detail_screen.dart';
import '../../features/calculators/screens/calculators_screen.dart';
import '../../features/clients/screens/clients_screen.dart';
import '../../features/compliance/screens/compliance_category_screen.dart';
import '../../features/compliance/screens/compliance_screen.dart';
import '../../features/documents/screens/documents_screen.dart';
import '../../features/emergency/screens/emergency_screen.dart';
import '../../features/emergency/screens/emergency_detail_screen.dart';
import '../../features/onboarding/screens/onboarding_screen.dart';
import '../../features/profile/screens/profile_screen.dart';
import '../../features/settings/screens/help_screen.dart';
import '../../features/settings/screens/more_screen.dart';
import '../../features/settings/screens/settings_screen.dart';
import '../providers/auth_providers.dart';
import '../shell/app_shell.dart';

/// Global key for the router's navigator, used for top-level navigation
/// (e.g. auth routes that sit outside the shell).
final _rootNavigatorKey = GlobalKey<NavigatorState>();

/// Riverpod provider that creates and exposes the application [GoRouter].
///
/// The router watches [isAuthenticatedProvider] and [isOnboardedProvider]
/// so that changing auth/onboarding state triggers a redirect evaluation.
final routerProvider = Provider<GoRouter>((ref) {
  // Watch auth state so the router refreshes when it changes.
  final isAuthenticated = ref.watch(isAuthenticatedProvider);
  final isOnboarded = ref.watch(isOnboardedProvider);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: '/',
    debugLogDiagnostics: true,
    redirect: (BuildContext context, GoRouterState state) {
      final location = state.matchedLocation;
      final isOnAuthPage = location.startsWith('/auth/');
      final isOnOnboarding = location == '/onboarding';

      // Not authenticated -> force login (unless already on an auth page).
      if (!isAuthenticated) {
        return isOnAuthPage ? null : '/auth/login';
      }

      // Authenticated but not onboarded -> force onboarding.
      if (!isOnboarded) {
        return isOnOnboarding ? null : '/onboarding';
      }

      // Authenticated + onboarded but still on auth/onboarding -> go home.
      if (isOnAuthPage || isOnOnboarding) {
        return '/';
      }

      // No redirect needed.
      return null;
    },
    routes: [
      // -- Auth routes (outside shell) ----------------------------------------
      GoRoute(
        path: '/auth/login',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/auth/signup',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SignupScreen(),
      ),
      GoRoute(
        path: '/auth/forgot-password',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: '/auth/reset-password',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) {
          final token = state.uri.queryParameters['token'] ?? '';
          return ResetPasswordScreen(token: token);
        },
      ),

      // -- Onboarding (outside shell) -----------------------------------------
      GoRoute(
        path: '/onboarding',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const OnboardingScreen(),
      ),

      // -- Main app shell with bottom navigation -----------------------------
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return AppShell(navigationShell: navigationShell);
        },
        branches: [
          // Tab 0: Home / Dashboard
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),

          // Tab 1: Advisory chat
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/advisory',
                builder: (context, state) => const AdvisoryScreen(),
              ),
            ],
          ),

          // Tab 2: Calculators / Tools
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/calculators',
                builder: (context, state) => const CalculatorsScreen(),
                routes: [
                  GoRoute(
                    path: ':type',
                    builder: (context, state) => CalculatorDetailScreen(
                      calculatorType: state.pathParameters['type'] ?? '',
                    ),
                  ),
                ],
              ),
            ],
          ),

          // Tab 3: Documents
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/documents',
                builder: (context, state) => const DocumentsScreen(),
              ),
            ],
          ),

          // Tab 4: More
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/more',
                builder: (context, state) => const MoreScreen(),
              ),
            ],
          ),
        ],
      ),

      // -- Routes accessible from "More" menu --------------------------------
      // These are top-level routes so they push over the shell
      // (with back navigation) rather than switching tabs.
      GoRoute(
        path: '/compliance',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const ComplianceScreen(),
        routes: [
          GoRoute(
            path: ':category',
            parentNavigatorKey: _rootNavigatorKey,
            builder: (context, state) => ComplianceCategoryScreen(
              category: state.pathParameters['category'] ?? '',
            ),
          ),
        ],
      ),
      GoRoute(
        path: '/emergency',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const EmergencyScreen(),
        routes: [
          GoRoute(
            path: ':topicId',
            parentNavigatorKey: _rootNavigatorKey,
            builder: (context, state) => EmergencyDetailScreen(
              topicId: state.pathParameters['topicId'] ?? '',
            ),
          ),
        ],
      ),
      GoRoute(
        path: '/clients',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const ClientsScreen(),
      ),
      GoRoute(
        path: '/analytics',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const AnalyticsScreen(),
      ),
      GoRoute(
        path: '/alerts',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const AlertsScreen(),
      ),
      GoRoute(
        path: '/profile',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/settings',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/help',
        parentNavigatorKey: _rootNavigatorKey,
        builder: (context, state) => const HelpScreen(),
      ),
    ],
  );
});
