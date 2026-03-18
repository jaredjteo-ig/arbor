import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/providers/auth_providers.dart';
import '../../../l10n/app_localizations.dart';

/// Screen for resetting a password using a one-time token from the email.
///
/// The token is passed as a route query parameter (`?token=...`).
class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key, required this.token});

  /// The one-time password-reset token from the URL.
  final String token;

  @override
  ConsumerState<ResetPasswordScreen> createState() =>
      _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _passwordFocusNode = FocusNode();
  final _confirmPasswordFocusNode = FocusNode();

  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  bool _isLoading = false;
  bool _isSuccess = false;

  String? _passwordError;
  String? _confirmPasswordError;
  String? _errorMessage;

  @override
  void dispose() {
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _passwordFocusNode.dispose();
    _confirmPasswordFocusNode.dispose();
    super.dispose();
  }

  bool _validateForm() {
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    String? passwordErr;
    String? confirmErr;

    if (password.isEmpty) {
      passwordErr = _l10n.authErrorPasswordRequired;
    } else if (password.length < 8) {
      passwordErr = _l10n.authErrorPasswordMinLength;
    }

    if (confirmPassword.isEmpty) {
      confirmErr = _l10n.authErrorConfirmPasswordRequired;
    } else if (confirmPassword != password) {
      confirmErr = _l10n.authErrorPasswordsDoNotMatch;
    }

    setState(() {
      _passwordError = passwordErr;
      _confirmPasswordError = confirmErr;
    });

    return passwordErr == null && confirmErr == null;
  }

  Future<void> _handleReset() async {
    if (!_validateForm()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final authService = ref.read(authServiceProvider);
      await authService.resetPassword(
        token: widget.token,
        newPassword: _passwordController.text,
      );

      if (mounted) {
        setState(() {
          _isSuccess = true;
          _isLoading = false;
        });
      }
    } on DioException catch (e) {
      if (mounted) {
        String message;
        if (e.response?.statusCode == 400 || e.response?.statusCode == 404) {
          message = _l10n.authResetPasswordExpired;
        } else {
          message = _l10n.authResetPasswordError;
        }
        setState(() {
          _isLoading = false;
          _errorMessage = message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = _l10n.authResetPasswordError;
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
          _l10n.authResetPassword,
          style: AppTypography.heading.copyWith(
            color: AppColors.primaryNavy,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          _l10n.authResetPasswordSubtitle,
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

        // New password
        AppInput(
          label: _l10n.authNewPassword,
          controller: _passwordController,
          focusNode: _passwordFocusNode,
          obscureText: _obscurePassword,
          errorText: _passwordError,
          helperText: _l10n.authPasswordHint,
          enabled: !_isLoading,
          textInputAction: TextInputAction.next,
          prefixIcon: const Icon(Icons.lock_outlined),
          suffixIcon: IconButton(
            icon: Icon(
              _obscurePassword
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
            ),
            onPressed: () {
              setState(() {
                _obscurePassword = !_obscurePassword;
              });
            },
          ),
          autofillHints: const [AutofillHints.newPassword],
          onSubmitted: (_) => _confirmPasswordFocusNode.requestFocus(),
        ),
        const SizedBox(height: AppSpacing.base),

        // Confirm password
        AppInput(
          label: _l10n.authConfirmPassword,
          controller: _confirmPasswordController,
          focusNode: _confirmPasswordFocusNode,
          obscureText: _obscureConfirm,
          errorText: _confirmPasswordError,
          enabled: !_isLoading,
          textInputAction: TextInputAction.done,
          prefixIcon: const Icon(Icons.lock_outlined),
          suffixIcon: IconButton(
            icon: Icon(
              _obscureConfirm
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
            ),
            onPressed: () {
              setState(() {
                _obscureConfirm = !_obscureConfirm;
              });
            },
          ),
          autofillHints: const [AutofillHints.newPassword],
          onSubmitted: (_) => _handleReset(),
        ),
        const SizedBox(height: AppSpacing.xl),

        // Reset button
        AppButton(
          label: _l10n.authResetPassword,
          onPressed: _isLoading ? null : _handleReset,
          isLoading: _isLoading,
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
          Icons.check_circle_outline,
          size: 64,
          color: AppColors.secondaryTeal,
        ),
        const SizedBox(height: AppSpacing.base),
        Text(
          _l10n.authResetPasswordSuccessTitle,
          style: AppTypography.heading.copyWith(
            color: AppColors.primaryNavy,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          _l10n.authResetPasswordSuccessMessage,
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
