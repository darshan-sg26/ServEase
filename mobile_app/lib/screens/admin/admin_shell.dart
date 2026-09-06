import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';

class AdminShell extends StatefulWidget {
  const AdminShell({super.key});

  @override
  State<AdminShell> createState() => _AdminShellState();
}

class _AdminShellState extends State<AdminShell> with WidgetsBindingObserver {
  PlatformAnalytics? _analytics;
  List<FraudFlag> _fraudFlags = [];
  bool _isLoading = true;
  bool _isFetching = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadAdminData();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _loadAdminData(background: true);
    }
  }

  Future<void> _loadAdminData({bool background = false}) async {
    if (_isFetching) return;
    _isFetching = true;
    if (!background && _analytics == null) {
      setState(() => _isLoading = true);
    }
    try {
      final a = await ApiService.fetchAnalytics();
      final f = await ApiService.fetchFraudFlags();
      if (mounted) {
        setState(() {
          _analytics = a;
          _fraudFlags = f;
          _isLoading = false;
        });
      }
    } catch (e) {
      // Safely handle error
    } finally {
      _isFetching = false;
      if (mounted && _isLoading) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.cream50,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.admin_panel_settings_rounded, color: AppColors.goldAccent, size: 24),
            const SizedBox(width: 10),
            Text(ApiService.currentUserName.isNotEmpty ? ApiService.currentUserName : 'Admin Console'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: AppColors.white),
            tooltip: 'Sign Out',
            onPressed: () {
              ApiService.logout();
              Navigator.pushReplacementNamed(context, '/');
            },
          ),
        ],
      ),
      body: SafeArea(
        child: _isLoading
            ? const AppResponsiveContainer(child: AppLoadingSkeleton(count: 3))
            : RefreshIndicator(
                onRefresh: _loadAdminData,
                color: AppColors.forest900,
                child: SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: AppResponsiveContainer(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        AppSectionHeader(
                          title: 'Platform Analytics & Overview',
                          subtitle: 'Real-time marketplace metrics and transaction performance',
                          trailing: IconButton(
                            icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                            onPressed: () => _loadAdminData(background: true),
                            tooltip: 'Refresh Metrics',
                          ),
                        ),
                        const SizedBox(height: 10),

                        // Metric Stat Cards Grid
                        LayoutBuilder(
                          builder: (context, constraints) {
                            final isDesktop = constraints.maxWidth > 700;
                            return GridView.count(
                              crossAxisCount: isDesktop ? 4 : 2,
                              shrinkWrap: true,
                              physics: const NeverScrollableScrollPhysics(),
                              mainAxisSpacing: 10,
                              crossAxisSpacing: 10,
                              childAspectRatio: isDesktop ? 1.8 : 1.25,
                              children: [
                                _StatCard(
                                  title: 'Total Users',
                                  value: '${_analytics?.totalUsers ?? 0}',
                                  icon: Icons.people_alt_rounded,
                                  color: AppColors.forest900,
                                ),
                                _StatCard(
                                  title: 'Completed Jobs',
                                  value: '${_analytics?.completedJobs ?? 0}',
                                  icon: Icons.verified_rounded,
                                  color: AppColors.success,
                                ),
                                _StatCard(
                                  title: 'Direct Offers',
                                  value: '${_analytics?.totalDirectOffers ?? 0}',
                                  icon: Icons.send_rounded,
                                  color: const Color(0xFFD97706),
                                ),
                                _StatCard(
                                  title: 'Security Flags',
                                  value: '${_analytics?.openFraudFlags ?? 0}',
                                  icon: Icons.security_rounded,
                                  color: AppColors.error,
                                ),
                              ],
                            );
                          },
                        ),
                        const SizedBox(height: 18),

                        // Channel Breakdown Card
                        AppCard(
                          padding: const EdgeInsets.all(18),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Row(
                                children: [
                                  Icon(Icons.pie_chart_outline_rounded, color: AppColors.forest900, size: 20),
                                  SizedBox(width: 8),
                                  Text(
                                    'Hiring Channel Breakdown',
                                    style: TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 15),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 4),
                              const Text(
                                'Open Marketplace Job Postings vs Direct Offer Outreach Volume',
                                style: TextStyle(fontSize: 12, color: AppColors.slate600),
                              ),
                              const SizedBox(height: 14),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceAround,
                                children: [
                                  Expanded(
                                    child: Column(
                                      children: [
                                        const Text('Open Jobs Feed', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600)),
                                        const SizedBox(height: 4),
                                        Text(
                                          '${_analytics?.pathAJobsCount ?? 0}',
                                          style: const TextStyle(fontFamily: 'Sora', fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.forest900),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Container(height: 36, width: 1, color: AppColors.border),
                                  Expanded(
                                    child: Column(
                                      children: [
                                        const Text('Direct Offer Hiring', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600)),
                                        const SizedBox(height: 4),
                                        Text(
                                          '${_analytics?.pathBJobsCount ?? 0}',
                                          style: const TextStyle(fontFamily: 'Sora', fontSize: 22, fontWeight: FontWeight.bold, color: AppColors.goldAccent),
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: 20),

                        // Isolation Forest Fraud Detection Queue
                        AppSectionHeader(
                          title: 'Security & Anomaly Queue',
                          subtitle: 'Isolation Forest AI model security scan results',
                          trailing: IconButton(
                            icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                            onPressed: _loadAdminData,
                            tooltip: 'Refresh Queue',
                          ),
                        ),
                        const SizedBox(height: 8),

                        _fraudFlags.isEmpty
                            ? const AppEmptyState(
                                icon: Icons.shield_rounded,
                                title: 'System Security 100% Healthy',
                                description: 'Isolation Forest anomaly model scanned active user vectors. Zero security flags open.',
                              )
                            : ListView.separated(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: _fraudFlags.length,
                                separatorBuilder: (_, __) => const SizedBox(height: 10),
                                itemBuilder: (context, index) {
                                  final flag = _fraudFlags[index];
                                  return AppCard(
                                    padding: const EdgeInsets.all(12),
                                    child: Row(
                                      children: [
                                        Container(
                                          padding: const EdgeInsets.all(8),
                                          decoration: BoxDecoration(
                                            color: AppColors.error.withValues(alpha: 0.1),
                                            shape: BoxShape.circle,
                                          ),
                                          child: const Icon(Icons.warning_amber_rounded, color: AppColors.error, size: 20),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                'User #${flag.userId} (${flag.userEmail})',
                                                style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 13),
                                                maxLines: 1,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                              const SizedBox(height: 2),
                                              Text(flag.reason, style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
                                            ],
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        AppBadge(
                                          label: '${flag.anomalyScore}',
                                          backgroundColor: AppColors.error.withValues(alpha: 0.15),
                                          textColor: AppColors.error,
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                        const SizedBox(height: 32),
                      ],
                    ),
                  ),
                ),
              ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.slate600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(icon, size: 16, color: color),
            ],
          ),
          Text(
            value,
            style: TextStyle(fontFamily: 'Sora', fontSize: 20, fontWeight: FontWeight.bold, color: color),
          ),
        ],
      ),
    );
  }
}
