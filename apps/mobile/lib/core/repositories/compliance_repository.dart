import 'package:dio/dio.dart';

import '../models/compliance.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';

/// Repository for the Compliance API domain.
///
/// Provides typed access to compliance checks, status monitoring,
/// and gap analysis.
class ComplianceRepository {
  const ComplianceRepository({required ApiClient client})
      : _client = client;

  final ApiClient _client;

  /// Runs a compliance check for the given company.
  ///
  /// Optionally filters to specific [domains] (e.g. "Employment", "CPF").
  Future<ComplianceResult> check({
    required int companyId,
    List<String>? domains,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/compliance/check',
        data: <String, dynamic>{
          'company_id': companyId,
          'domains': ?domains,
        },
      );
      return ComplianceResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Fetches the current compliance status for a company.
  Future<ComplianceStatus> getStatus(int companyId) async {
    try {
      final response =
          await _client.dio.get<Map<String, dynamic>>(
        '/compliance/status/$companyId',
      );
      return ComplianceStatus.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Performs a gap analysis identifying areas of non-compliance.
  Future<GapAnalysisResult> gapAnalysis({
    required int companyId,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/compliance/gap-analysis',
        data: <String, dynamic>{
          'company_id': companyId,
        },
      );
      return GapAnalysisResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
