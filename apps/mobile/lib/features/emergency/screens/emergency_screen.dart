import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import 'emergency_detail_screen.dart';

// ---------------------------------------------------------------------------
// Data models
// ---------------------------------------------------------------------------

class EmergencyStep {
  const EmergencyStep({
    required this.stepNumber,
    required this.action,
    required this.deadline,
    required this.detail,
  });

  final int stepNumber;
  final String action;
  final String deadline;
  final String detail;
}

class EmergencyTopic {
  const EmergencyTopic({
    required this.topicId,
    required this.title,
    required this.icon,
    required this.description,
    required this.immediateObligations,
    required this.documentsNeeded,
    required this.processSteps,
    required this.whenToGetHelp,
    required this.keyProvisions,
  });

  final String topicId;
  final String title;
  final IconData icon;
  final String description;
  final List<EmergencyStep> immediateObligations;
  final List<String> documentsNeeded;
  final List<EmergencyStep> processSteps;
  final List<String> whenToGetHelp;
  final List<String> keyProvisions;
}

// ---------------------------------------------------------------------------
// Emergency data — mirrored from emergency_responses.py
// ---------------------------------------------------------------------------

const List<EmergencyTopic> emergencyTopics = [
  EmergencyTopic(
    topicId: 'tadm-claim',
    title: 'TADM / ECT Claim Against You',
    icon: Icons.gavel,
    description:
        'An employee or ex-employee has filed a claim with the Tripartite '
        'Alliance for Dispute Management (TADM) or Employment Claims '
        'Tribunal (ECT).',
    immediateObligations: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Do NOT contact the claimant directly about the claim',
        deadline: 'Immediately',
        detail: 'All communication should go through TADM mediation.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Gather all relevant employment records',
        deadline: 'Within 3 working days',
        detail: 'TADM will request documentation during mediation.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Attend the mediation session',
        deadline: 'As scheduled by TADM',
        detail:
            'Non-attendance may result in the claim proceeding to ECT '
            'without your input.',
      ),
    ],
    documentsNeeded: [
      'Employment contract and KET',
      'Payslips for the claim period',
      'Leave records',
      'Any written warnings or performance records',
      'Termination letter (if applicable)',
      'CPF contribution records',
      'Correspondence with the employee about the disputed matter',
    ],
    processSteps: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Receive TADM notice',
        deadline: 'Day 0',
        detail: 'You will receive written notice of the claim with details.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Prepare your response and documents',
        deadline: 'Days 1-3',
        detail: 'Organize all evidence supporting your position.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Attend TADM mediation',
        deadline: 'Typically within 4 weeks',
        detail: 'A mediator will help both parties reach resolution.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'If unresolved, claim proceeds to ECT',
        deadline: 'Within 4 weeks of failed mediation',
        detail: 'ECT is a tribunal hearing — more formal than mediation.',
      ),
      EmergencyStep(
        stepNumber: 5,
        action: 'ECT hearing and decision',
        deadline: 'Scheduled by ECT',
        detail:
            'Tribunal makes a binding decision. Claims limited to \$20,000 '
            '(or \$30,000 with union).',
      ),
    ],
    whenToGetHelp: [
      'The claim amount exceeds \$10,000',
      'Multiple employees have filed claims simultaneously',
      'The claim involves allegations of discrimination or wrongful dismissal',
      'You are unsure whether your employment practices are compliant',
      'You need representation at ECT',
    ],
    keyProvisions: [
      'EA-S14-misconduct-dismissal',
      'EA-S22-final-payment',
      'TADM-ECT-process',
    ],
  ),
  EmergencyTopic(
    topicId: 'workplace-injury',
    title: 'Workplace Injury',
    icon: Icons.local_hospital,
    description:
        'An employee has been injured at work. You have immediate legal '
        'obligations under the Work Injury Compensation Act (WICA) and '
        'Workplace Safety and Health Act (WSH Act).',
    immediateObligations: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Ensure the injured employee receives medical attention',
        deadline: 'Immediately',
        detail: 'Call 995 for emergencies. Do NOT delay treatment.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Secure the accident scene',
        deadline: 'Immediately',
        detail:
            'Preserve evidence. Do not disturb the scene for serious injuries.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Report to MOM if serious injury or death',
        deadline: 'Within 24 hours',
        detail:
            'WSH (Incident Reporting) Regulations require immediate '
            'notification for fatal or dangerous incidents.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'File incident report with MOM via iReport',
        deadline: 'Within 10 days',
        detail:
            'Required for all workplace injuries resulting in >3 days MC.',
      ),
    ],
    documentsNeeded: [
      'Accident/incident report form',
      'Medical certificate and medical reports',
      'Witness statements',
      'Photos of the accident scene',
      'Employee\'s employment records',
      'Safety training records for the employee',
      'Risk assessment for the work activity',
      'WICA insurance policy details',
    ],
    processSteps: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Provide immediate medical assistance',
        deadline: 'Day 0',
        detail: 'Employee\'s health comes first.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Notify MOM via iReport',
        deadline: 'Within 10 days',
        detail: 'Submit the incident report with all required details.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Notify your WICA insurer',
        deadline: 'Within 14 days',
        detail: 'Your insurer will manage the compensation claim.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'Continue paying medical leave wages',
        deadline: 'Ongoing',
        detail: 'EA s89: Paid sick leave and hospitalisation leave apply.',
      ),
      EmergencyStep(
        stepNumber: 5,
        action: 'Cooperate with MOM investigation',
        deadline: 'As required',
        detail: 'MOM may investigate workplace safety compliance.',
      ),
    ],
    whenToGetHelp: [
      'The injury is fatal or results in permanent disability',
      'MOM has initiated a WSH investigation',
      'The employee disputes the compensation amount',
      'You do not have valid WICA insurance',
      'Multiple injuries have occurred at your workplace',
    ],
    keyProvisions: [
      'WICA-employer-obligations',
      'WSH-incident-reporting',
      'EA-S89-sick-leave',
    ],
  ),
  EmergencyTopic(
    topicId: 'wrongful-dismissal',
    title: 'Wrongful Dismissal Allegation',
    icon: Icons.person_off,
    description:
        'A terminated employee is alleging wrongful dismissal. This could '
        'lead to TADM mediation, ECT claim, or MOM investigation.',
    immediateObligations: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Review the termination decision and documentation',
        deadline: 'Immediately',
        detail:
            'Ensure you have written records of the reason for termination.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Verify notice period was served or paid in lieu',
        deadline: 'Immediately',
        detail: 'EA s10 and s11 require proper notice.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Ensure all final payments are made',
        deadline: 'Within 3 working days of last day',
        detail: 'EA s22: salary, leave encashment, any outstanding payments.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'File IR21 with IRAS',
        deadline: 'At least 1 month before cessation',
        detail: 'Tax clearance is mandatory for all cessations.',
      ),
    ],
    documentsNeeded: [
      'Employment contract',
      'Termination letter with stated reason',
      'Performance appraisals and warning letters',
      'Evidence supporting the reason for termination',
      'Payslips and CPF records',
      'Proof of final payment',
      'Notice period calculation',
      'Any correspondence with the employee about the termination',
    ],
    processSteps: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Document your position thoroughly',
        deadline: 'Days 1-3',
        detail: 'Write down the timeline and reasons clearly.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Review against TGFEP fair dismissal guidelines',
        deadline: 'Days 1-3',
        detail:
            'Ensure the dismissal was for valid reasons with proper process.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'If TADM claim filed, prepare for mediation',
        deadline: 'Within 4 weeks',
        detail: 'Gather all documentation and attend mediation.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'If ECT proceeding, consider legal representation',
        deadline: 'As scheduled',
        detail: 'ECT has a 1-year limitation from dismissal date.',
      ),
    ],
    whenToGetHelp: [
      'The employee was dismissed during pregnancy or maternity leave',
      'The dismissal may relate to union activity or whistleblowing',
      'There are allegations of discrimination (age, race, gender, disability)',
      'You did not follow a proper due inquiry process (EA s14)',
      'Multiple wrongful dismissal claims have been filed',
    ],
    keyProvisions: [
      'EA-S14-misconduct-dismissal',
      'EA-S10-notice',
      'EA-S11-salary-in-lieu',
      'TGFEP-fair-dismissal',
    ],
  ),
  EmergencyTopic(
    topicId: 'mom-inspection',
    title: 'MOM Inspection or Audit',
    icon: Icons.policy,
    description:
        'The Ministry of Manpower is conducting an inspection of your '
        'workplace. This could be routine or triggered by a complaint.',
    immediateObligations: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Cooperate fully with MOM officers',
        deadline: 'Immediately',
        detail: 'Obstruction of MOM officers is a criminal offence.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Designate a point of contact for the inspection',
        deadline: 'Immediately',
        detail: 'One person should coordinate all information requests.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Gather all required records',
        deadline: 'As requested',
        detail: 'MOM can request records going back 2 years.',
      ),
    ],
    documentsNeeded: [
      'Employment contracts and KETs for all employees',
      'Payslips for the past 2 years',
      'CPF contribution records',
      'Leave records',
      'Working hours and overtime records',
      'Foreign worker employment passes and conditions',
      'Workplace safety and health records',
      'Insurance policies (WICA, etc.)',
    ],
    processSteps: [
      EmergencyStep(
        stepNumber: 1,
        action: 'MOM issues inspection notice',
        deadline: 'Day 0',
        detail: 'May be scheduled or unannounced.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Prepare all requested documents',
        deadline: 'Before inspection',
        detail: 'Organize by employee and category.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'MOM conducts on-site inspection',
        deadline: 'Inspection day',
        detail: 'Officers may interview employees directly.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'MOM issues findings',
        deadline: '1-4 weeks after inspection',
        detail:
            'May include rectification orders or prosecution notices.',
      ),
      EmergencyStep(
        stepNumber: 5,
        action: 'Rectify any findings within deadline',
        deadline: 'As specified by MOM',
        detail: 'Failure to comply can result in prosecution.',
      ),
    ],
    whenToGetHelp: [
      'MOM has found potential violations',
      'You are unsure if your records are complete',
      'The inspection involves foreign worker compliance',
      'MOM has issued a stop-work order',
      'Prosecution proceedings have been initiated',
    ],
    keyProvisions: [
      'EA-S95-KETs',
      'EA-S88A-payslip',
      'EA-S21-salary-payment',
      'EFMA-conditions',
    ],
  ),
  EmergencyTopic(
    topicId: 'discrimination-complaint',
    title: 'Discrimination or Harassment Complaint',
    icon: Icons.report_problem,
    description:
        'An employee has raised a discrimination or harassment complaint. '
        'This could involve TAFEP investigation if escalated.',
    immediateObligations: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Take the complaint seriously — acknowledge receipt',
        deadline: 'Within 24 hours',
        detail: 'Document the complaint in writing.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Ensure the complainant is not subjected to retaliation',
        deadline: 'Immediately',
        detail: 'Retaliation can result in additional claims.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Begin internal investigation',
        deadline: 'Within 1 week',
        detail:
            'Appoint an impartial investigator (not the alleged '
            'harasser\'s manager).',
      ),
    ],
    documentsNeeded: [
      'Written complaint from the employee',
      'Company anti-harassment/discrimination policy',
      'Statements from all parties involved',
      'Witness statements',
      'Relevant email or message records',
      'HR records of any prior complaints',
    ],
    processSteps: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Receive and document the complaint',
        deadline: 'Day 0',
        detail: 'Record all details accurately.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Conduct confidential investigation',
        deadline: 'Weeks 1-3',
        detail: 'Interview all relevant parties, review evidence.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Determine findings and take action',
        deadline: 'Week 3-4',
        detail:
            'Outcomes may include mediation, warning, disciplinary action, '
            'or policy changes.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'Communicate outcome to all parties',
        deadline: 'After investigation',
        detail: 'Both complainant and respondent should be informed.',
      ),
      EmergencyStep(
        stepNumber: 5,
        action: 'Follow up and monitor',
        deadline: 'Ongoing',
        detail: 'Ensure no retaliation and the situation is resolved.',
      ),
    ],
    whenToGetHelp: [
      'The complaint involves sexual harassment or assault',
      'A TAFEP complaint has been filed',
      'The alleged discriminator is in senior management',
      'Multiple complaints have been filed about the same person or issue',
      'The company does not have an anti-harassment policy',
    ],
    keyProvisions: [
      'TGFEP-fair-employment',
      'TAFEP-complaint-process',
      'WFA-workplace-fairness',
    ],
  ),
  EmergencyTopic(
    topicId: 'data-breach',
    title: 'Employee Data Breach',
    icon: Icons.security,
    description:
        'Employee personal data has been exposed, leaked, or accessed '
        'without authorization. Singapore\'s PDPA requires prompt action.',
    immediateObligations: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Contain the breach',
        deadline: 'Immediately',
        detail: 'Stop the unauthorized access, secure affected systems.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Assess the scope of the breach',
        deadline: 'Within 24 hours',
        detail:
            'Determine what data was exposed and how many people are affected.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Notify PDPC if significant harm likely',
        deadline: 'Within 3 calendar days',
        detail:
            'PDPA mandatory breach notification for notifiable data breaches.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'Notify affected individuals',
        deadline: 'As soon as practicable',
        detail:
            'If the breach is likely to result in significant harm.',
      ),
    ],
    documentsNeeded: [
      'Incident log with timeline',
      'List of affected data and individuals',
      'Description of data protection measures in place',
      'Evidence of how the breach occurred',
      'Remediation actions taken',
      'PDPC notification form (if applicable)',
    ],
    processSteps: [
      EmergencyStep(
        stepNumber: 1,
        action: 'Contain and assess the breach',
        deadline: 'Day 0-1',
        detail: 'Identify scope and stop ongoing exposure.',
      ),
      EmergencyStep(
        stepNumber: 2,
        action: 'Notify PDPC (if notifiable breach)',
        deadline: 'Within 3 days',
        detail: 'Use the PDPC data breach notification form.',
      ),
      EmergencyStep(
        stepNumber: 3,
        action: 'Notify affected individuals',
        deadline: 'As soon as practicable',
        detail:
            'Clear, plain language about what happened and what to do.',
      ),
      EmergencyStep(
        stepNumber: 4,
        action: 'Investigate root cause',
        deadline: 'Weeks 1-2',
        detail:
            'Determine how the breach occurred and fix the vulnerability.',
      ),
      EmergencyStep(
        stepNumber: 5,
        action: 'Review and strengthen data protection',
        deadline: 'Ongoing',
        detail: 'Update policies, training, and technical measures.',
      ),
    ],
    whenToGetHelp: [
      'The breach involves NRIC numbers, financial data, or health records',
      'More than 500 individuals are affected',
      'The breach was caused by a malicious attack',
      'You are unsure whether the breach is notifiable to PDPC',
      'Affected individuals have suffered or may suffer significant harm',
    ],
    keyProvisions: [
      'PDPA-breach-notification',
      'PDPA-protection-obligation',
      'PDPA-accountability',
    ],
  ),
];

/// Lookup helper — returns null if the topicId is not found.
EmergencyTopic? findEmergencyTopic(String topicId) {
  for (final topic in emergencyTopics) {
    if (topic.topicId == topicId) return topic;
  }
  return null;
}

// ---------------------------------------------------------------------------
// Emergency Hub Screen
// ---------------------------------------------------------------------------

class EmergencyScreen extends StatelessWidget {
  const EmergencyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergency HR Situations'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.base),
        children: [
          // Warning banner
          const AlertBanner(
            title: 'Important',
            description:
                'These guides provide immediate steps. For complex '
                'situations, always consult an employment law specialist.',
            variant: AlertBannerVariant.error,
          ),
          const SizedBox(height: AppSpacing.lg),

          // Emergency type cards
          ...emergencyTopics.map(
            (topic) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: _EmergencyCard(topic: topic),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Single emergency card with red left border
// ---------------------------------------------------------------------------

class _EmergencyCard extends StatelessWidget {
  const _EmergencyCard({required this.topic});

  final EmergencyTopic topic;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      padding: EdgeInsets.zero,
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => EmergencyDetailScreen(topicId: topic.topicId),
          ),
        );
      },
      child: Container(
        decoration: const BoxDecoration(
          border: Border(
            left: BorderSide(
              color: AppColors.riskRed,
              width: 4,
            ),
          ),
        ),
        padding: const EdgeInsets.all(AppSpacing.base),
        child: Row(
          children: [
            // Icon container
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: AppColors.riskRedBg,
                borderRadius: AppRadius.md,
              ),
              child: Icon(
                topic.icon,
                color: AppColors.riskRed,
                size: 24,
              ),
            ),
            const SizedBox(width: AppSpacing.md),

            // Title and description
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    topic.title,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.neutralGray900,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    topic.description,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.neutralGray500,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),

            // Chevron
            const Icon(
              Icons.chevron_right,
              color: AppColors.neutralGray400,
              size: 24,
            ),
          ],
        ),
      ),
    );
  }
}
