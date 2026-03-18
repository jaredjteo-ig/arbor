/// Metadata for a document template in the template library.
class TemplateDefinition {
  const TemplateDefinition({
    required this.id,
    required this.name,
    required this.description,
    required this.category,
    required this.templateType,
    required this.provisionsCount,
    this.complianceNotes = const [],
    this.requiredFields = const [],
    this.optionalFields = const [],
  });

  final int id;
  final String name;
  final String description;
  final String category;
  final String templateType;
  final int provisionsCount;
  final List<String> complianceNotes;
  final List<String> requiredFields;
  final List<String> optionalFields;

  /// All available templates in display order.
  static const List<TemplateDefinition> all = [
    TemplateDefinition(
      id: 1,
      name: 'Employment Contract (Full-Time)',
      description:
          'EA-compliant full-time employment contract including all Key Employment Terms (KET).',
      category: 'Contracts',
      templateType: 'contract',
      provisionsCount: 7,
      complianceNotes: [
        'KET must be issued within 14 days of employment start (EA s95A)',
        'Salary must be paid within 7 days of salary period end (EA s21)',
      ],
      requiredFields: [
        'company_name', 'company_uen', 'company_address', 'employee_name',
        'nric_fin', 'job_title', 'department', 'start_date',
        'basic_monthly_salary', 'salary_period',
      ],
      optionalFields: [
        'probation_period_months', 'fixed_allowances', 'variable_allowances',
        'overtime_rate', 'notice_period_weeks', 'work_hours_per_day', 'rest_day',
      ],
    ),
    TemplateDefinition(
      id: 2,
      name: 'Employment Contract (Part-Time)',
      description:
          'EA-compliant part-time employment contract with pro-rated entitlements.',
      category: 'Contracts',
      templateType: 'contract',
      provisionsCount: 4,
      complianceNotes: [
        'Part-time employee: works <35 hours/week',
        'Leave entitlements pro-rated based on hours worked',
      ],
      requiredFields: [
        'company_name', 'company_uen', 'employee_name', 'nric_fin',
        'job_title', 'start_date', 'hourly_rate', 'hours_per_week',
      ],
      optionalFields: ['days_per_week', 'specific_work_days'],
    ),
    TemplateDefinition(
      id: 3,
      name: 'Key Employment Terms (KET)',
      description:
          'Standalone KET document compliant with EA s95A.',
      category: 'Contracts',
      templateType: 'ket',
      provisionsCount: 3,
      complianceNotes: [
        'Must be issued within 14 days of employment start (EA s95A)',
        'Non-compliance: Fine up to \$5,000 per offence',
      ],
      requiredFields: [
        'company_name', 'employee_name', 'job_title', 'start_date',
        'basic_monthly_salary', 'salary_period', 'work_hours_per_day',
        'rest_day', 'notice_period_weeks',
      ],
      optionalFields: ['fixed_allowances', 'deductions'],
    ),
    TemplateDefinition(
      id: 4,
      name: 'Annual Leave Policy',
      description: 'Company annual leave policy aligned with EA leave schedule.',
      category: 'Policies',
      templateType: 'policy',
      provisionsCount: 2,
      complianceNotes: [
        'Minimum annual leave per EA: 7 days (1st year) to 14 days (8th+ year)',
      ],
      requiredFields: ['company_name'],
      optionalFields: ['additional_leave_days', 'carry_forward_limit'],
    ),
    TemplateDefinition(
      id: 5,
      name: 'Sick Leave Policy',
      description: 'Company sick leave and medical certificate policy per EA s89.',
      category: 'Policies',
      templateType: 'policy',
      provisionsCount: 2,
      complianceNotes: [
        'EA s89: 14 days outpatient + 60 days hospitalisation (inclusive)',
      ],
      requiredFields: ['company_name'],
      optionalFields: ['panel_clinic_details'],
    ),
    TemplateDefinition(
      id: 6,
      name: 'Termination Letter (With Notice)',
      description: 'Employer termination letter with notice period per EA s10.',
      category: 'Letters',
      templateType: 'letter',
      provisionsCount: 3,
      complianceNotes: [
        'Notice period must match contract or EA minimum (EA s10)',
        'Final salary within 3 working days of last day (EA s22)',
      ],
      requiredFields: [
        'company_name', 'employee_name', 'job_title', 'termination_date',
        'last_working_day', 'notice_period_weeks', 'reason_for_termination',
      ],
      optionalFields: ['encashment_details', 'return_of_property'],
    ),
    TemplateDefinition(
      id: 7,
      name: 'Resignation Acceptance Letter',
      description: 'Formal acceptance of employee resignation.',
      category: 'Letters',
      templateType: 'letter',
      provisionsCount: 2,
      complianceNotes: ['Final payment within 3 working days (EA s22)'],
      requiredFields: [
        'company_name', 'employee_name', 'job_title',
        'resignation_date', 'last_working_day',
      ],
      optionalFields: ['handover_instructions'],
    ),
    TemplateDefinition(
      id: 8,
      name: 'Warning Letter',
      description:
          'Formal warning letter for misconduct or poor performance (1st/2nd/final).',
      category: 'Letters',
      templateType: 'letter',
      provisionsCount: 2,
      complianceNotes: [
        'Due inquiry before summary dismissal (EA s14)',
        'Progressive discipline recommended (TGFEP)',
      ],
      requiredFields: [
        'company_name', 'employee_name', 'job_title', 'warning_level',
        'incident_date', 'incident_description', 'expected_improvement',
      ],
      optionalFields: ['previous_warnings', 'improvement_deadline'],
    ),
    TemplateDefinition(
      id: 9,
      name: 'FWA Request Form',
      description: 'Flexible Work Arrangement request form per TG-FWAR guidelines.',
      category: 'Forms',
      templateType: 'form',
      provisionsCount: 3,
      complianceNotes: [
        'Employer must respond within 2 months (TG-FWAR)',
      ],
      requiredFields: [
        'company_name', 'employee_name', 'job_title', 'department',
        'fwa_type', 'proposed_start_date', 'reason',
      ],
      optionalFields: ['proposed_schedule', 'impact_assessment'],
    ),
    TemplateDefinition(
      id: 10,
      name: 'Flexible Work Arrangement Policy',
      description: 'Company FWA policy aligned with TG-FWAR guidelines.',
      category: 'Policies',
      templateType: 'policy',
      provisionsCount: 4,
      complianceNotes: [
        'All employees can request FWA from 1 December 2024 (TG-FWAR)',
      ],
      requiredFields: ['company_name'],
      optionalFields: ['eligible_roles', 'excluded_roles'],
    ),
    TemplateDefinition(
      id: 11,
      name: 'Expense Claims Form',
      description: 'Standard expense reimbursement form with approval workflow.',
      category: 'Forms',
      templateType: 'form',
      provisionsCount: 1,
      complianceNotes: [
        'EA s27: Deductions from salary require written consent',
      ],
      requiredFields: ['company_name', 'employee_name', 'department'],
      optionalFields: ['expense_categories', 'approval_limit'],
    ),
    TemplateDefinition(
      id: 12,
      name: 'Timesheet Template',
      description: 'Weekly timesheet for recording hours, overtime, and rest days.',
      category: 'Forms',
      templateType: 'form',
      provisionsCount: 3,
      complianceNotes: [
        'EA Part IV: Max 8 hours/day or 44 hours/week',
        'Overtime: max 72 hours/month (EA s38)',
      ],
      requiredFields: ['company_name', 'employee_name', 'week_starting'],
    ),
  ];

  /// Look up a template by its ID.
  static TemplateDefinition? fromId(int id) {
    for (final t in all) {
      if (t.id == id) return t;
    }
    return null;
  }
}
