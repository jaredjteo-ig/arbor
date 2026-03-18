import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// The kind of content an [AppInput] collects.
enum AppInputType { text, number, dropdown, textarea }

/// A design-system text input that supports text, number, dropdown, and
/// multi-line textarea variants.
///
/// For [AppInputType.dropdown], supply [dropdownItems] and use [onDropdownChanged]
/// to handle selection.
class AppInput extends StatelessWidget {
  const AppInput({
    super.key,
    this.type = AppInputType.text,
    this.label,
    this.hintText,
    this.helperText,
    this.errorText,
    this.controller,
    this.onChanged,
    this.onSubmitted,
    this.obscureText = false,
    this.enabled = true,
    this.maxLines = 1,
    this.prefixIcon,
    this.suffixIcon,
    this.dropdownItems,
    this.dropdownValue,
    this.onDropdownChanged,
    this.textInputAction,
    this.focusNode,
    this.autofillHints,
  });

  final AppInputType type;
  final String? label;
  final String? hintText;
  final String? helperText;
  final String? errorText;
  final TextEditingController? controller;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final bool obscureText;
  final bool enabled;
  final int maxLines;
  final Widget? prefixIcon;
  final Widget? suffixIcon;

  /// Items for [AppInputType.dropdown].
  final List<DropdownMenuItem<String>>? dropdownItems;
  final String? dropdownValue;
  final ValueChanged<String?>? onDropdownChanged;

  final TextInputAction? textInputAction;
  final FocusNode? focusNode;
  final Iterable<String>? autofillHints;

  TextInputType get _keyboardType {
    return switch (type) {
      AppInputType.number => TextInputType.number,
      AppInputType.textarea => TextInputType.multiline,
      _ => TextInputType.text,
    };
  }

  @override
  Widget build(BuildContext context) {
    if (type == AppInputType.dropdown) {
      return _buildDropdown(context);
    }

    final effectiveMaxLines = type == AppInputType.textarea ? (maxLines > 1 ? maxLines : 4) : 1;

    return TextFormField(
      controller: controller,
      focusNode: focusNode,
      onChanged: onChanged,
      onFieldSubmitted: onSubmitted,
      obscureText: obscureText,
      enabled: enabled,
      maxLines: effectiveMaxLines,
      keyboardType: _keyboardType,
      textInputAction: type == AppInputType.textarea ? TextInputAction.newline : textInputAction,
      autofillHints: autofillHints,
      style: AppTypography.body.copyWith(color: AppColors.neutralGray900),
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        helperText: helperText,
        errorText: errorText,
        prefixIcon: prefixIcon,
        suffixIcon: suffixIcon,
        labelStyle: AppTypography.bodySmall.copyWith(color: AppColors.neutralGray600),
        hintStyle: AppTypography.body.copyWith(color: AppColors.neutralGray400),
        helperStyle: AppTypography.caption.copyWith(color: AppColors.neutralGray500),
        errorStyle: AppTypography.caption.copyWith(color: AppColors.riskRed),
        errorBorder: OutlineInputBorder(
          borderRadius: AppRadius.md,
          borderSide: const BorderSide(color: AppColors.riskRed, width: 1.5),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: AppRadius.md,
          borderSide: const BorderSide(color: AppColors.riskRed, width: 2),
        ),
      ),
    );
  }

  Widget _buildDropdown(BuildContext context) {
    return DropdownButtonFormField<String>(
      initialValue: dropdownValue,
      items: dropdownItems,
      onChanged: enabled ? onDropdownChanged : null,
      style: AppTypography.body.copyWith(color: AppColors.neutralGray900),
      decoration: InputDecoration(
        labelText: label,
        hintText: hintText,
        helperText: helperText,
        errorText: errorText,
        prefixIcon: prefixIcon,
        labelStyle: AppTypography.bodySmall.copyWith(color: AppColors.neutralGray600),
        hintStyle: AppTypography.body.copyWith(color: AppColors.neutralGray400),
        helperStyle: AppTypography.caption.copyWith(color: AppColors.neutralGray500),
        errorStyle: AppTypography.caption.copyWith(color: AppColors.riskRed),
        errorBorder: OutlineInputBorder(
          borderRadius: AppRadius.md,
          borderSide: const BorderSide(color: AppColors.riskRed, width: 1.5),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: AppRadius.md,
          borderSide: const BorderSide(color: AppColors.riskRed, width: 2),
        ),
      ),
    );
  }
}
