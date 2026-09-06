import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';
import '../../services/location_service.dart';
import '../map/map_discovery_screen.dart';

class ProviderShell extends StatefulWidget {
  const ProviderShell({super.key});

  @override
  State<ProviderShell> createState() => _ProviderShellState();
}

class _ProviderShellState extends State<ProviderShell> with WidgetsBindingObserver {
  int _currentIndex = 0;
  ProviderProfile? _myProviderProfile;
  List<WorkerProfile> _directoryWorkers = [];
  List<Job> _myJobs = [];
  List<DirectOffer> _sentOffers = [];
  bool _isLoading = true;
  bool _isFetching = false;

  // Post Job Location & Radius State
  double? _jobLatitude;
  double? _jobLongitude;
  String? _jobLocationName;
  double _jobSearchRadiusKm = 10.0;
  bool _isAcquiringGps = false;

  final TextEditingController _jobSearchCtrl = TextEditingController();
  final TextEditingController _workerSearchCtrl = TextEditingController();
  final TextEditingController _offerSearchCtrl = TextEditingController();

  String _jobSearchQuery = '';
  String _workerSearchQuery = '';
  String _offerSearchQuery = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadData();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _jobSearchCtrl.dispose();
    _workerSearchCtrl.dispose();
    _offerSearchCtrl.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _loadData(background: true);
    }
  }

  bool _matchesTokens(String query, List<String?> candidateTexts) {
    final cleanQ = query.trim().toLowerCase();
    if (cleanQ.isEmpty) return true;
    final tokens = cleanQ.split(RegExp(r'\s+')).where((t) => t.isNotEmpty).toList();
    final combined = candidateTexts
        .where((t) => t != null && t.isNotEmpty)
        .map((t) => t!.toLowerCase())
        .join(' ');
    return tokens.every((token) => combined.contains(token));
  }

  Future<void> _loadData({bool background = false}) async {
    if (_isFetching) return;
    _isFetching = true;
    if (!background && _myProviderProfile == null && _myJobs.isEmpty && _directoryWorkers.isEmpty) {
      setState(() => _isLoading = true);
    }

    try {
      final results = await Future.wait([
        ApiService.fetchMyProviderProfile(),
        ApiService.fetchWorkers(),
        ApiService.fetchJobs(),
        ApiService.fetchDirectOffers(),
      ]);

      if (mounted) {
        setState(() {
          _myProviderProfile = results[0] as ProviderProfile?;
          _directoryWorkers = results[1] as List<WorkerProfile>;
          _myJobs = results[2] as List<Job>;
          _sentOffers = results[3] as List<DirectOffer>;
          _isLoading = false;
        });
      }
    } catch (e) {
      // Safely handle network error
    } finally {
      _isFetching = false;
      if (mounted && _isLoading) {
        setState(() => _isLoading = false);
      }
    }
  }

  String _formatDateTime(DateTime? dt) {
    if (dt == null) return '';
    final local = dt.toLocal();
    final diff = DateTime.now().difference(local);
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    return '${local.day}/${local.month}/${local.year} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  void _showContactDialog(BuildContext context, String name, String phone) {
    final displayPhone = phone.isNotEmpty ? phone : '+91 98765 43210';
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            const CircleAvatar(
              backgroundColor: AppColors.cream100,
              child: Icon(Icons.phone_in_talk_rounded, color: AppColors.forest900),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Contact Worker', style: TextStyle(fontSize: 13, color: AppColors.slate600)),
                  Text(name, style: const TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Job Confirmed! You can contact the worker directly below:'),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.cream50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    displayPhone,
                    style: const TextStyle(
                      fontFamily: 'Sora',
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppColors.forest900,
                    ),
                  ),
                  const Icon(Icons.call_rounded, color: AppColors.success),
                ],
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          AppButton(
            label: 'Call Worker',
            icon: Icons.phone_rounded,
            onPressed: () {
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Calling Worker at $displayPhone...')),
              );
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final displayName = _myProviderProfile?.fullName ?? ApiService.currentUserName;

    return Scaffold(
      backgroundColor: AppColors.cream50,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.person_search_rounded, color: AppColors.goldAccent, size: 24),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                displayName.isNotEmpty ? displayName : 'Job Provider Portal',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
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
            : IndexedStack(
                index: _currentIndex,
                children: [
                  _buildDashboardTab(),
                  _buildFindWorkersTab(),
                  _buildPostJobTab(),
                  _buildSentOffersTab(),
                  MapDiscoveryScreen.forProviderWorkers(
                    onSelectWorker: (w) => _showWorkerDetailsModal(context, w),
                    onSendOffer: (w) => _showSendOfferModal(context, w),
                  ),
                ],
              ),
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(top: BorderSide(color: AppColors.border, width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          selectedItemColor: AppColors.forest900,
          unselectedItemColor: AppColors.slate600,
          backgroundColor: AppColors.white,
          elevation: 0,
          type: BottomNavigationBarType.fixed,
          selectedLabelStyle: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 12),
          unselectedLabelStyle: const TextStyle(fontSize: 11),
          onTap: (idx) {
            setState(() => _currentIndex = idx);
            _loadData(background: true);
          },
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_outlined),
              activeIcon: Icon(Icons.dashboard_rounded),
              label: 'Dashboard',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.people_outline_rounded),
              activeIcon: Icon(Icons.people_rounded),
              label: 'Find Workers',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.add_circle_outline_rounded),
              activeIcon: Icon(Icons.add_circle_rounded),
              label: 'Post a Job',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.send_outlined),
              activeIcon: Icon(Icons.send_rounded),
              label: 'Sent Offers',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.map_outlined),
              activeIcon: Icon(Icons.map_rounded),
              label: 'Nearby Map',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDashboardTab() {
    return RefreshIndicator(
      onRefresh: _loadData,
      color: AppColors.forest900,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: AppResponsiveContainer(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AppSectionHeader(
              title: 'Welcome back, ${ApiService.currentUserName}!',
              subtitle: 'Select a hiring channel or manage your active job listings below:',
            ),
            const SizedBox(height: 8),

            // Two Channel Highlight Cards
            LayoutBuilder(
              builder: (context, constraints) {
                final isWide = constraints.maxWidth > 700;
                final postJobCard = AppCard(
                  backgroundColor: AppColors.forest900,
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppColors.forest800,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Icon(Icons.assignment_add, color: AppColors.goldAccent, size: 22),
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Text(
                              'Post a Job & ML Match',
                              style: TextStyle(
                                fontFamily: 'Sora',
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: AppColors.white,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Post job requirements and let our Hybrid ML Engine rank nearby verified workers by distance, experience, and trust score.',
                        style: TextStyle(color: AppColors.cream50, fontSize: 12, height: 1.35),
                      ),
                      const SizedBox(height: 14),
                      AppButton(
                        label: 'Post a New Requirement',
                        icon: Icons.add_circle_outline_rounded,
                        customColor: AppColors.cream50,
                        isFullWidth: true,
                        onPressed: () => setState(() => _currentIndex = 2),
                      ),
                    ],
                  ),
                );

                final browseCard = AppCard(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppColors.cream100,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: const Icon(Icons.person_search_rounded, color: AppColors.forest900, size: 22),
                          ),
                          const SizedBox(width: 10),
                          const Expanded(
                            child: Text(
                              'Search Worker Directory',
                              style: TextStyle(
                                fontFamily: 'Sora',
                                fontSize: 16,
                                fontWeight: FontWeight.bold,
                                color: AppColors.ink900,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Browse worker storefront profiles directly (view skills, completed jobs, trust scores) and send direct offers with proposed budgets.',
                        style: TextStyle(color: AppColors.slate600, fontSize: 12, height: 1.35),
                      ),
                      const SizedBox(height: 14),
                      AppButton(
                        label: 'Browse Worker Directory',
                        icon: Icons.people_outline_rounded,
                        isSecondary: true,
                        isFullWidth: true,
                        onPressed: () => setState(() => _currentIndex = 1),
                      ),
                    ],
                  ),
                );

                return isWide
                    ? Row(
                        children: [
                          Expanded(child: postJobCard),
                          const SizedBox(width: 14),
                          Expanded(child: browseCard),
                        ],
                      )
                    : Column(
                        children: [
                          postJobCard,
                          const SizedBox(height: 12),
                          browseCard,
                        ],
                      );
              },
            ),

            const SizedBox(height: 20),

            // Active Posted Jobs Section
            AppSectionHeader(
              title: 'My Active Job Listings',
              subtitle: 'Open requirements accepting applications and ML candidate matches',
              trailing: IconButton(
                icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                onPressed: _loadData,
                tooltip: 'Refresh Listings',
              ),
            ),
            const SizedBox(height: 8),

            AppSearchBar(
              controller: _jobSearchCtrl,
              hintText: 'Search my jobs by title, skill, or status...',
              onChanged: (val) => setState(() => _jobSearchQuery = val),
              onClear: () => setState(() => _jobSearchQuery = ''),
            ),

            const SizedBox(height: 14),

            Builder(
              builder: (context) {
                final filteredJobs = _myJobs.where((j) {
                  return _matchesTokens(_jobSearchQuery, [
                    j.title,
                    j.description,
                    j.requiredSkill,
                    j.status,
                    j.worker?.fullName,
                  ]);
                }).toList();

                if (_myJobs.isEmpty) {
                  return AppEmptyState(
                    icon: Icons.assignment_outlined,
                    title: 'No Job Listings Posted Yet',
                    description: 'Create your first job listing to get ML matched worker recommendations.',
                    actionLabel: 'Post a Job Now',
                    onAction: () => setState(() => _currentIndex = 2),
                  );
                }

                if (filteredJobs.isEmpty) {
                  return AppEmptyState(
                    icon: Icons.search_off_rounded,
                    title: 'No jobs match your search',
                    description: 'Try searching with a different skill, title, or status.',
                    actionLabel: 'Clear Search',
                    onAction: () {
                      _jobSearchCtrl.clear();
                      setState(() => _jobSearchQuery = '');
                    },
                  );
                }

                return LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth > 750;
                    return isWide
                        ? GridView.builder(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              mainAxisSpacing: 14,
                              crossAxisSpacing: 14,
                              childAspectRatio: 1.4,
                            ),
                            itemCount: filteredJobs.length,
                            itemBuilder: (ctx, i) => _buildProviderJobCard(filteredJobs[i]),
                          )
                        : ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: filteredJobs.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 14),
                            itemBuilder: (ctx, i) => _buildProviderJobCard(filteredJobs[i]),
                          );
                  },
                );
              },
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    ),
  );
}

  Future<void> _handleDeleteJob(int jobId) async {
    final ok = await ApiService.deleteJob(jobId);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ok ? 'Job deleted successfully' : 'Failed to delete job'),
          duration: const Duration(seconds: 2),
        ),
      );
    }
    _loadData();
  }

  Widget _buildProviderJobCard(Job job) {
    final isCompleted = job.status == 'completed';
    final workerName = job.worker?.fullName ?? 'Assigned Worker';
    final workerPhone = job.worker?.phone ?? '+91 98765 43210';

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Flexible(
                child: AppBadge(
                  label: '${job.requiredSkill} • ${job.acceptedCount}/${job.workersNeeded} Filled',
                  backgroundColor: AppColors.cream100,
                  textColor: AppColors.forest900,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '₹${job.budgetMin.toInt()} - ₹${job.budgetMax.toInt()}',
                style: const TextStyle(
                  fontFamily: 'Sora',
                  fontWeight: FontWeight.bold,
                  color: AppColors.success,
                  fontSize: 15,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            job.title,
            style: const TextStyle(
              fontFamily: 'Sora',
              fontSize: 15,
              fontWeight: FontWeight.bold,
              color: AppColors.ink900,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Text(
            'Posted ${_formatDateTime(job.createdAt)} • Urgency: ${job.urgency.toUpperCase()}',
            style: const TextStyle(fontSize: 11, color: AppColors.slate600),
          ),
          const SizedBox(height: 8),
          Text(
            job.description,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: AppColors.slate600, height: 1.3),
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 12),

          if (isCompleted) ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const AppBadge(
                  label: 'COMPLETED & PAID',
                  backgroundColor: Color(0xFFEBF5FF),
                  textColor: Color(0xFF2563EB),
                  icon: Icons.verified_rounded,
                ),
                Wrap(
                  spacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    AppButton(
                      label: 'Rate Worker',
                      icon: Icons.star_rounded,
                      isSecondary: true,
                      onPressed: () => _showProviderRateWorkerModal(context, job),
                    ),
                    IconButton(
                      icon: const Icon(Icons.phone_rounded, color: AppColors.forest900, size: 20),
                      tooltip: 'Contact Worker',
                      onPressed: () => _showContactDialog(context, workerName, workerPhone),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline_rounded, color: AppColors.error, size: 20),
                      tooltip: 'Delete Job',
                      onPressed: () => _handleDeleteJob(job.id),
                    ),
                  ],
                ),
              ],
            )
          ] else if (job.workerId != null) ...[
            Row(
              children: [
                Expanded(
                  child: AppButton(
                    label: job.providerCompleted ? 'Waiting Worker Confirm' : 'Confirm Completion',
                    icon: Icons.check_circle_outline_rounded,
                    customColor: job.providerCompleted ? AppColors.slate600 : AppColors.success,
                    onPressed: job.providerCompleted
                        ? null
                        : () async {
                            final ok = await ApiService.completeJob(job.id);
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text(ok ? 'Completion confirmed!' : 'Already marked complete.')),
                              );
                            }
                            _loadData();
                          },
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.phone_rounded, color: AppColors.forest900),
                  tooltip: 'Contact Worker',
                  onPressed: () => _showContactDialog(context, workerName, workerPhone),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, color: AppColors.error, size: 20),
                  tooltip: 'Delete Job',
                  onPressed: () => _handleDeleteJob(job.id),
                ),
              ],
            )
          ] else ...[
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      AppButton(
                        label: 'ML Matches',
                        icon: Icons.auto_graph_rounded,
                        onPressed: () => _showMatchesModal(context, job.id),
                      ),
                      AppButton(
                        label: 'Applicants',
                        icon: Icons.people_outline_rounded,
                        isSecondary: true,
                        onPressed: () => _showApplicationsModal(context, job.id),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, color: AppColors.error, size: 20),
                  tooltip: 'Delete Job',
                  onPressed: () => _handleDeleteJob(job.id),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildFindWorkersTab() {
    return RefreshIndicator(
      onRefresh: _loadData,
      color: AppColors.forest900,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: AppResponsiveContainer(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Worker Storefront Directory',
                subtitle: 'Search and send direct job offers to verified skilled workers',
                trailing: IconButton(
                  icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                  onPressed: () => _loadData(background: true),
                  tooltip: 'Refresh Directory',
                ),
              ),
              const SizedBox(height: 8),

            AppSearchBar(
              controller: _workerSearchCtrl,
              hintText: 'Search workers by name, skill, or service...',
              onChanged: (val) => setState(() => _workerSearchQuery = val),
              onClear: () => setState(() => _workerSearchQuery = ''),
            ),

            const SizedBox(height: 14),

            Builder(
              builder: (context) {
                final filteredWorkers = _directoryWorkers.where((w) {
                  final skillNames = w.skills.map((s) => s.skillName).toList();
                  final skillTags = w.skills.expand((s) => s.skillTags).toList();
                  return _matchesTokens(_workerSearchQuery, [
                    w.fullName,
                    w.bio,
                    w.hourlyRate.toString(),
                    ...skillNames,
                    ...skillTags,
                  ]);
                }).toList();

                if (_directoryWorkers.isEmpty) {
                  return AppEmptyState(
                    icon: Icons.people_outline_rounded,
                    title: 'No Workers Found',
                    description: 'There are no active worker profiles registered in the directory right now.',
                    actionLabel: 'Refresh Directory',
                    onAction: _loadData,
                  );
                }

                if (filteredWorkers.isEmpty) {
                  return AppEmptyState(
                    icon: Icons.search_off_rounded,
                    title: 'No workers match your search',
                    description: 'Try searching for a different skill, name, or service category.',
                    actionLabel: 'Clear Search',
                    onAction: () {
                      _workerSearchCtrl.clear();
                      setState(() => _workerSearchQuery = '');
                    },
                  );
                }

                return LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth > 750;
                    return isWide
                        ? GridView.builder(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              mainAxisSpacing: 14,
                              crossAxisSpacing: 14,
                              childAspectRatio: 1.4,
                            ),
                            itemCount: filteredWorkers.length,
                            itemBuilder: (ctx, i) => _buildWorkerCard(filteredWorkers[i]),
                          )
                        : ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: filteredWorkers.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 14),
                            itemBuilder: (ctx, i) => _buildWorkerCard(filteredWorkers[i]),
                          );
                  },
                );
              },
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    ),
  );
}

  Widget _buildWorkerCard(WorkerProfile w) {
    final firstSkill = w.skills.isNotEmpty ? w.skills[0].skillName : 'General Services';

    return AppCard(
      onTap: () => _showWorkerDetailsModal(context, w),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: AppColors.forest900,
                child: Text(
                  w.fullName.isNotEmpty ? w.fullName[0].toUpperCase() : 'W',
                  style: const TextStyle(fontFamily: 'Sora', fontSize: 16, fontWeight: FontWeight.bold, color: AppColors.white),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            w.fullName,
                            style: const TextStyle(fontFamily: 'Sora', fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.ink900),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 4),
                        const Icon(Icons.verified_rounded, color: AppColors.goldAccent, size: 15),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      '$firstSkill • ₹${w.hourlyRate.toInt()}/hr',
                      style: const TextStyle(fontSize: 11, color: AppColors.slate600),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              AppBadge.trustScore(w.trustScore),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            w.bio ?? 'Certified Skilled Worker ready for local service assignments.',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: AppColors.slate600, height: 1.3),
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Flexible(
                child: Text(
                  '${w.ratingDisplay} • ${w.completedJobsCount} Jobs',
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.forest900),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              AppButton(
                label: 'Send Offer',
                icon: Icons.send_rounded,
                onPressed: () => _showSendOfferModal(context, w),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _acquireJobGpsLocation() async {
    setState(() => _isAcquiringGps = true);
    final result = await LocationService.getCurrentLocation();
    setState(() => _isAcquiringGps = false);

    if (!mounted) return;

    if (result.isSuccess) {
      setState(() {
        _jobLatitude = result.latitude;
        _jobLongitude = result.longitude;
        _jobLocationName = 'Device GPS (${result.latitude!.toStringAsFixed(4)}, ${result.longitude!.toStringAsFixed(4)})';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('GPS Location acquired successfully!'),
          duration: Duration(seconds: 2),
        ),
      );
    } else {
      showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Row(
            children: [
              Icon(Icons.location_off_rounded, color: AppColors.error),
              SizedBox(width: 8),
              Text('Location Unavailable', style: TextStyle(fontSize: 16)),
            ],
          ),
          content: Text(result.errorMessage ?? 'Could not determine GPS coordinates.'),
          actions: [
            if (result.isServiceDisabled)
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  LocationService.openLocationSettings();
                },
                child: const Text('Enable GPS'),
              ),
            if (result.isPermissionDeniedForever)
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  LocationService.openAppSettings();
                },
                child: const Text('Open App Settings'),
              ),
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
  }

  Widget _buildPostJobTab() {
    final titleCtrl = TextEditingController();
    final descCtrl = TextEditingController();
    final skillCtrl = TextEditingController(text: "Plumbing");
    final workersNeededCtrl = TextEditingController(text: "1");
    final minBudgetCtrl = TextEditingController(text: "500");
    final maxBudgetCtrl = TextEditingController(text: "1200");
    final dateCtrl = TextEditingController(text: "Tomorrow at 10:00 AM");

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      child: AppResponsiveContainer(
        maxWidth: 700,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const AppSectionHeader(
              title: 'Post a New Requirement',
              subtitle: 'Specify job details and location to activate ML Candidate Matching',
            ),
            const SizedBox(height: 8),

            AppCard(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  TextField(
                    controller: titleCtrl,
                    decoration: const InputDecoration(labelText: 'Job Title (e.g. Emergency Pipe Leak Repair)'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: descCtrl,
                    maxLines: 3,
                    decoration: const InputDecoration(labelText: 'Job Description & Scope'),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: skillCtrl,
                          decoration: const InputDecoration(labelText: 'Required Skill'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: workersNeededCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Workers Needed'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: minBudgetCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Min Budget (₹)'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: maxBudgetCtrl,
                          keyboardType: TextInputType.number,
                          decoration: const InputDecoration(labelText: 'Max Budget (₹)'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: dateCtrl,
                    decoration: const InputDecoration(labelText: 'Scheduled Date/Time'),
                  ),
                  const SizedBox(height: 16),

                  // Job Location & Search Radius
                  const Text(
                    'JOB LOCATION & SEARCH RADIUS',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.8,
                      color: AppColors.slate600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: AppColors.cream50,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: _jobLatitude != null ? AppColors.success : AppColors.border,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              _jobLatitude != null ? Icons.location_on_rounded : Icons.location_off_outlined,
                              color: _jobLatitude != null ? AppColors.success : AppColors.slate600,
                              size: 20,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _jobLatitude != null
                                    ? (_jobLocationName ?? 'GPS: ${_jobLatitude!.toStringAsFixed(4)}, ${_jobLongitude!.toStringAsFixed(4)}')
                                    : 'Location not selected',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: _jobLatitude != null ? AppColors.forest900 : AppColors.slate600,
                                ),
                              ),
                            ),
                            if (_isAcquiringGps)
                              const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.forest900),
                              )
                            else
                              OutlinedButton.icon(
                                onPressed: _acquireJobGpsLocation,
                                icon: const Icon(Icons.my_location_rounded, size: 13),
                                label: Text(
                                  _jobLatitude != null ? 'Update GPS' : 'Use My Current Location',
                                  style: const TextStyle(fontSize: 11),
                                ),
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: AppColors.forest900,
                                  side: const BorderSide(color: AppColors.forest900),
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  minimumSize: Size.zero,
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Candidate Search Radius:',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.ink900),
                        ),
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 8,
                          children: [5.0, 10.0, 15.0, 25.0].map((r) {
                            final isSelected = _jobSearchRadiusKm == r;
                            return ChoiceChip(
                              label: Text('${r.toInt()} km', style: TextStyle(fontSize: 11, color: isSelected ? Colors.white : AppColors.ink900)),
                              selected: isSelected,
                              selectedColor: AppColors.forest900,
                              backgroundColor: AppColors.cream100,
                              onSelected: (selected) {
                                if (selected) {
                                  setState(() => _jobSearchRadiusKm = r);
                                }
                              },
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),
                  AppButton(
                    label: 'Publish Job Requirement',
                    icon: Icons.check_circle_outline_rounded,
                    isFullWidth: true,
                    onPressed: () async {
                      if (titleCtrl.text.trim().isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Please enter job title.')));
                        return;
                      }

                      final ok = await ApiService.postJob({
                        'title': titleCtrl.text.trim(),
                        'description': descCtrl.text.trim(),
                        'required_skill': skillCtrl.text.trim(),
                        'workers_needed': int.tryParse(workersNeededCtrl.text.trim()) ?? 1,
                        'budget_min': double.tryParse(minBudgetCtrl.text.trim()) ?? 500.0,
                        'budget_max': double.tryParse(maxBudgetCtrl.text.trim()) ?? 1200.0,
                        'scheduled_date': dateCtrl.text.trim(),
                        'urgency': 'immediate',
                        'latitude': _jobLatitude ?? 12.9716,
                        'longitude': _jobLongitude ?? 77.5946,
                        'search_radius_km': _jobSearchRadiusKm,
                        if (_jobLocationName != null) 'location_name': _jobLocationName,
                      });

                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(ok ? 'Job requirement published! ML matching active.' : 'Job posted.')),
                        );
                        _loadData();
                        setState(() => _currentIndex = 0);
                      }
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Widget _buildSentOffersTab() {
    return RefreshIndicator(
      onRefresh: _loadData,
      color: AppColors.forest900,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        child: AppResponsiveContainer(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppSectionHeader(
                title: 'Sent Direct Job Offers',
                subtitle: 'Direct outreach offers sent to workers from storefront directory',
                trailing: IconButton(
                  icon: const Icon(Icons.refresh_rounded, color: AppColors.forest900, size: 20),
                  onPressed: () => _loadData(background: true),
                  tooltip: 'Refresh Sent Offers',
                ),
              ),
              const SizedBox(height: 8),

            AppSearchBar(
              controller: _offerSearchCtrl,
              hintText: 'Search sent offers by title, worker, or skill...',
              onChanged: (val) => setState(() => _offerSearchQuery = val),
              onClear: () => setState(() => _offerSearchQuery = ''),
            ),

            const SizedBox(height: 14),

            Builder(
              builder: (context) {
                final filteredOffers = _sentOffers.where((o) {
                  return _matchesTokens(_offerSearchQuery, [
                    o.title,
                    o.description,
                    o.requiredSkill,
                    o.worker?.fullName,
                    o.status,
                    o.proposedBudget.toString(),
                  ]);
                }).toList();

                if (_sentOffers.isEmpty) {
                  return AppEmptyState(
                    icon: Icons.send_outlined,
                    title: 'No Direct Offers Sent',
                    description: 'Browse the worker directory and tap "Send Direct Offer" to reach out directly.',
                    actionLabel: 'Find Workers',
                    onAction: () => setState(() => _currentIndex = 1),
                  );
                }

                if (filteredOffers.isEmpty) {
                  return AppEmptyState(
                    icon: Icons.search_off_rounded,
                    title: 'No sent offers match your search',
                    description: 'Try searching with a different worker name, skill, or title.',
                    actionLabel: 'Clear Search',
                    onAction: () {
                      _offerSearchCtrl.clear();
                      setState(() => _offerSearchQuery = '');
                    },
                  );
                }

                return LayoutBuilder(
                  builder: (context, constraints) {
                    final isWide = constraints.maxWidth > 750;
                    return isWide
                        ? GridView.builder(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 2,
                              mainAxisSpacing: 14,
                              crossAxisSpacing: 14,
                              childAspectRatio: 1.4,
                            ),
                            itemCount: filteredOffers.length,
                            itemBuilder: (ctx, i) => _buildSentOfferCard(filteredOffers[i]),
                          )
                        : ListView.separated(
                            shrinkWrap: true,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount: filteredOffers.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 14),
                            itemBuilder: (ctx, i) => _buildSentOfferCard(filteredOffers[i]),
                          );
                  },
                );
              },
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    ),
  );
}

  Widget _buildSentOfferCard(DirectOffer offer) {
    final workerName = offer.worker?.fullName ?? 'Worker';
    final workerPhone = offer.worker?.phone ?? '+91 98765 43210';

    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Flexible(child: AppBadge.status(offer.status)),
              const SizedBox(width: 8),
              Text(
                '₹${offer.proposedBudget.toInt()}',
                style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, color: AppColors.success, fontSize: 16),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            offer.title,
            style: const TextStyle(fontFamily: 'Sora', fontSize: 15, fontWeight: FontWeight.bold, color: AppColors.ink900),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Flexible(
                child: Text(
                  'To: $workerName',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.slate600),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 4),
              Text('• ${_formatDateTime(offer.sentAt)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            offer.description,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: AppColors.slate600, height: 1.3),
          ),
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.border),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Status: ${offer.status.toUpperCase()}',
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppColors.slate600),
              ),
              IconButton(
                icon: const Icon(Icons.phone_rounded, color: AppColors.forest900, size: 20),
                onPressed: () => _showContactDialog(context, workerName, workerPhone),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showMatchesModal(BuildContext context, int jobId) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return FutureBuilder<List<MatchedWorker>>(
          future: ApiService.fetchJobMatches(jobId),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            final matches = snapshot.data ?? [];
            return Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('ML Hybrid Matched Candidates', style: TextStyle(fontFamily: 'Sora', fontSize: 17, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 4),
                  const Text('Ranked by distance, trust score, and skill relevance algorithm', style: TextStyle(fontSize: 12, color: AppColors.slate600)),
                  const SizedBox(height: 14),

                  matches.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.all(16),
                          child: Text('No ML matches returned for this job.'),
                        )
                      : ListView.separated(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: matches.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (context, index) {
                            final m = matches[index];
                            return AppCard(
                              padding: const EdgeInsets.all(12),
                              child: Row(
                                children: [
                                  CircleAvatar(
                                    radius: 18,
                                    backgroundColor: AppColors.forest900,
                                    child: Text(m.worker.fullName[0], style: const TextStyle(color: AppColors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(m.worker.fullName, style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 13)),
                                        Text('${m.worker.ratingDisplay} • ${m.distanceKm.toStringAsFixed(1)}km away • Trust: ${m.worker.trustScore.toStringAsFixed(1)}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  AppBadge(
                                    label: '${m.matchScore.toInt()}% Match',
                                    backgroundColor: const Color(0xFFE6F7ED),
                                    textColor: AppColors.success,
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _showApplicationsModal(BuildContext context, int jobId) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return FutureBuilder<List<JobApplication>>(
          future: ApiService.fetchJobApplications(jobId),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            final apps = snapshot.data ?? [];
            return Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Job Applicants', style: TextStyle(fontFamily: 'Sora', fontSize: 17, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 14),
                  apps.isEmpty
                      ? const Padding(
                          padding: EdgeInsets.all(16),
                          child: Text('No applications submitted yet for this requirement.'),
                        )
                      : ListView.separated(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: apps.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (context, index) {
                            final a = apps[index];
                            final wName = a.worker?.fullName ?? 'Worker #${a.workerId}';
                            final isAccepted = a.status == 'accepted';

                            return AppCard(
                              padding: const EdgeInsets.all(12),
                              child: Row(
                                children: [
                                  CircleAvatar(
                                    radius: 18,
                                    backgroundColor: AppColors.forest900,
                                    child: Text(wName[0], style: const TextStyle(color: AppColors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(wName, style: const TextStyle(fontFamily: 'Sora', fontWeight: FontWeight.bold, fontSize: 13)),
                                        Text('${a.worker?.ratingDisplay ?? ""} • Status: ${a.status.toUpperCase()}', style: const TextStyle(fontSize: 11, color: AppColors.slate600)),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  if (isAccepted) ...[
                                    const AppBadge(label: 'ACCEPTED', backgroundColor: Color(0xFFE6F7ED), textColor: AppColors.success),
                                  ] else ...[
                                    AppButton(
                                      label: 'Accept',
                                      icon: Icons.check_rounded,
                                      onPressed: () async {
                                        Navigator.pop(ctx);
                                        await ApiService.respondJobApplication(jobId, a.id, "accept");
                                        _loadData();
                                      },
                                    ),
                                  ],
                                ],
                              ),
                            );
                          },
                        ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _showWorkerDetailsModal(BuildContext context, WorkerProfile w) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: AppColors.forest900,
                    child: Text(w.fullName[0], style: const TextStyle(fontFamily: 'Sora', fontSize: 20, color: AppColors.white, fontWeight: FontWeight.bold)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(w.fullName, style: const TextStyle(fontFamily: 'Sora', fontSize: 16, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 2),
                        Text('${w.ratingDisplay} • ₹${w.hourlyRate.toInt()}/hr • ${w.completedJobsCount} Jobs Completed', style: const TextStyle(fontSize: 12, color: AppColors.slate600)),
                      ],
                    ),
                  ),
                  AppBadge.trustScore(w.trustScore),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1, color: AppColors.border),
              const SizedBox(height: 12),
              const Text('Bio & Overview:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
              const SizedBox(height: 4),
              Text(w.bio ?? 'Certified Skilled Worker registered on ServEase digital trust platform.', style: const TextStyle(color: AppColors.slate600, height: 1.35, fontSize: 13)),
              const SizedBox(height: 20),
              AppButton(
                label: 'Send Direct Job Offer',
                icon: Icons.send_rounded,
                isFullWidth: true,
                onPressed: () {
                  Navigator.pop(ctx);
                  _showSendOfferModal(context, w);
                },
              ),
            ],
          ),
        );
      },
    );
  }

  void _showSendOfferModal(BuildContext context, WorkerProfile worker) {
    final titleCtrl = TextEditingController(text: "Direct Job Offer for ${worker.fullName}");
    final descCtrl = TextEditingController(text: "Direct job outreach proposal based on your storefront profile.");
    final skillCtrl = TextEditingController(text: worker.skills.isNotEmpty ? worker.skills[0].skillName : "Plumbing");
    final budgetCtrl = TextEditingController(text: (worker.hourlyRate * 3).toInt().toString());
    final dateCtrl = TextEditingController(text: "Tomorrow at 10:00 AM");

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) {
        return Padding(
          padding: EdgeInsets.only(
            left: 20, right: 20, top: 20,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Send Direct Offer to ${worker.fullName}', style: const TextStyle(fontFamily: 'Sora', fontSize: 17, fontWeight: FontWeight.bold)),
                const SizedBox(height: 14),
                TextField(controller: titleCtrl, decoration: const InputDecoration(labelText: 'Offer Title')),
                const SizedBox(height: 10),
                TextField(controller: descCtrl, maxLines: 2, decoration: const InputDecoration(labelText: 'Description & Scope')),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(child: TextField(controller: skillCtrl, decoration: const InputDecoration(labelText: 'Required Skill'))),
                    const SizedBox(width: 10),
                    Expanded(child: TextField(controller: budgetCtrl, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Proposed Budget (₹)'))),
                  ],
                ),
                const SizedBox(height: 10),
                TextField(controller: dateCtrl, decoration: const InputDecoration(labelText: 'Scheduled Timing')),
                const SizedBox(height: 18),
                AppButton(
                  label: 'Send Offer to Worker',
                  icon: Icons.send_rounded,
                  isFullWidth: true,
                  onPressed: () async {
                    Navigator.pop(ctx);
                    final ok = await ApiService.sendDirectOffer({
                      'worker_id': worker.id,
                      'title': titleCtrl.text.trim(),
                      'description': descCtrl.text.trim(),
                      'required_skill': skillCtrl.text.trim(),
                      'proposed_budget': double.tryParse(budgetCtrl.text.trim()) ?? 800.0,
                      'scheduled_date': dateCtrl.text.trim(),
                      'latitude': 12.9716,
                      'longitude': 77.5946,
                    });

                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(ok ? 'Direct offer sent to ${worker.fullName}!' : 'Direct offer sent.')),
                      );
                      _loadData();
                      setState(() => _currentIndex = 3);
                    }
                  },
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showProviderRateWorkerModal(BuildContext context, Job job) {
    int overallRating = 5;
    int serviceQualityRating = 5;
    int behaviorRating = 5;
    int reliabilityRating = 5;
    int commRating = 5;
    final commentCtrl = TextEditingController();
    bool isSubmitting = false;

    final workerName = job.worker?.fullName ?? (job.workerId != null ? 'Worker #${job.workerId}' : 'Worker');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(
                left: 20,
                right: 20,
                top: 20,
                bottom: MediaQuery.of(context).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Rate Worker Performance',
                          style: TextStyle(fontFamily: 'Sora', fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close_rounded),
                          onPressed: () => Navigator.pop(ctx),
                        ),
                      ],
                    ),
                    Text(
                      'Job: ${job.title} • Worker: $workerName',
                      style: const TextStyle(fontSize: 12, color: AppColors.slate600),
                    ),
                    const SizedBox(height: 16),
                    const Text('Overall Rating', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                    const SizedBox(height: 6),
                    Row(
                      children: List.generate(5, (index) {
                        final star = index + 1;
                        return IconButton(
                          icon: Icon(
                            star <= overallRating ? Icons.star_rounded : Icons.star_outline_rounded,
                            color: AppColors.goldAccent,
                            size: 32,
                          ),
                          onPressed: () => setModalState(() => overallRating = star),
                        );
                      }),
                    ),
                    const SizedBox(height: 12),
                    const Divider(height: 1, color: AppColors.border),
                    const SizedBox(height: 12),
                    const Text('Category Breakdown', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 8),
                    _buildCategoryStarSelector('Work & Service Quality', serviceQualityRating, (val) => setModalState(() => serviceQualityRating = val)),
                    _buildCategoryStarSelector('Behaviour & Professionalism', behaviorRating, (val) => setModalState(() => behaviorRating = val)),
                    _buildCategoryStarSelector('Reliability & Punctuality', reliabilityRating, (val) => setModalState(() => reliabilityRating = val)),
                    _buildCategoryStarSelector('Communication', commRating, (val) => setModalState(() => commRating = val)),
                    const SizedBox(height: 14),
                    const Text('Feedback / Comments (Optional)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                    const SizedBox(height: 6),
                    TextField(
                      controller: commentCtrl,
                      maxLines: 2,
                      decoration: InputDecoration(
                        hintText: 'Share feedback about the quality and timeliness of work...',
                        hintStyle: const TextStyle(fontSize: 13, color: AppColors.slate600),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                    const SizedBox(height: 20),
                    AppButton(
                      label: isSubmitting ? 'Submitting...' : 'Submit Rating & Recalculate Trust',
                      icon: Icons.rate_review_rounded,
                      isFullWidth: true,
                      onPressed: isSubmitting
                          ? null
                          : () async {
                              final messenger = ScaffoldMessenger.of(context);
                              setModalState(() => isSubmitting = true);
                              final res = await ApiService.submitRating(
                                jobId: job.id,
                                overallRating: overallRating,
                                categoryRatings: {
                                  'service_quality': serviceQualityRating,
                                  'behavior': behaviorRating,
                                  'reliability': reliabilityRating,
                                  'communication': commRating,
                                },
                                comment: commentCtrl.text.trim().isNotEmpty ? commentCtrl.text.trim() : null,
                              );
                              setModalState(() => isSubmitting = false);
                              if (ctx.mounted) {
                                Navigator.pop(ctx);
                              }
                              messenger.showSnackBar(
                                SnackBar(
                                  content: Text(res['success'] == true ? 'Worker rated successfully! Trust score updated.' : res['message'] ?? 'Rating failed'),
                                  backgroundColor: res['success'] == true ? AppColors.forest900 : AppColors.error,
                                ),
                              );
                              if (mounted) {
                                _loadData();
                              }
                            },
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildCategoryStarSelector(String label, int currentVal, ValueChanged<int> onChanged) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12, color: AppColors.ink900))),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(5, (i) {
              final star = i + 1;
              return InkWell(
                onTap: () => onChanged(star),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 2),
                  child: Icon(
                    star <= currentVal ? Icons.star_rounded : Icons.star_outline_rounded,
                    color: AppColors.goldAccent,
                    size: 20,
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }
}
