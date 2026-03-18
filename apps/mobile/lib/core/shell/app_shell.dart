import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../design/tokens/tokens.dart';

/// App shell that wraps the main content with a Material 3 [NavigationBar].
///
/// Uses [StatefulNavigationShell] from GoRouter to preserve each tab's
/// navigation stack independently.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  /// The shell provided by [StatefulShellRoute.indexedStack].
  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (index) {
          navigationShell.goBranch(
            index,
            initialLocation: index == navigationShell.currentIndex,
          );
        },
        backgroundColor: AppColors.neutralWhite,
        indicatorColor: AppColors.primaryNavy.withAlpha(30),
        height: 72,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(
              Icons.home,
              color: AppColors.primaryNavy,
            ),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(
              Icons.chat_bubble,
              color: AppColors.primaryNavy,
            ),
            label: 'Advisory',
          ),
          NavigationDestination(
            icon: Icon(Icons.calculate_outlined),
            selectedIcon: Icon(
              Icons.calculate,
              color: AppColors.primaryNavy,
            ),
            label: 'Tools',
          ),
          NavigationDestination(
            icon: Icon(Icons.description_outlined),
            selectedIcon: Icon(
              Icons.description,
              color: AppColors.primaryNavy,
            ),
            label: 'Docs',
          ),
          NavigationDestination(
            icon: Icon(Icons.more_horiz),
            selectedIcon: Icon(
              Icons.more_horiz,
              color: AppColors.primaryNavy,
            ),
            label: 'More',
          ),
        ],
      ),
    );
  }
}
