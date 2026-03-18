import 'package:flutter/material.dart';

import '../design/tokens/tokens.dart';
import 'offline_manager.dart';

/// A slim banner displayed at the top of the screen when the device is
/// offline.
///
/// Slides in with an animation when [OfflineStatus.offline] is active and
/// slides out when connectivity returns. Uses the project design tokens
/// for consistent styling.
///
/// Usage:
/// ```dart
/// OfflineBanner(status: offlineManager.status)
/// ```
class OfflineBanner extends StatefulWidget {
  const OfflineBanner({
    super.key,
    required this.status,
    this.animationDuration = const Duration(milliseconds: 300),
  });

  /// The current offline status that drives visibility.
  final OfflineStatus status;

  /// Duration of the slide-in / slide-out animation.
  final Duration animationDuration;

  @override
  State<OfflineBanner> createState() => _OfflineBannerState();
}

class _OfflineBannerState extends State<OfflineBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.animationDuration,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
      reverseCurve: Curves.easeIn,
    ));

    // Set initial animation state based on current status.
    if (_shouldShow(widget.status)) {
      _controller.value = 1.0;
    }
  }

  @override
  void didUpdateWidget(OfflineBanner oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.status != widget.status) {
      if (_shouldShow(widget.status)) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  bool _shouldShow(OfflineStatus status) {
    return status == OfflineStatus.offline;
  }

  String get _message {
    return switch (widget.status) {
      OfflineStatus.offline =>
        'Offline mode \u2014 some features unavailable',
      OfflineStatus.syncing => 'Syncing pending changes\u2026',
      OfflineStatus.online => '',
    };
  }

  IconData get _icon {
    return switch (widget.status) {
      OfflineStatus.offline => Icons.wifi_off,
      OfflineStatus.syncing => Icons.sync,
      OfflineStatus.online => Icons.wifi,
    };
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: Material(
        color: AppColors.riskAmber,
        child: SafeArea(
          bottom: false,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.base,
              vertical: AppSpacing.sm,
            ),
            child: Row(
              children: [
                Icon(
                  _icon,
                  size: 18,
                  color: AppColors.neutralGray900,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    _message,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.neutralGray900,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
