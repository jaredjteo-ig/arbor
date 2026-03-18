import 'package:dio/dio.dart';

import '../models/company.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';

/// Repository for the Profile (Company) API domain.
///
/// Provides typed access to company profile CRUD operations and
/// workforce composition data.
class ProfileRepository {
  const ProfileRepository({required ApiClient client})
      : _client = client;

  final ApiClient _client;

  /// Fetches the company profile for the given ID.
  Future<CompanyProfile> getProfile(int companyId) async {
    try {
      final response =
          await _client.dio.get<Map<String, dynamic>>(
        '/profile/$companyId',
      );
      return CompanyProfile.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Creates a new company profile.
  Future<CompanyProfile> createProfile(
      Map<String, dynamic> data) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/profile/',
        data: data,
      );
      return CompanyProfile.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Updates an existing company profile.
  Future<CompanyProfile> updateProfile(
    int companyId,
    Map<String, dynamic> data,
  ) async {
    try {
      final response =
          await _client.dio.put<Map<String, dynamic>>(
        '/profile/$companyId',
        data: data,
      );
      return CompanyProfile.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Fetches the workforce composition breakdown for a company.
  Future<WorkforceComposition> getWorkforce(int companyId) async {
    try {
      final response =
          await _client.dio.get<Map<String, dynamic>>(
        '/profile/$companyId/workforce',
      );
      return WorkforceComposition.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
