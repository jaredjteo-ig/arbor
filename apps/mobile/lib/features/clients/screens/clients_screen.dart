import 'package:flutter/material.dart';

import '../../../core/design/tokens/tokens.dart';
import '../../../core/design/components/components.dart';

/// Data model for a client company.
class _ClientCompany {
  final int id;
  final String name;
  final String uen;
  final String sector;
  final int employeeCount;
  final int? complianceScore;
  final String? riskTier;
  final String? lastActivity;

  const _ClientCompany({
    required this.id,
    required this.name,
    required this.uen,
    required this.sector,
    required this.employeeCount,
    this.complianceScore,
    this.riskTier,
    this.lastActivity,
  });
}

const _demoClients = [
  _ClientCompany(
    id: 1,
    name: 'Horizon Tech Pte Ltd',
    uen: '202301234A',
    sector: 'Technology',
    employeeCount: 45,
    complianceScore: 85,
    riskTier: 'green',
    lastActivity: '2026-03-11',
  ),
  _ClientCompany(
    id: 2,
    name: 'Marina F&B Group',
    uen: '201912345B',
    sector: 'Food & Beverage',
    employeeCount: 120,
    complianceScore: 62,
    riskTier: 'amber',
    lastActivity: '2026-03-10',
  ),
  _ClientCompany(
    id: 3,
    name: 'BuildSafe Construction',
    uen: '201845678C',
    sector: 'Construction',
    employeeCount: 200,
    complianceScore: 38,
    riskTier: 'red',
    lastActivity: '2026-03-08',
  ),
  _ClientCompany(
    id: 4,
    name: 'Orchid Wellness Clinic',
    uen: '202209876D',
    sector: 'Healthcare',
    employeeCount: 15,
    complianceScore: 92,
    riskTier: 'green',
    lastActivity: '2026-03-12',
  ),
  _ClientCompany(
    id: 5,
    name: 'QuickShip Logistics',
    uen: '202156789E',
    sector: 'Logistics',
    employeeCount: 80,
    complianceScore: 55,
    riskTier: 'amber',
    lastActivity: '2026-03-06',
  ),
  _ClientCompany(
    id: 6,
    name: 'GreenLeaf Trading',
    uen: '202034567F',
    sector: 'Retail',
    employeeCount: 30,
    complianceScore: null,
    riskTier: null,
    lastActivity: null,
  ),
];

const _sectors = [
  'All',
  'Technology',
  'Food & Beverage',
  'Construction',
  'Healthcare',
  'Logistics',
  'Retail',
];

/// Consultant client list with search, filter, and summary metrics.
class ClientsScreen extends StatefulWidget {
  const ClientsScreen({super.key});

  @override
  State<ClientsScreen> createState() => _ClientsScreenState();
}

class _ClientsScreenState extends State<ClientsScreen> {
  String _search = '';
  String _selectedSector = 'All';

  List<_ClientCompany> get _filtered {
    return _demoClients.where((c) {
      final matchSearch = _search.isEmpty ||
          c.name.toLowerCase().contains(_search.toLowerCase()) ||
          c.uen.toLowerCase().contains(_search.toLowerCase());
      final matchSector =
          _selectedSector == 'All' || c.sector == _selectedSector;
      return matchSearch && matchSector;
    }).toList();
  }

  RiskTier? _parseRiskTier(String? tier) {
    return switch (tier) {
      'green' => RiskTier.green,
      'amber' => RiskTier.amber,
      'red' => RiskTier.red,
      _ => null,
    };
  }

  @override
  Widget build(BuildContext context) {
    final clients = _filtered;

    return Scaffold(
      appBar: AppBar(title: const Text('Clients')),
      body: Column(
        children: [
          // Summary metrics
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.base,
              AppSpacing.sm,
              AppSpacing.base,
              0,
            ),
            child: Row(
              children: [
                _MetricChip(
                  label: 'Total',
                  value: '${_demoClients.length}',
                ),
                const SizedBox(width: AppSpacing.sm),
                _MetricChip(
                  label: 'Green',
                  value:
                      '${_demoClients.where((c) => c.riskTier == 'green').length}',
                  color: AppColors.riskGreen,
                ),
                const SizedBox(width: AppSpacing.sm),
                _MetricChip(
                  label: 'Amber',
                  value:
                      '${_demoClients.where((c) => c.riskTier == 'amber').length}',
                  color: AppColors.riskAmber,
                ),
                const SizedBox(width: AppSpacing.sm),
                _MetricChip(
                  label: 'Red',
                  value:
                      '${_demoClients.where((c) => c.riskTier == 'red').length}',
                  color: AppColors.riskRed,
                ),
              ],
            ),
          ),

          // Search
          Padding(
            padding: const EdgeInsets.all(AppSpacing.base),
            child: TextField(
              onChanged: (v) => setState(() => _search = v),
              decoration: InputDecoration(
                hintText: 'Search clients...',
                prefixIcon: const Icon(Icons.search, size: 20),
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSpacing.md,
                ),
                border: OutlineInputBorder(
                  borderRadius: AppRadius.md,
                  borderSide:
                      const BorderSide(color: AppColors.neutralGray200),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: AppRadius.md,
                  borderSide:
                      const BorderSide(color: AppColors.neutralGray200),
                ),
              ),
            ),
          ),

          // Sector filter chips
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding:
                  const EdgeInsets.symmetric(horizontal: AppSpacing.base),
              itemCount: _sectors.length,
              separatorBuilder: (_, _) =>
                  const SizedBox(width: AppSpacing.sm),
              itemBuilder: (context, index) {
                final sector = _sectors[index];
                final selected = _selectedSector == sector;
                return ChoiceChip(
                  label: Text(sector),
                  selected: selected,
                  onSelected: (_) =>
                      setState(() => _selectedSector = sector),
                  selectedColor: AppColors.primaryNavy,
                  labelStyle: TextStyle(
                    color: selected
                        ? AppColors.neutralWhite
                        : AppColors.neutralGray600,
                    fontSize: 13,
                  ),
                  backgroundColor: AppColors.neutralGray100,
                  shape: RoundedRectangleBorder(
                    borderRadius: AppRadius.full,
                  ),
                );
              },
            ),
          ),

          const SizedBox(height: AppSpacing.sm),

          // Client list
          Expanded(
            child: clients.isEmpty
                ? const EmptyState(
                    icon: Icons.people_outlined,
                    heading: 'No clients found',
                    description: 'Try adjusting your search or filters.',
                  )
                : ListView.separated(
                    padding: const EdgeInsets.all(AppSpacing.base),
                    itemCount: clients.length,
                    separatorBuilder: (_, _) =>
                        const SizedBox(height: AppSpacing.sm),
                    itemBuilder: (context, index) {
                      final client = clients[index];
                      return _ClientCard(
                        client: client,
                        riskTier: _parseRiskTier(client.riskTier),
                      );
                    },
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddClientSheet(context),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: AppColors.neutralWhite,
        icon: const Icon(Icons.add),
        label: const Text('Add Client'),
      ),
    );
  }

  void _showAddClientSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => Padding(
        padding: EdgeInsets.fromLTRB(
          AppSpacing.base,
          AppSpacing.base,
          AppSpacing.base,
          MediaQuery.of(context).viewInsets.bottom + AppSpacing.base,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Add New Client', style: AppTypography.title),
            const SizedBox(height: AppSpacing.base),
            TextField(
              decoration: InputDecoration(
                labelText: 'Company Name',
                border:
                    OutlineInputBorder(borderRadius: AppRadius.md),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              decoration: InputDecoration(
                labelText: 'UEN',
                border:
                    OutlineInputBorder(borderRadius: AppRadius.md),
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            TextField(
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: 'Employee Count',
                border:
                    OutlineInputBorder(borderRadius: AppRadius.md),
              ),
            ),
            const SizedBox(height: AppSpacing.base),
            AppButton(
              label: 'Add Client',
              onPressed: () => Navigator.pop(context),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
        ),
      ),
    );
  }
}

class _ClientCard extends StatelessWidget {
  const _ClientCard({required this.client, this.riskTier});

  final _ClientCompany client;
  final RiskTier? riskTier;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Now viewing: ${client.name}'),
            duration: const Duration(seconds: 2),
          ),
        );
      },
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.primaryNavy.withAlpha(25),
                  borderRadius: AppRadius.md,
                ),
                child: const Icon(
                  Icons.business,
                  color: AppColors.primaryNavy,
                  size: 20,
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      client.name,
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppColors.neutralGray900,
                      ),
                    ),
                    Text(
                      client.uen,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray400,
                      ),
                    ),
                  ],
                ),
              ),
              if (riskTier != null) RiskTierBadge(tier: riskTier!),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              _InfoChip(icon: Icons.category, text: client.sector),
              const SizedBox(width: AppSpacing.md),
              _InfoChip(
                icon: Icons.people,
                text: '${client.employeeCount} employees',
              ),
            ],
          ),
          if (client.complianceScore != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Compliance: ${client.complianceScore}/100',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray600,
                  ),
                ),
                if (client.lastActivity != null)
                  Text(
                    _formatDate(client.lastActivity!),
                    style: AppTypography.caption.copyWith(
                      color: AppColors.neutralGray400,
                    ),
                  ),
              ],
            ),
          ] else
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.sm),
              child: Text(
                'No compliance check yet',
                style: AppTypography.caption.copyWith(
                  color: AppColors.neutralGray400,
                ),
              ),
            ),
        ],
      ),
    );
  }

  String _formatDate(String dateStr) {
    final date = DateTime.tryParse(dateStr);
    if (date == null) return dateStr;
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    return '${date.day} ${months[date.month - 1]} ${date.year}';
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: AppColors.neutralGray400),
        const SizedBox(width: AppSpacing.xs),
        Text(
          text,
          style: AppTypography.caption.copyWith(
            color: AppColors.neutralGray500,
          ),
        ),
      ],
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
    this.color,
  });

  final String label;
  final String value;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(
          vertical: AppSpacing.sm,
          horizontal: AppSpacing.md,
        ),
        decoration: BoxDecoration(
          color: AppColors.neutralGray50,
          borderRadius: AppRadius.md,
          border: Border.all(color: AppColors.neutralGray200),
        ),
        child: Column(
          children: [
            Text(
              value,
              style: AppTypography.title.copyWith(
                color: color ?? AppColors.neutralGray900,
              ),
            ),
            Text(
              label,
              style: AppTypography.caption.copyWith(
                color: AppColors.neutralGray500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
