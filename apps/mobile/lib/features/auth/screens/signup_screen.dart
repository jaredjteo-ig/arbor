import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/providers/auth_providers.dart';
import '../../../l10n/app_localizations.dart';

/// Sign-up screen for new users.
///
/// Collects name, email, password, and password confirmation, then
/// registers the user via [AuthNotifier.register].
class SignupScreen extends ConsumerStatefulWidget {
  const SignupScreen({super.key});

  @override
  ConsumerState<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends ConsumerState<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  final _nameFocusNode = FocusNode();
  final _emailFocusNode = FocusNode();
  final _passwordFocusNode = FocusNode();
  final _confirmPasswordFocusNode = FocusNode();

  bool _obscurePassword = true;
  bool _obscureConfirm = true;

  String? _nameError;
  String? _emailError;
  String? _passwordError;
  String? _confirmPasswordError;

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _nameFocusNode.dispose();
    _emailFocusNode.dispose();
    _passwordFocusNode.dispose();
    _confirmPasswordFocusNode.dispose();
    super.dispose();
  }

  bool _validateForm() {
    final name = _nameController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final confirmPassword = _confirmPasswordController.text;

    String? nameErr;
    String? emailErr;
    String? passwordErr;
    String? confirmErr;

    if (name.isEmpty) {
      nameErr = _l10n.authErrorNameRequired;
    }

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

    if (confirmPassword.isEmpty) {
      confirmErr = _l10n.authErrorConfirmPasswordRequired;
    } else if (confirmPassword != password) {
      confirmErr = _l10n.authErrorPasswordsDoNotMatch;
    }

    setState(() {
      _nameError = nameErr;
      _emailError = emailErr;
      _passwordError = passwordErr;
      _confirmPasswordError = confirmErr;
    });

    return nameErr == null &&
        emailErr == null &&
        passwordErr == null &&
        confirmErr == null;
  }

  Future<void> _handleSignup() async {
    if (!_validateForm()) return;

    await ref.read(authStateProvider.notifier).register(
          _emailController.text.trim(),
          _passwordController.text,
          _nameController.text.trim(),
        );
  }

  AppLocalizations get _l10n => AppLocalizations.of(context)!;

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authStateProvider);
    final isLoading = authState is AuthLoading;
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
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          _l10n.authCreateAccount,
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

                        // Name
                        AppInput(
                          label: _l10n.authName,
                          hintText: _l10n.authNameHint,
                          controller: _nameController,
                          focusNode: _nameFocusNode,
                          errorText: _nameError,
                          enabled: !isLoading,
                          textInputAction: TextInputAction.next,
                          prefixIcon: const Icon(Icons.person_outlined),
                          autofillHints: const [AutofillHints.name],
                          onSubmitted: (_) =>
                              _emailFocusNode.requestFocus(),
                        ),
                        const SizedBox(height: AppSpacing.base),

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
                          helperText: _l10n.authPasswordHint,
                          enabled: !isLoading,
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
                          onSubmitted: (_) =>
                              _confirmPasswordFocusNode.requestFocus(),
                        ),
                        const SizedBox(height: AppSpacing.base),

                        // Confirm password
                        AppInput(
                          label: _l10n.authConfirmPassword,
                          controller: _confirmPasswordController,
                          focusNode: _confirmPasswordFocusNode,
                          obscureText: _obscureConfirm,
                          errorText: _confirmPasswordError,
                          enabled: !isLoading,
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
                          onSubmitted: (_) => _handleSignup(),
                        ),
                        const SizedBox(height: AppSpacing.xl),

                        // Create account button
                        AppButton(
                          label: _l10n.authCreateAccount,
                          onPressed: isLoading ? null : _handleSignup,
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

                        // Google sign-up placeholder
                        AppButton(
                          label: _l10n.authSignUpWithGoogle,
                          variant: AppButtonVariant.outlined,
                          icon: Icons.g_mobiledata,
                          onPressed: isLoading ? null : () {},
                          fullWidth: true,
                        ),
                        const SizedBox(height: AppSpacing.xl),

                        // Login link
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _l10n.authHaveAccount,
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.neutralGray600,
                              ),
                            ),
                            TextButton(
                              onPressed: isLoading
                                  ? null
                                  : () => context.go('/auth/login'),
                              child: Text(
                                _l10n.authLogin,
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
