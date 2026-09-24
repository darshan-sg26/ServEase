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
  List<PendingSkillApproval> _pendingSkills = [];
  bool _isLoading = true;
  bool _isFetching = false;
  bool _isSkillsLoading = false;
  String? _skillsError;

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
    if (mounted) {
      setState(() {
        _isSkillsLoading = true;
        _skillsError = null;
      });
    }
    try {
      final results = await Future.wait([
        ApiService.fetchAnalytics(),
        ApiService.fetchFraudFlags(),
        ApiService.fetchPendingSkillApprovals(),
      ]);
      if (mounted) {
        final skillsRes = results[2] as Map<String, dynamic>;
        setState(() {
          _analytics = results[0] as PlatformAnalytics?;
          _fraudFlags = results[1] as List<FraudFlag>;
          if (skillsRes['success'] == true) {
            _pendingSkills = (skillsRes['data'] as List).cast<PendingSkillApproval>();
            _skillsError = null;
          } else {
            _skillsError = skillsRes['error'] as String? ?? 'Failed to load skill approvals.';
            _pendingSkills = [];
          }
          _isSkillsLoading = false;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _skillsError = 'Unexpected error: $e';
          _isSkillsLoading = false;
        });
      }
    } finally {
      _isFetching = false;
      if (mounted && _isLoading) {
        setState(() {
          _isLoading = false;
          _isSkillsLoading = false;
        });
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

                        // Skill Verification Queue Section
                        AppSectionHeader(
                          title: 'Skill Verification Queue',
                          subtitle: 'Worker-submitted custom skills awaiting administrative approval',
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              if (_pendingSkills.isNotEmpty)
                                AppBadge(
                                  label: '${_pendingSkills.length} Pending',
                                  backgroundColor: const Color(0xFFFEF3C7),
                                  textColor: const Color(0xFFB45309),
                                ),
                              IconButton(
                                icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                                onPressed: () => _loadAdminData(background: true),
                                tooltip: 'Refresh Skills',
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),

                        if (_isSkillsLoading && _pendingSkills.isEmpty)
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 32),
                            child: Center(child: CircularProgressIndicator(color: AppColors.forest900)),
                          )
                        else if (_skillsError != null && _pendingSkills.isEmpty)
                          AppCard(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Container(
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: AppColors.error.withValues(alpha: 0.1),
                                    shape: BoxShape.circle,
                                  ),
                                  child: const Icon(Icons.error_outline_rounded, color: AppColors.error, size: 28),
                                ),
                                const SizedBox(height: 12),
                                const Text(
                                  'Unable to Load Skill Verification Queue',
                                  textAlign: TextAlign.center,
                                  style: TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 14, color: AppColors.ink900),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  _skillsError!,
                                  textAlign: TextAlign.center,
                                  style: const TextStyle(fontSize: 12, color: AppColors.error),
                                ),
                                const SizedBox(height: 16),
                                OutlinedButton.icon(
                                  icon: const Icon(Icons.refresh_rounded, size: 16),
                                  label: const Text('Retry'),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: AppColors.forest900,
                                    side: const BorderSide(color: AppColors.forest900),
                                  ),
                                  onPressed: () => _loadAdminData(background: true),
                                ),
                              ],
                            ),
                          )
                        else if (_pendingSkills.isEmpty)
                          const AppEmptyState(
                            icon: Icons.verified_user_rounded,
                            title: 'All Skills Verified',
                            description: 'Zero worker skills pending verification. Queue is completely clear.',
                          )
                        else
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (_skillsError != null)
                                Container(
                                  margin: const EdgeInsets.only(bottom: 10),
                                  padding: const EdgeInsets.all(10),
                                  decoration: BoxDecoration(
                                    color: AppColors.error.withValues(alpha: 0.1),
                                    borderRadius: BorderRadius.circular(8),
                                    border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
                                  ),
                                  child: Row(
                                    children: [
                                      const Icon(Icons.warning_amber_rounded, color: AppColors.error, size: 18),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: Text(
                                          'Background refresh failed: $_skillsError',
                                          style: const TextStyle(color: AppColors.error, fontSize: 11),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ListView.separated(
                                shrinkWrap: true,
                                physics: const NeverScrollableScrollPhysics(),
                                itemCount: _pendingSkills.length,
                                separatorBuilder: (_, __) => const SizedBox(height: 10),
                                itemBuilder: (context, index) {
                                  final skill = _pendingSkills[index];
                                  return AppCard(
                                    padding: const EdgeInsets.all(14),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Container(
                                              padding: const EdgeInsets.all(8),
                                              decoration: BoxDecoration(
                                                color: AppColors.cream100,
                                                borderRadius: BorderRadius.circular(10),
                                              ),
                                              child: const Icon(Icons.handyman_rounded, color: AppColors.forest900, size: 20),
                                            ),
                                            const SizedBox(width: 12),
                                            Expanded(
                                              child: Column(
                                                crossAxisAlignment: CrossAxisAlignment.start,
                                                children: [
                                                  Text(
                                                    skill.skillName,
                                                    style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 15),
                                                  ),
                                                  const SizedBox(height: 3),
                                                  Text(
                                                    'Worker: ${skill.workerName} (Worker #${skill.workerId})',
                                                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.ink900),
                                                  ),
                                                  const SizedBox(height: 2),
                                                  Text(
                                                    '${skill.yearsExperience.toStringAsFixed(1)} yrs exp • ₹${skill.hourlyRate.toInt()}/hr',
                                                    style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                                                  ),
                                                  if (skill.skillTags.isNotEmpty) ...[
                                                    const SizedBox(height: 4),
                                                    Text(
                                                      'Tags: ${skill.skillTags.join(", ")}',
                                                      style: const TextStyle(fontSize: 11, color: AppColors.slate600, fontStyle: FontStyle.italic),
                                                    ),
                                                  ],
                                                ],
                                              ),
                                            ),
                                            AppBadge.trustScore(skill.workerTrustScore),
                                          ],
                                        ),
                                        const SizedBox(height: 12),
                                        const Divider(height: 1, color: AppColors.border),
                                        const SizedBox(height: 10),
                                        Row(
                                          mainAxisAlignment: MainAxisAlignment.end,
                                          children: [
                                            TextButton.icon(
                                              icon: const Icon(Icons.close_rounded, size: 16, color: AppColors.error),
                                              label: const Text('Reject', style: TextStyle(color: AppColors.error, fontWeight: FontWeight.bold)),
                                              onPressed: () => _showRejectDialog(context, skill),
                                            ),
                                            const SizedBox(width: 8),
                                            ElevatedButton.icon(
                                              style: ElevatedButton.styleFrom(
                                                backgroundColor: AppColors.success,
                                                foregroundColor: AppColors.white,
                                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                              ),
                                              icon: const Icon(Icons.check_rounded, size: 16),
                                              label: const Text('Approve', style: TextStyle(fontWeight: FontWeight.bold)),
                                              onPressed: () => _handleApproveSkill(skill),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            ],
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

  Future<void> _handleApproveSkill(PendingSkillApproval skill) async {
    final messenger = ScaffoldMessenger.of(context);
    final res = await ApiService.approveSkill(skill.id);
    if (!mounted) return;
    if (res['success'] == true) {
      messenger.showSnackBar(
        SnackBar(
          content: Text("Skill '${skill.skillName}' approved and verified!"),
          backgroundColor: AppColors.success,
          duration: const Duration(seconds: 2),
        ),
      );
      _loadAdminData(background: true);
    } else {
      messenger.showSnackBar(
        SnackBar(
          content: Text(res['message'] ?? 'Failed to approve skill'),
          backgroundColor: AppColors.error,
        ),
      );
    }
  }

  void _showRejectDialog(BuildContext context, PendingSkillApproval skill) {
    final reasonCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          title: Text("Reject Skill: ${skill.skillName}"),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                "Are you sure you want to reject this custom skill for ${skill.workerName}?",
                style: const TextStyle(fontSize: 13, color: AppColors.slate600),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(
                  labelText: 'Optional Rejection Reason',
                  hintText: 'e.g. Insufficient experience or proof',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AppColors.error, foregroundColor: AppColors.white),
              onPressed: () async {
                final messenger = ScaffoldMessenger.of(context);
                Navigator.pop(ctx);
                final res = await ApiService.rejectSkill(skill.id, reason: reasonCtrl.text.trim());
                if (!mounted) return;
                if (res['success'] == true) {
                  messenger.showSnackBar(
                    SnackBar(
                      content: Text("Skill '${skill.skillName}' rejected."),
                      backgroundColor: AppColors.error,
                      duration: const Duration(seconds: 2),
                    ),
                  );
                  _loadAdminData(background: true);
                } else {
                  messenger.showSnackBar(
                    SnackBar(
                      content: Text(res['message'] ?? 'Failed to reject skill'),
                      backgroundColor: AppColors.error,
                    ),
                  );
                }
              },
              child: const Text('Confirm Reject'),
            ),
          ],
        );
      },
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
