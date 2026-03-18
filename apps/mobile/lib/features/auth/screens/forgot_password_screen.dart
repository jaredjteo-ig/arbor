import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/providers/auth_providers.dart';
import '../../../l10n/app_localizations.dart';

/// Screen for requesting a password-reset email.
///
/// After submitting, shows a success confirmation so the user knows to
/// check their inbox.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _emailController = TextEditingController();
  final _emailFocusNode = FocusNode();

  bool _isLoading = false;
  bool _isSuccess = false;
  String? _emailError;
  String? _errorMessage;

  @override
  void dispose() {
    _emailController.dispose();
    _emailFocusNode.dispose();
    super.dispose();
  }

  bool _validateEmail() {
    final email = _emailController.text.trim();
    String? err;

    if (email.isEmpty) {
      err = _l10n.authErrorEmailRequired;
    } else if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      err = _l10n.authErrorEmailInvalid;
    }

    setState(() {
      _emailError = err;
    });

    return err == null;
  }

  Future<void> _handleSubmit() async {
    if (!_validateEmail()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authService = ref.read(authServiceProvider);
      await authService.requestPasswordReset(_emailController.text.trim());

      if (mounted) {
        setState(() {
          _isSuccess = true;
          _isLoading = false;
        });
      }
    } on DioException catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          // Show success even on 404 to prevent email enumeration
          if (e.response?.statusCode == 404) {
            _isSuccess = true;
          } else {
            _errorMessage = _l10n.authForgotPasswordError;
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = _l10n.authForgotPasswordError;
        });
      }
    }
  }

  AppLocalizations get _l10n => AppLocalizations.of(context)!;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primaryNavy,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // ── Branding ────────────────────────
                const Icon(
                  Icons.shield_outlined,
                  size: 48,
                  color: AppColors.neutralWhite,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  _l10n.appName,
                  style: AppTypography.title.copyWith(
                    color: AppColors.neutralWhite,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.xl),

                // ── Form Card ───────────────────────
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: _isSuccess ? _buildSuccess() : _buildForm(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _l10n.authForgotPasswordTitle,
          style: AppTypography.heading.copyWith(
            color: AppColors.primaryNavy,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          _l10n.authForgotPasswordSubtitle,
          style: AppTypography.body.copyWith(
            color: AppColors.neutralGray600,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.xl),

        // Error banner
        if (_errorMessage != null) ...[
          AlertBanner(
            title: _errorMessage!,
            variant: AlertBannerVariant.error,
          ),
          const SizedBox(height: AppSpacing.base),
        ],

        // Email
        AppInput(
          label: _l10n.authEmail,
          hintText: _l10n.authEmailHint,
          controller: _emailController,
          focusNode: _emailFocusNode,
          errorText: _emailError,
          enabled: !_isLoading,
          textInputAction: TextInputAction.done,
          prefixIcon: const Icon(Icons.email_outlined),
          autofillHints: const [AutofillHints.email],
          onSubmitted: (_) => _handleSubmit(),
        ),
        const SizedBox(height: AppSpacing.xl),

        // Submit button
        AppButton(
          label: _l10n.authSendResetLink,
          onPressed: _isLoading ? null : _handleSubmit,
          isLoading: _isLoading,
          fullWidth: true,
        ),
        const SizedBox(height: AppSpacing.base),

        // Back to login
        AppButton(
          label: _l10n.authBackToLogin,
          variant: AppButtonVariant.text,
          onPressed: _isLoading ? null : () => context.go('/auth/login'),
          fullWidth: true,
        ),
      ],
    );
  }

  Widget _buildSuccess() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(
          Icons.mark_email_read_outlined,
          size: 64,
          color: AppColors.secondaryTeal,
        ),
        const SizedBox(height: AppSpacing.base),
        Text(
          _l10n.authForgotPasswordSuccessTitle,
          style: AppTypography.heading.copyWith(
            color: AppColors.primaryNavy,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          _l10n.authForgotPasswordSuccessMessage,
          style: AppTypography.body.copyWith(
            color: AppColors.neutralGray600,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: _l10n.authBackToLogin,
          onPressed: () => context.go('/auth/login'),
          fullWidth: true,
        ),
      ],
    );
  }
}
