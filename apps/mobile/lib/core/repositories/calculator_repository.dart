import 'package:dio/dio.dart';

import '../models/calculator.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';

/// Repository for the Calculator API domain.
///
/// Provides typed access to CPF, leave entitlement, and salary
/// calculation endpoints.
class CalculatorRepository {
  const CalculatorRepository({required ApiClient client})
      : _client = client;

  final ApiClient _client;

  /// Calculates CPF contributions based on salary, age, and citizenship.
  Future<CpfResult> calculateCpf({
    required double grossSalary,
    required int employeeAge,
    required String citizenshipStatus,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/calculator/cpf',
        data: <String, dynamic>{
          'gross_salary': grossSalary,
          'employee_age': employeeAge,
          'citizenship_status': citizenshipStatus,
        },
      );
      return CpfResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Calculates leave entitlements based on service years and employment
  /// type.
  Future<LeaveResult> calculateLeave({
    required int yearsOfService,
    required String employmentType,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/calculator/leave',
        data: <String, dynamic>{
          'years_of_service': yearsOfService,
          'employment_type': employmentType,
        },
      );
      return LeaveResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Calculates a full salary breakdown including CPF and net pay.
  Future<SalaryResult> calculateSalary({
    required double grossSalary,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/calculator/salary',
        data: <String, dynamic>{
          'gross_salary': grossSalary,
        },
      );
      return SalaryResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
