import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/advisory.dart';
import '../models/company.dart';
import '../models/compliance.dart';
import '../models/document.dart';
import '../models/knowledge_base.dart';
import '../network/api_client.dart';
import '../network/sse_client.dart';
import '../repositories/advisory_repository.dart';
import '../repositories/calculator_repository.dart';
import '../repositories/compliance_repository.dart';
import '../repositories/document_repository.dart';
import '../repositories/kb_repository.dart';
import '../repositories/profile_repository.dart';
import '../repositories/search_repository.dart';
import 'auth_providers.dart';

// ── Core Infrastructure ────────────────────────────────────────────────────

/// Provides the configured [ApiClient] with auth interceptor, logging,
/// and error handling.
final apiClientProvider = Provider<ApiClient>((ref) {
  final authService = ref.watch(authServiceProvider);
  return ApiClient(authService: authService);
});

/// Provides the [SSEClient] for streaming responses (advisory).
final sseClientProvider = Provider<SSEClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return SSEClient(dio: apiClient.dio);
});

// ── Repository Providers ───────────────────────────────────────────────────

/// Provides the [AdvisoryRepository] for advisory queries and history.
final advisoryRepositoryProvider = Provider<AdvisoryRepository>((ref) {
  return AdvisoryRepository(
    client: ref.watch(apiClientProvider),
    sseClient: ref.watch(sseClientProvider),
  );
});

/// Provides the [CalculatorRepository] for CPF, leave, and salary
/// calculations.
final calculatorRepositoryProvider =
    Provider<CalculatorRepository>((ref) {
  return CalculatorRepository(client: ref.watch(apiClientProvider));
});

/// Provides the [ComplianceRepository] for compliance checks and gap
/// analysis.
final complianceRepositoryProvider =
    Provider<ComplianceRepository>((ref) {
  return ComplianceRepository(client: ref.watch(apiClientProvider));
});

/// Provides the [DocumentRepository] for template listing and document
/// generation.
final documentRepositoryProvider =
    Provider<DocumentRepository>((ref) {
  return DocumentRepository(client: ref.watch(apiClientProvider));
});

/// Provides the [ProfileRepository] for company profile operations.
final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepository(client: ref.watch(apiClientProvider));
});

/// Provides the [KbRepository] for knowledge base queries.
final kbRepositoryProvider = Provider<KbRepository>((ref) {
  return KbRepository(client: ref.watch(apiClientProvider));
});

/// Provides the [SearchRepository] for semantic and full-text search.
final searchRepositoryProvider = Provider<SearchRepository>((ref) {
  return SearchRepository(client: ref.watch(apiClientProvider));
});

// ── Family Data Providers (Riverpod 3 pattern) ─────────────────────────────
//
// For parameterized data (e.g. "fetch profile for company #42"), Riverpod 3
// uses AsyncNotifierProvider.family. The notifier receives the arg via its
// constructor and stores it for use in build() and action methods.

/// Fetches and caches a company profile by ID.
///
/// Usage:
/// ```dart
/// final profile = ref.watch(companyProfileProvider(42));
/// profile.when(
///   data: (p) => Text(p.name),
///   loading: () => CircularProgressIndicator(),
///   error: (e, s) => Text('Error: $e'),
/// );
/// ```
class CompanyProfileNotifier extends AsyncNotifier<CompanyProfile> {
  CompanyProfileNotifier(this._companyId);

  final int _companyId;

  @override
  Future<CompanyProfile> build() {
    return ref.read(profileRepositoryProvider).getProfile(_companyId);
  }

  /// Updates the company profile and refreshes the cached data.
  Future<void> updateProfile(Map<String, dynamic> data) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(profileRepositoryProvider)
          .updateProfile(_companyId, data),
    );
  }

  /// Forces a refresh of the company profile from the server.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () =>
          ref.read(profileRepositoryProvider).getProfile(_companyId),
    );
  }
}

/// Provider for [CompanyProfileNotifier], parameterized by company ID.
final companyProfileProvider = AsyncNotifierProvider.family<
    CompanyProfileNotifier, CompanyProfile, int>(
  (companyId) => CompanyProfileNotifier(companyId),
);

/// Fetches and caches the workforce composition for a company.
class WorkforceNotifier extends AsyncNotifier<WorkforceComposition> {
  WorkforceNotifier(this._companyId);

  final int _companyId;

  @override
  Future<WorkforceComposition> build() {
    return ref
        .read(profileRepositoryProvider)
        .getWorkforce(_companyId);
  }

  /// Forces a refresh of the workforce data.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(profileRepositoryProvider)
          .getWorkforce(_companyId),
    );
  }
}

/// Provider for [WorkforceNotifier], parameterized by company ID.
final workforceProvider = AsyncNotifierProvider.family<
    WorkforceNotifier, WorkforceComposition, int>(
  (companyId) => WorkforceNotifier(companyId),
);

/// Fetches and caches the compliance status for a company.
class ComplianceStatusNotifier
    extends AsyncNotifier<ComplianceStatus> {
  ComplianceStatusNotifier(this._companyId);

  final int _companyId;

  @override
  Future<ComplianceStatus> build() {
    return ref
        .read(complianceRepositoryProvider)
        .getStatus(_companyId);
  }

  /// Forces a refresh of the compliance status.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(complianceRepositoryProvider)
          .getStatus(_companyId),
    );
  }
}

/// Provider for [ComplianceStatusNotifier], parameterized by company ID.
final complianceStatusProvider = AsyncNotifierProvider.family<
    ComplianceStatusNotifier, ComplianceStatus, int>(
  (companyId) => ComplianceStatusNotifier(companyId),
);

/// Fetches and caches conversation history by conversation ID.
class AdvisoryHistoryNotifier extends AsyncNotifier<AdvisoryHistory> {
  AdvisoryHistoryNotifier(this._conversationId);

  final int _conversationId;

  @override
  Future<AdvisoryHistory> build() {
    return ref
        .read(advisoryRepositoryProvider)
        .getHistory(_conversationId);
  }

  /// Forces a refresh of the conversation history.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref
          .read(advisoryRepositoryProvider)
          .getHistory(_conversationId),
    );
  }
}

/// Provider for [AdvisoryHistoryNotifier], parameterized by
/// conversation ID.
final advisoryHistoryProvider = AsyncNotifierProvider.family<
    AdvisoryHistoryNotifier, AdvisoryHistory, int>(
  (conversationId) => AdvisoryHistoryNotifier(conversationId),
);

// ── Non-Family Data Providers ──────────────────────────────────────────────

/// Fetches and caches the list of document templates.
class DocumentTemplatesNotifier
    extends AsyncNotifier<List<Template>> {
  @override
  Future<List<Template>> build() {
    return ref.read(documentRepositoryProvider).getTemplates();
  }

  /// Forces a refresh of the template list.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(documentRepositoryProvider).getTemplates(),
    );
  }
}

/// Provider for [DocumentTemplatesNotifier].
final documentTemplatesProvider = AsyncNotifierProvider<
    DocumentTemplatesNotifier, List<Template>>(
  DocumentTemplatesNotifier.new,
);

/// Fetches and caches the list of legislative acts.
class ActsNotifier extends AsyncNotifier<List<Act>> {
  @override
  Future<List<Act>> build() {
    return ref.read(kbRepositoryProvider).getActs();
  }

  /// Forces a refresh of the acts list.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(kbRepositoryProvider).getActs(),
    );
  }
}

/// Provider for [ActsNotifier].
final actsProvider =
    AsyncNotifierProvider<ActsNotifier, List<Act>>(
  ActsNotifier.new,
);

/// Fetches and caches the list of regulatory domains.
class DomainsNotifier extends AsyncNotifier<List<Domain>> {
  @override
  Future<List<Domain>> build() {
    return ref.read(kbRepositoryProvider).getDomains();
  }

  /// Forces a refresh of the domains list.
  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(
      () => ref.read(kbRepositoryProvider).getDomains(),
    );
  }
}

/// Provider for [DomainsNotifier].
final domainsProvider =
    AsyncNotifierProvider<DomainsNotifier, List<Domain>>(
  DomainsNotifier.new,
);

/// Fetches and caches a single provision by ID.
class ProvisionNotifier extends AsyncNotifier<Provision> {
  ProvisionNotifier(this._provisionId);

  final int _provisionId;

  @override
  Future<Provision> build() {
    return ref
        .read(kbRepositoryProvider)
        .getProvision(_provisionId);
  }
}

/// Provider for [ProvisionNotifier], parameterized by provision ID.
final provisionProvider = AsyncNotifierProvider.family<
    ProvisionNotifier, Provision, int>(
  (provisionId) => ProvisionNotifier(provisionId),
);

// ── One-shot Action Providers ──────────────────────────────────────────────
//
// These are not cached notifiers — they are used for user-initiated actions
// (e.g. submitting a query, running a calculation). Feature-level widgets
// typically call the repository directly and manage local loading state.
//
// Example usage:
//   final result = await ref.read(calculatorRepositoryProvider).calculateCpf(...);
//
// Or wrap in a feature-level notifier if the result needs to be shared.
