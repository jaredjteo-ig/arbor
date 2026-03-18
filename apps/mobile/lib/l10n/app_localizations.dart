import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[Locale('en')];

  /// Application name
  ///
  /// In en, this message translates to:
  /// **'AITE'**
  String get appName;

  /// Application tagline
  ///
  /// In en, this message translates to:
  /// **'AI-powered HR Advisory for Singapore SMEs'**
  String get appTagline;

  /// No description provided for @navDashboard.
  ///
  /// In en, this message translates to:
  /// **'Dashboard'**
  String get navDashboard;

  /// No description provided for @navAdvisory.
  ///
  /// In en, this message translates to:
  /// **'Advisory'**
  String get navAdvisory;

  /// No description provided for @navCalculators.
  ///
  /// In en, this message translates to:
  /// **'Calculators'**
  String get navCalculators;

  /// No description provided for @navDocuments.
  ///
  /// In en, this message translates to:
  /// **'Documents'**
  String get navDocuments;

  /// No description provided for @navCompliance.
  ///
  /// In en, this message translates to:
  /// **'Compliance'**
  String get navCompliance;

  /// No description provided for @navAlerts.
  ///
  /// In en, this message translates to:
  /// **'Alerts'**
  String get navAlerts;

  /// No description provided for @navProfile.
  ///
  /// In en, this message translates to:
  /// **'Company Profile'**
  String get navProfile;

  /// No description provided for @navSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get navSettings;

  /// No description provided for @navHelp.
  ///
  /// In en, this message translates to:
  /// **'Help'**
  String get navHelp;

  /// No description provided for @navMore.
  ///
  /// In en, this message translates to:
  /// **'More'**
  String get navMore;

  /// No description provided for @authLogin.
  ///
  /// In en, this message translates to:
  /// **'Log in'**
  String get authLogin;

  /// Heading on the login form card
  ///
  /// In en, this message translates to:
  /// **'Welcome back'**
  String get authLoginTitle;

  /// No description provided for @authSignup.
  ///
  /// In en, this message translates to:
  /// **'Sign up'**
  String get authSignup;

  /// Heading and button label for registration
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get authCreateAccount;

  /// No description provided for @authEmail.
  ///
  /// In en, this message translates to:
  /// **'Email address'**
  String get authEmail;

  /// Placeholder text for email input
  ///
  /// In en, this message translates to:
  /// **'you@company.com'**
  String get authEmailHint;

  /// No description provided for @authPassword.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get authPassword;

  /// Helper text shown below password input
  ///
  /// In en, this message translates to:
  /// **'At least 8 characters'**
  String get authPasswordHint;

  /// Label for the confirm-password field
  ///
  /// In en, this message translates to:
  /// **'Confirm password'**
  String get authConfirmPassword;

  /// Label for the new-password field on reset screen
  ///
  /// In en, this message translates to:
  /// **'New password'**
  String get authNewPassword;

  /// Label for the name field on signup
  ///
  /// In en, this message translates to:
  /// **'Full name'**
  String get authName;

  /// Placeholder text for name input
  ///
  /// In en, this message translates to:
  /// **'John Doe'**
  String get authNameHint;

  /// No description provided for @authForgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get authForgotPassword;

  /// No description provided for @authResetPassword.
  ///
  /// In en, this message translates to:
  /// **'Reset password'**
  String get authResetPassword;

  /// Subtitle on the reset-password form
  ///
  /// In en, this message translates to:
  /// **'Enter your new password below.'**
  String get authResetPasswordSubtitle;

  /// No description provided for @authOrContinueWith.
  ///
  /// In en, this message translates to:
  /// **'Or continue with'**
  String get authOrContinueWith;

  /// No description provided for @authGoogle.
  ///
  /// In en, this message translates to:
  /// **'Google'**
  String get authGoogle;

  /// Google sign-in button label
  ///
  /// In en, this message translates to:
  /// **'Sign in with Google'**
  String get authSignInWithGoogle;

  /// Google sign-up button label
  ///
  /// In en, this message translates to:
  /// **'Sign up with Google'**
  String get authSignUpWithGoogle;

  /// Text before the sign-up link on login screen
  ///
  /// In en, this message translates to:
  /// **'Don\'t have an account?'**
  String get authNoAccount;

  /// Text before the login link on signup screen
  ///
  /// In en, this message translates to:
  /// **'Already have an account?'**
  String get authHaveAccount;

  /// Link text to return to the login screen
  ///
  /// In en, this message translates to:
  /// **'Back to log in'**
  String get authBackToLogin;

  /// Button label on forgot-password screen
  ///
  /// In en, this message translates to:
  /// **'Send reset link'**
  String get authSendResetLink;

  /// Heading on forgot-password form
  ///
  /// In en, this message translates to:
  /// **'Forgot password'**
  String get authForgotPasswordTitle;

  /// Subtitle on forgot-password form
  ///
  /// In en, this message translates to:
  /// **'Enter your email and we\'ll send you a link to reset your password.'**
  String get authForgotPasswordSubtitle;

  /// Heading after successful password-reset request
  ///
  /// In en, this message translates to:
  /// **'Check your email'**
  String get authForgotPasswordSuccessTitle;

  /// Message after successful password-reset request
  ///
  /// In en, this message translates to:
  /// **'If an account exists with that email, you\'ll receive a password reset link shortly.'**
  String get authForgotPasswordSuccessMessage;

  /// Error message when forgot-password request fails
  ///
  /// In en, this message translates to:
  /// **'Unable to send reset link. Please try again.'**
  String get authForgotPasswordError;

  /// Heading after successful password reset
  ///
  /// In en, this message translates to:
  /// **'Password updated'**
  String get authResetPasswordSuccessTitle;

  /// Message after successful password reset
  ///
  /// In en, this message translates to:
  /// **'Your password has been reset. You can now log in with your new password.'**
  String get authResetPasswordSuccessMessage;

  /// Error when reset-password request fails
  ///
  /// In en, this message translates to:
  /// **'Unable to reset password. Please try again.'**
  String get authResetPasswordError;

  /// Error when the reset token is expired or invalid
  ///
  /// In en, this message translates to:
  /// **'This reset link has expired. Please request a new one.'**
  String get authResetPasswordExpired;

  /// Validation error for empty email
  ///
  /// In en, this message translates to:
  /// **'Email address is required.'**
  String get authErrorEmailRequired;

  /// Validation error for malformed email
  ///
  /// In en, this message translates to:
  /// **'Please enter a valid email address.'**
  String get authErrorEmailInvalid;

  /// Validation error for empty password
  ///
  /// In en, this message translates to:
  /// **'Password is required.'**
  String get authErrorPasswordRequired;

  /// Validation error for short password
  ///
  /// In en, this message translates to:
  /// **'Password must be at least 8 characters.'**
  String get authErrorPasswordMinLength;

  /// Validation error for empty confirm-password
  ///
  /// In en, this message translates to:
  /// **'Please confirm your password.'**
  String get authErrorConfirmPasswordRequired;

  /// Validation error when passwords differ
  ///
  /// In en, this message translates to:
  /// **'Passwords do not match.'**
  String get authErrorPasswordsDoNotMatch;

  /// Validation error for empty name
  ///
  /// In en, this message translates to:
  /// **'Full name is required.'**
  String get authErrorNameRequired;

  /// No description provided for @commonSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get commonSave;

  /// No description provided for @commonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancel;

  /// No description provided for @commonClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get commonClose;

  /// No description provided for @commonBack.
  ///
  /// In en, this message translates to:
  /// **'Back'**
  String get commonBack;

  /// No description provided for @commonNext.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get commonNext;

  /// No description provided for @commonSubmit.
  ///
  /// In en, this message translates to:
  /// **'Submit'**
  String get commonSubmit;

  /// No description provided for @commonLoading.
  ///
  /// In en, this message translates to:
  /// **'Loading...'**
  String get commonLoading;

  /// No description provided for @commonError.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get commonError;

  /// No description provided for @commonRetry.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get commonRetry;

  /// No description provided for @commonSearch.
  ///
  /// In en, this message translates to:
  /// **'Search'**
  String get commonSearch;

  /// No description provided for @commonNoResults.
  ///
  /// In en, this message translates to:
  /// **'No results found'**
  String get commonNoResults;

  /// No description provided for @commonCurrency.
  ///
  /// In en, this message translates to:
  /// **'S\$'**
  String get commonCurrency;

  /// No description provided for @riskGreen.
  ///
  /// In en, this message translates to:
  /// **'Low Risk'**
  String get riskGreen;

  /// No description provided for @riskAmber.
  ///
  /// In en, this message translates to:
  /// **'Medium Risk'**
  String get riskAmber;

  /// No description provided for @riskRed.
  ///
  /// In en, this message translates to:
  /// **'High Risk'**
  String get riskRed;

  /// No description provided for @authorityStatutory.
  ///
  /// In en, this message translates to:
  /// **'Statutory'**
  String get authorityStatutory;

  /// No description provided for @authorityGuideline.
  ///
  /// In en, this message translates to:
  /// **'Tripartite Guideline'**
  String get authorityGuideline;

  /// No description provided for @authorityBestPractice.
  ///
  /// In en, this message translates to:
  /// **'Best Practice'**
  String get authorityBestPractice;

  /// No description provided for @feedbackHelpful.
  ///
  /// In en, this message translates to:
  /// **'Was this helpful?'**
  String get feedbackHelpful;

  /// No description provided for @feedbackYes.
  ///
  /// In en, this message translates to:
  /// **'Yes'**
  String get feedbackYes;

  /// No description provided for @feedbackNo.
  ///
  /// In en, this message translates to:
  /// **'No'**
  String get feedbackNo;

  /// No description provided for @feedbackWhatWasWrong.
  ///
  /// In en, this message translates to:
  /// **'What was wrong?'**
  String get feedbackWhatWasWrong;

  /// No description provided for @feedbackThankYou.
  ///
  /// In en, this message translates to:
  /// **'Thank you for your feedback'**
  String get feedbackThankYou;

  /// No description provided for @accessibilityTextSize.
  ///
  /// In en, this message translates to:
  /// **'Text Size'**
  String get accessibilityTextSize;

  /// No description provided for @accessibilityNormal.
  ///
  /// In en, this message translates to:
  /// **'Normal'**
  String get accessibilityNormal;

  /// No description provided for @accessibilityLarge.
  ///
  /// In en, this message translates to:
  /// **'Large'**
  String get accessibilityLarge;

  /// No description provided for @accessibilityExtraLarge.
  ///
  /// In en, this message translates to:
  /// **'Extra Large'**
  String get accessibilityExtraLarge;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
