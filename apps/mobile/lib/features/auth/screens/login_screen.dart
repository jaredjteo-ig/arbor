import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/providers/auth_providers.dart';
import '../../../l10n/app_localizations.dart';

/// Login screen displayed when the user is not authenticated.
///
/// Features email/password login, Google sign-in placeholder, forgot-password
/// link, and sign-up navigation.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _emailFocusNode = FocusNode();
  final _passwordFocusNode = FocusNode();

  bool _obscurePassword = true;
  String? _emailError;
  String? _passwordError;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _emailFocusNode.dispose();
    _passwordFocusNode.dispose();
    super.dispose();
  }

  bool _validateForm() {
    final email = _emailController.text.trim();
    final password = _passwordController.text;

    String? emailErr;
    String? passwordErr;

    if (email.isEmpty) {
      emailErr = _l10n.authErrorEmailRequired;
    } else if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      emailErr = _l10n.authErrorEmailInvalid;
    }

    if (password.isEmpty) {
      passwordErr = _l10n.authErrorPasswordRequired;
    } else if (password.length < 8) {
      passwordErr = _l10n.authErrorPasswordMinLength;
    }

    setState(() {
      _emailError = emailErr;
      _passwordError = passwordErr;
    });

    return emailErr == null && passwordErr == null;
  }

  Future<void> _handleLogin() async {
    if (!_validateForm()) return;

    await ref.read(authStateProvider.notifier).login(
          _emailController.text.trim(),
          _passwordController.text,
        );
  }

  AppLocalizations get _l10n => AppLocalizations.of(context)!;

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);
    final isLoading = authState is AuthLoading;

    // Listen for auth errors and show them inline (not via snackbar, since
    // the error string is displayed directly in the form).
    final errorMessage = authState is AuthError ? authState.message : null;

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
                  size: 64,
                  color: AppColors.neutralWhite,
                ),
                const SizedBox(height: AppSpacing.base),
                Text(
                  _l10n.appName,
                  style: AppTypography.pageTitle.copyWith(
                    color: AppColors.neutralWhite,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  _l10n.appTagline,
                  style: AppTypography.body.copyWith(
                    color: AppColors.neutralWhite.withAlpha(200),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.s2xl),

                // ── Form Card ───────────────────────
                AppCard(
                  padding: const EdgeInsets.all(AppSpacing.xl),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          _l10n.authLoginTitle,
                          style: AppTypography.heading.copyWith(
                            color: AppColors.primaryNavy,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: AppSpacing.xl),

                        // Error banner
                        if (errorMessage != null) ...[
                          AlertBanner(
                            title: errorMessage,
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
                          enabled: !isLoading,
                          textInputAction: TextInputAction.next,
                          prefixIcon: const Icon(Icons.email_outlined),
                          autofillHints: const [AutofillHints.email],
                          onSubmitted: (_) =>
                              _passwordFocusNode.requestFocus(),
                        ),
                        const SizedBox(height: AppSpacing.base),

                        // Password
                        AppInput(
                          label: _l10n.authPassword,
                          controller: _passwordController,
                          focusNode: _passwordFocusNode,
                          obscureText: _obscurePassword,
                          errorText: _passwordError,
                          enabled: !isLoading,
                          textInputAction: TextInputAction.done,
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
                          autofillHints: const [AutofillHints.password],
                          onSubmitted: (_) => _handleLogin(),
                        ),

                        // Forgot password
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: isLoading
                                ? null
                                : () => context.go('/auth/forgot-password'),
                            child: Text(
                              _l10n.authForgotPassword,
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.primaryNavy,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.base),

                        // Sign in button
                        AppButton(
                          label: _l10n.authLogin,
                          onPressed: isLoading ? null : _handleLogin,
                          isLoading: isLoading,
                          fullWidth: true,
                        ),
                        const SizedBox(height: AppSpacing.base),

                        // Divider
                        Row(
                          children: [
                            const Expanded(
                              child: Divider(color: AppColors.neutralGray300),
                            ),
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: AppSpacing.base,
                              ),
                              child: Text(
                                _l10n.authOrContinueWith,
                                style: AppTypography.caption.copyWith(
                                  color: AppColors.neutralGray500,
                                ),
                              ),
                            ),
                            const Expanded(
                              child: Divider(color: AppColors.neutralGray300),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.base),

                        // Google sign-in placeholder
                        AppButton(
                          label: _l10n.authSignInWithGoogle,
                          variant: AppButtonVariant.outlined,
                          icon: Icons.g_mobiledata,
                          onPressed: isLoading ? null : () {},
                          fullWidth: true,
                        ),
                        const SizedBox(height: AppSpacing.xl),

                        // Sign up link
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _l10n.authNoAccount,
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.neutralGray600,
                              ),
                            ),
                            TextButton(
                              onPressed: isLoading
                                  ? null
                                  : () => context.go('/auth/signup'),
                              child: Text(
                                _l10n.authSignup,
                                style: AppTypography.bodySmall.copyWith(
                                  color: AppColors.primaryNavy,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
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
